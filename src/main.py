"""
Audio Transcriber - Main Entry Point
Generate SRT subtitles from audio files using Google Gemini 2.0
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_loader import AudioLoader
from config import (
    CLEAN_TEMP_FILES,
    DEFAULT_OUTPUT_DIR,
    LANGUAGE,
    MODEL,
    SAMPLE_RATE,
    SEGMENT_DURATION,
    VERBOSE,
)
from srt_generator import SRTGenerator
from transcriber import Transcriber
from vad import find_speech_regions, group_regions, regions_to_segments


class AudioTranscriberApp:
    """Main application class for Audio Transcriber"""

    def __init__(self):
        self.audio_loader = AudioLoader(target_sample_rate=SAMPLE_RATE)
        self.transcriber = Transcriber()
        self.srt_generator = SRTGenerator()

    def transcribe_file(self, input_file: str, output_file: str = None, target_lang: str = None, is_bilingual: bool = False) -> str:
        """
        Transcribe audio/video file to SRT subtitle using VAD + Gemini pipeline.

        Pipeline:
        1. Convert audio to WAV
        2. VAD detects speech regions (accurate timestamps from audio energy)
        3. Group regions into chunks, extract audio per chunk
        4. Gemini transcribes each chunk (text only, no timestamps)
        5. Combine VAD timestamps + Gemini text → SRT
        """
        try:
            if VERBOSE:
                print(f"\n{'=' * 60}")
                print(f"📁 Processing: {os.path.basename(input_file)}")
                print(f"{'=' * 60}")

            audio, wav_path, duration = self.audio_loader.load_and_convert(input_file)

            if VERBOSE:
                print(f"\n📊 Audio Information:")
                print(f"   Duration: {duration:.2f} seconds")
                print(f"   Sample Rate: {audio.frame_rate} Hz")
            
            # Disable text wrapping for bilingual mode to keep 1 line per language
            if is_bilingual:
                self.srt_generator.max_chars_per_line = 2000
            else:
                self.srt_generator.max_chars_per_line = 40  # Reset to default
                print(f"   Channels: {audio.channels}")

            # Step 1: VAD - detect speech regions from audio energy
            print(f"\n🔍 Detecting speech regions (VAD)...")
            regions = find_speech_regions(wav_path)
            total_speech = sum(e - s for s, e in regions)
            mins_s, secs_s = divmod(int(total_speech), 60)
            print(f"   Found {len(regions)} speech regions ({mins_s}m{secs_s:02d}s of speech)")

            if not regions:
                print("   No speech detected in audio")
                if CLEAN_TEMP_FILES:
                    try:
                        os.remove(wav_path)
                    except Exception:
                        pass
                return None

            # Step 2: Group regions into API-friendly chunks
            groups = group_regions(regions, max_group_duration=30.0)
            print(f"   Grouped into {len(groups)} chunks for transcription")

            # Step 3: Transcribe each group with Gemini (text only)
            print(f"\n🤖 Transcribing with Gemini 2.0...")
            all_segments = []

            for i, group in enumerate(groups):
                chunk_num = i + 1
                label = f"Chunk {chunk_num}/{len(groups)}"
                group_regions_list = group["regions"]

                # Extract group audio
                start_ms = int(group["start"] * 1000)
                end_ms = int(group["end"] * 1000)
                chunk_audio = audio[start_ms:end_ms]

                # Save chunk to temp WAV
                chunk_wav = self.audio_loader.save_chunk(chunk_audio, i)

                try:
                    # Get segments directly from transcriber (handles translation/bilingual)
                    chunk_segments = self.transcriber.transcribe(
                        chunk_wav, 
                        chunk_duration=min(30.0, duration), 
                        label=label,
                        target_lang=target_lang,
                        is_bilingual=is_bilingual
                    )

                    # Adjust timestamps to be relative to the full audio
                    # chunk_segments timestamps are 0-based for the chunk
                    # we need to add the group's start time to align with original audio
                    start_offset = group["start"]
                    for segment in chunk_segments:
                        segment["start"] += start_offset
                        segment["end"] += start_offset
                        
                        # Add language labels for bilingual mode if translation exists
                        if is_bilingual and "\n" in segment["text"]:
                            parts = segment["text"].split("\n", 1)
                            if len(parts) == 2:
                                original = parts[0]
                                translation = parts[1]
                                # Format: Original (Grey) on new line, Translation on next line
                                # Using standard SRT font color tag
                                segment["text"] = f'<font color="#808080">{original}</font>\n{translation}'
                    
                    all_segments.extend(chunk_segments)

                except Exception as e:
                    print(f"   [{label}] Failed: {e}")
                finally:
                    if CLEAN_TEMP_FILES:
                        try:
                            os.remove(chunk_wav)
                        except Exception:
                            pass

            # Clean up temp WAV
            if CLEAN_TEMP_FILES:
                try:
                    os.remove(wav_path)
                except Exception:
                    pass

            if not all_segments:
                print("\n   No transcription segments produced")
                return None

            # Step 4: Generate SRT file
            if output_file is None:
                input_path = Path(input_file)
                output_path = input_path.with_suffix(".srt")
                output_file = str(output_path)
            else:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"\n📝 Generating SRT subtitle...")
            self.srt_generator.save_srt(all_segments, output_file)

            print(f"\n✅ Successfully generated: {output_file}")
            print(f"   Subtitle segments: {len(all_segments)}")

            return output_file

        except FileNotFoundError as e:
            print(f"\n❌ Error: {e}")
            return None
        except ValueError as e:
            print(f"\n❌ Error: {e}")
            return None
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            if VERBOSE:
                import traceback
                traceback.print_exc()
            return None

    def _distribute_texts(self, regions, texts):
        """
        Distribute texts across regions when counts don't match.
        Uses proportional distribution based on region duration.
        """
        if not texts or not regions:
            return []

        full_text = " ".join(t.strip() for t in texts if t and t.strip())
        words = full_text.split()
        if not words:
            return []

        total_duration = sum(e - s for s, e in regions)
        if total_duration <= 0:
            return []

        segments = []
        word_idx = 0

        for start, end in regions:
            region_dur = end - start
            proportion = region_dur / total_duration
            word_count = max(1, round(len(words) * proportion))

            region_words = words[word_idx:word_idx + word_count]
            word_idx += word_count

            if region_words:
                segments.append({
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "text": " ".join(region_words),
                })

        # Append any remaining words to last segment
        if word_idx < len(words) and segments:
            segments[-1]["text"] += " " + " ".join(words[word_idx:])

        return segments

    def transcribe_batch(self, input_files: list, output_dir: str = None, target_lang: str = None, is_bilingual: bool = False) -> list:
        """
        Transcribe multiple audio files

        Args:
            input_files: List of input audio file paths
            output_dir: Output directory for SRT files

        Returns:
            List of successfully generated SRT file paths
        """
        if not input_files:
            print("❌ No input files provided")
            return []

        # Set output directory
        if output_dir is None:
            output_dir = DEFAULT_OUTPUT_DIR

        print(f"\n🔄 Batch processing {len(input_files)} files...")
        if output_dir:
            print(f"📁 Output directory: {output_dir}")

        successful_files = []

        for i, input_file in enumerate(input_files, 1):
            print(f"\n{'=' * 60}")
            print(f"File {i}/{len(input_files)}")
            print(f"{'=' * 60}")

            # Determine output file path
            input_path = Path(input_file)
            if output_dir:
                output_path = Path(output_dir) / input_path.with_suffix(".srt").name
            else:
                output_path = input_path.with_suffix(".srt")

            # Transcribe
            result = self.transcribe_file(
                input_file,
                str(output_path),
                target_lang=target_lang,
                is_bilingual=is_bilingual
            )

            if result:
                successful_files.append(result)

        # Summary
        print(f"\n{'=' * 60}")
        print("📊 Batch Processing Summary")
        print(f"{'=' * 60}")
        print(f"Total files: {len(input_files)}")
        print(f"Successful: {len(successful_files)}")
        print(f"Failed: {len(input_files) - len(successful_files)}")

        if successful_files:
            print(f"\n✅ Generated SRT files:")
            for srt_file in successful_files:
                print(f"   - {srt_file}")

        return successful_files

    def watch_folder(self, watch_dir: str, output_dir: str = None):
        """
        Watch folder for new audio files and auto-transcribe

        Args:
            watch_dir: Directory to watch for audio files
            output_dir: Output directory for SRT files
        """
        from config import WATCH_EXTENSIONS, WATCH_INTERVAL

        print(f"\n👀 Watch Mode Activated")
        print(f"   Watching: {watch_dir}")
        print(f"   Output: {output_dir if output_dir else 'Same as input'}")
        print(f"   Extensions: {WATCH_EXTENSIONS}")
        print(f"   Interval: {WATCH_INTERVAL}s")
        print(f"\n🔄 Waiting for audio files... (Press Ctrl+C to stop)")

        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Track processed files
        processed_files = set()

        try:
            while True:
                # Scan directory for audio files
                watch_path = Path(watch_dir)
                extensions = WATCH_EXTENSIONS.split(",")

                for ext in extensions:
                    ext = ext.strip()
                    for audio_file in watch_path.glob(f"*{ext}"):
                        if str(audio_file) not in processed_files:
                            print(f"\n{'=' * 60}")
                            print(f"🎉 New audio file detected: {audio_file.name}")
                            print(f"{'=' * 60}")

                            # Determine output file
                            if output_dir:
                                output_file = str(
                                    Path(output_dir)
                                    / audio_file.with_suffix(".srt").name
                                )
                            else:
                                output_file = str(audio_file.with_suffix(".srt"))

                            # Transcribe
                            self.transcribe_file(str(audio_file), output_file)

                            # Mark as processed
                            processed_files.add(str(audio_file))

                # Wait before next scan
                time.sleep(WATCH_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n\n👋 Watch mode stopped")

    def run(self):
        """Run the CLI application"""
        parser = argparse.ArgumentParser(
            description="Generate SRT subtitles from audio & video files using Google Gemini 2.0",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Transcribe single file
  python main.py input.mp3 output.srt

  # Transcribe with specific language
  python main.py input.mp3 --language id

  # Batch process multiple files
  python main.py file1.mp3 file2.wav -o subs/

  # Watch folder for new files
  python main.py --watch audio_folder/ --output-dir subs/

  # Verbose mode for debugging
  python main.py input.mp3 --verbose
            """,
        )

        parser.add_argument(
            "input_files", nargs="*", help="Input audio file(s) to transcribe"
        )

        parser.add_argument("-o", "--output", help="Output SRT file or directory")

        parser.add_argument(
            "--output-dir", help="Output directory for batch processing"
        )

        parser.add_argument("--watch", help="Watch folder for new audio files")

        parser.add_argument(
            "--translate", "-t",
            type=str,
            help="Target language code for translation (e.g. 'id' for Indonesian, 'en' for English)"
        )

        parser.add_argument(
            "--bilingual", "-b",
            action="store_true",
            help="Output bilingual subtitles (Original + Translation). Requires --translate."
        )

        parser.add_argument(
            "--segment-duration", "-s",
            type=float,
            default=SEGMENT_DURATION,
            help="Subtitle segment duration in seconds"
        )

        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Verbose output for debugging"
        )

        parser.add_argument(
            "--language",
            "-l",
            default=LANGUAGE,
            help="Language code (default: auto-detect)",
        )

        parser.add_argument(
            "--keep-temp", action="store_true", help="Keep temporary WAV files"
        )

        args = parser.parse_args()

        # Update global config based on args
        global VERBOSE, CLEAN_TEMP_FILES
        VERBOSE = args.verbose
        CLEAN_TEMP_FILES = not args.keep_temp

        # Print banner
        print(f"\n{'=' * 60}")
        print("🎧🎬 Audio & Video Transcriber - VAD + Gemini 2.0")
        print(f"{'=' * 60}")
        print(f"Model: {MODEL}")
        print(
            f"Language: {args.language.upper() if args.language != 'auto' else 'Auto-detect'}"
        )
        print(f"Pipeline: VAD timestamps + Gemini text")

        # Run appropriate mode
        if args.watch:
            self.watch_folder(args.watch, args.output_dir or args.output)

        elif args.input_files:
            # Expand directories into individual supported files
            expanded_files = []
            for item in args.input_files:
                item_path = Path(item)
                if item_path.is_dir():
                    for f in sorted(item_path.iterdir()):
                        if f.is_file() and self.audio_loader.is_supported_format(str(f)):
                            expanded_files.append(str(f))
                    if not expanded_files:
                        print(f"❌ No supported audio/video files found in '{item}'")
                else:
                    expanded_files.append(item)

            if expanded_files:
                self.transcribe_batch(expanded_files, args.output_dir or args.output, target_lang=args.translate, is_bilingual=args.bilingual)
            else:
                print("❌ No files to process")
                sys.exit(1)

        else:
            parser.print_help()
            sys.exit(1)


def main():
    """Entry point"""
    app = AudioTranscriberApp()
    app.run()


if __name__ == "__main__":
    main()
