"""
Gemini 2.0 transcription module with timestamp support
Transcribes audio files and returns segments with start/end times for SRT generation
"""

import json
import os
import sys
import threading
import time

from config import GEMINI_API_KEY, LANGUAGE, MAX_OUTPUT_TOKENS, MODEL, TEMPERATURE
from google import generativeai as genai


class ProgressIndicator:
    """Background spinner for long-running operations"""

    def __init__(self, message: str):
        self.message = message
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        symbols = [".", "..", "...", "....", "....."]
        start_time = time.time()
        idx = 0
        while not self._stop.is_set():
            elapsed = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            time_str = f"{mins}m{secs:02d}s" if mins else f"{secs}s"
            sys.stdout.write(f"\r   {self.message} {symbols[idx % len(symbols)]} ({time_str})   ")
            sys.stdout.flush()
            idx += 1
            self._stop.wait(1.0)

    def stop(self, final_message: str = None):
        self._stop.set()
        if self._thread:
            self._thread.join()
        # Clear the entire line first to remove spinner remnants
        sys.stdout.write("\r" + " " * 80 + "\r")
        if final_message:
            sys.stdout.write(f"   {final_message}\n")
        sys.stdout.flush()


class Transcriber:
    """Transcribes audio using Gemini 2.0 API with timestamp support"""

    def __init__(self):
        """Initialize the transcriber"""
        self.api_key = GEMINI_API_KEY
        self.model_name = MODEL
        self.language = LANGUAGE
        self.temperature = TEMPERATURE
        self.max_tokens = MAX_OUTPUT_TOKENS

    def transcribe(self, audio_path: str, chunk_duration: float = None, label: str = None, 
                  target_lang: str = None, is_bilingual: bool = False) -> list:
        """
        Transcribe audio file and return segments with timestamps

        Args:
            audio_path: Path to audio file (WAV format)
            chunk_duration: Duration of this chunk in seconds (for better prompting)
            label: Display label for progress (e.g. "Chunk 3/16")
            target_lang: Target language for translation (e.g. "id", "en")
            is_bilingual: If True, output both original and translated text

        Returns:
            List of segments with 'start', 'end', and 'text' keys
        """
        audio_file = None
        prefix = f"   [{label}] " if label else "   "
        try:
            # Validate API key
            if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
                raise ValueError(
                    "GEMINI_API_KEY not set in config.py. Please edit src/config.py"
                )

            # Initialize Gemini client
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)

            # Show file size for context
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

            # Upload audio file with progress
            upload_label = f"[{label}] Uploading" if label else "Uploading to Gemini API"
            progress = ProgressIndicator(upload_label)
            progress.start()
            audio_file = genai.upload_file(audio_path)
            progress.stop(f"{prefix}Uploaded ({file_size_mb:.1f} MB)")

            # Build prompt
            language_names = {
                "id": "Indonesian",
                "en": "English",
                "ja": "Japanese",
                "ko": "Korean",
                "zh": "Chinese",
                "ar": "Arabic",
                "es": "Spanish",
                "fr": "French",
                "de": "German",
                "it": "Italian",
                "pt": "Portuguese",
                "ru": "Russian",
                "hi": "Hindi",
                "th": "Thai",
                "vi": "Vietnamese",
            }
            
            lang_instruction = ""
            if self.language and self.language != "auto":
                lang_name = language_names.get(self.language, self.language)
                lang_instruction = f"The audio is in {lang_name}."

            # Construct the prompt based on mode
            if target_lang:
                target_lang_name = language_names.get(target_lang, target_lang)
                if is_bilingual:
                    task_instruction = (
                        f"Transcribe the audio and translate it into {target_lang_name}. "
                        "For each segment, provide BOTH the original text and the translation. "
                        "Return a JSON array of objects with keys: 'start' (float seconds), 'end' (float seconds), "
                        "'text' (string, original text), and 'translation' (string, translated text)."
                    )
                else:
                    task_instruction = (
                        f"Transcribe the audio and translate it directly into {target_lang_name}. "
                        "Return a JSON array of objects with keys: 'start' (float seconds), 'end' (float seconds), "
                        "and 'text' (string, translated text)."
                    )
            else:
                task_instruction = (
                    "Transcribe the audio perfectly. "
                    "Return a JSON array of objects with keys: 'start' (float seconds), 'end' (float seconds), "
                    "and 'text' (string)."
                )

            duration_hint = ""
            if chunk_duration:
                duration_hint = f"\nThis audio is approximately {chunk_duration:.0f} seconds long. Timestamps must start near 0.0 and end near {chunk_duration:.0f}.\n"



            # Generate transcription with progress
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
                "response_mime_type": "application/json",
            }

            # Construct JSON template based on mode
            if is_bilingual:
                json_template = '[{"start": 0.0, "end": 2.5, "text": "Segment text", "translation": "Translated text"}]'
            elif target_lang:
                json_template = '[{"start": 0.0, "end": 2.5, "text": "Translated text"}]'
            else:
                json_template = '[{"start": 0.0, "end": 2.5, "text": "Segment text"}]'

            prompt = f"""
            {lang_instruction}
            {duration_hint}
            {task_instruction}
            
            Use this JSON format for the response:
            {json_template}
            
            Strictly follow this format. Do not include markdown code blocks.
            Ensure timestamps are accurate.
            """

            transcribe_label = f"[{label}] Transcribing" if label else "Gemini is transcribing"
            progress = ProgressIndicator(transcribe_label)
            progress.start()
            response = model.generate_content(
                [prompt, audio_file], generation_config=generation_config
            )
            progress.stop(f"{prefix}Transcription received!")

            # Cleanup
            try:
                genai.delete_file(audio_file.name)
            except Exception:
                pass

            # Parse JSON response
            text = response.text.strip()
            # Remove markdown if present
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines).strip()
            
            try:
                raw_segments = json.loads(text)
            except json.JSONDecodeError:
                # Fallback: try to find array in text
                import re
                match = re.search(r'\[.*\]', text, re.DOTALL)
                if match:
                    raw_segments = json.loads(match.group(0))
                else:
                    # Provide snippet for debugging
                    raise ValueError(f"Could not parse JSON response: {text[:200]}...")

            # Validate and format segments
            segments = []
            for s in raw_segments:
                if 'start' in s and 'end' in s and 'text' in s:
                    # Format text for bilingual mode
                    segment_text = s['text']
                    if is_bilingual and 'translation' in s and s['translation']:
                         segment_text = f"{s['text']}\n{s['translation']}"
                    
                    segments.append({
                        'start': float(s['start']),
                        'end': float(s['end']),
                        'text': segment_text
                    })
            
            # Validate segment structure
            validated_segments = []
            for i, segment in enumerate(segments):
                # Ensure all required keys exist
                if not all(key in segment for key in ["start", "end", "text"]):
                    print(f"{prefix}Warning: Skipping invalid segment at index {i} (missing keys)")
                    continue
                
                # Type validation
                if not isinstance(segment.get("start"), (int, float)):
                    print(f"{prefix}Warning: Skipping segment {i} due to invalid 'start' type")
                    continue
                if not isinstance(segment.get("end"), (int, float)):
                    print(f"{prefix}Warning: Skipping segment {i} due to invalid 'end' type")
                    continue
                if not isinstance(segment.get("text"), str):
                    print(f"{prefix}Warning: Skipping segment {i} due to invalid 'text' type")
                    continue

                validated_segments.append(segment)
            
            segments = validated_segments

            print(f"{prefix}Segments: {len(segments)}")

            return segments

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON response: {e}\nResponse: {text}")
        except Exception as e:
            raise RuntimeError(f"Transcription error: {e}")
        finally:
            # Clean up uploaded file
            if audio_file is not None:
                try:
                    genai.delete_file(audio_file.name)
                except Exception:
                    pass

    def transcribe_text_only(self, audio_path: str, num_regions: int, label: str = None) -> list:
        """
        Transcribe audio and return ONLY text split into segments.
        Timestamps are NOT requested from Gemini — they come from VAD instead.

        Args:
            audio_path: Path to audio file (WAV format)
            num_regions: Number of speech regions detected by VAD in this chunk
            label: Display label for progress

        Returns:
            List of transcription text strings
        """
        audio_file = None
        prefix = f"   [{label}] " if label else "   "
        try:
            if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
                raise ValueError("GEMINI_API_KEY not set in config.py")

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)

            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

            upload_label = f"[{label}] Uploading" if label else "Uploading to Gemini API"
            progress = ProgressIndicator(upload_label)
            progress.start()
            audio_file = genai.upload_file(audio_path)
            progress.stop(f"{prefix}Uploaded ({file_size_mb:.1f} MB)")

            language_names = {
                "id": "Indonesian", "en": "English", "ja": "Japanese",
                "ko": "Korean", "zh": "Chinese", "ar": "Arabic",
                "es": "Spanish", "fr": "French", "de": "German",
                "it": "Italian", "pt": "Portuguese", "ru": "Russian",
                "hi": "Hindi", "th": "Thai", "vi": "Vietnamese",
            }

            if self.language == "auto":
                lang_instruction = "Detect the language automatically."
            else:
                lang_name = language_names.get(self.language, self.language)
                lang_instruction = f"Transcribe in {lang_name}."

            prompt = f"""{lang_instruction}

Transcribe the following audio. The audio contains {num_regions} speech segments separated by silence.
Return the result as a JSON array of strings, where each element is the transcription of one speech segment, in order.

Example for 3 segments:
["First segment text here", "Second segment text here", "Third segment text here"]

Requirements:
- Return exactly {num_regions} strings in the array
- Each string corresponds to one speech segment in chronological order
- If a segment is unclear, transcribe your best guess
- Return ONLY valid JSON array, no other text
"""

            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
                "response_mime_type": "application/json",
            }

            transcribe_label = f"[{label}] Transcribing" if label else "Gemini transcribing"
            progress = ProgressIndicator(transcribe_label)
            progress.start()
            response = model.generate_content(
                [prompt, audio_file], generation_config=generation_config
            )
            progress.stop(f"{prefix}Transcription received!")

            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            result = json.loads(text)

            if isinstance(result, list):
                texts = [str(item) for item in result]
            else:
                texts = [str(result)]

            print(f"{prefix}Segments: {len(texts)}")
            return texts

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON response: {e}\nResponse: {text}")
        except Exception as e:
            raise RuntimeError(f"Transcription error: {e}")
        finally:
            if audio_file is not None:
                try:
                    genai.delete_file(audio_file.name)
                except Exception:
                    pass

    def get_supported_languages(self) -> dict:
        """Return dictionary of supported language codes"""
        return {
            "id": "Indonesian",
            "en": "English",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ar": "Arabic",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "hi": "Hindi",
            "th": "Thai",
            "vi": "Vietnamese",
            "ms": "Malay",
            "nl": "Dutch",
            "pl": "Polish",
            "sv": "Swedish",
            "tr": "Turkish",
        }


if __name__ == "__main__":
    # Quick test - needs an audio file
    import sys

    if len(sys.argv) > 1:
        transcriber = Transcriber()
        segments = transcriber.transcribe(sys.argv[1])
        print(f"Segments: {len(segments)}")
        for i, seg in enumerate(segments[:3], 1):
            print(f"{i}. [{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
    else:
        print("Usage: python transcriber.py <audio_file.wav>")
