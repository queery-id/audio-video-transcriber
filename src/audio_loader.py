"""
Audio loader module - Load and validate audio files
Supports multiple audio formats: MP3, WAV, FLAC, M4A, AAC, OGG, etc.
"""
import os

from pydub import AudioSegment
from pydub.utils import mediainfo


class AudioLoader:
    """Load and convert audio files for transcription"""

    SUPPORTED_FORMATS = {
        # Audio
        '.mp3', '.wav', '.flac', '.m4a', '.aac',
        '.ogg', '.wma', '.aiff', '.opus', '.amr', '.au', '.ra',
        # Video
        '.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.3gp'
    }

    def __init__(self, target_sample_rate: int = 16000):
        """
        Initialize audio loader

        Args:
            target_sample_rate: Target sample rate in Hz (default: 16000 for speech)
        """
        self.target_sample_rate = target_sample_rate

    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if file format is supported

        Args:
            file_path: Path to audio file

        Returns:
            True if format is supported, False otherwise
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_FORMATS

    def load_audio(self, file_path: str) -> AudioSegment:
        """
        Load audio file

        Args:
            file_path: Path to audio file

        Returns:
            AudioSegment object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Check if format is supported
        if not self.is_supported_format(file_path):
            raise ValueError(
                f"Unsupported audio format: {os.path.splitext(file_path)[1]}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        try:
            # Load audio file
            print(f"📂 Loading audio: {os.path.basename(file_path)}")
            audio = AudioSegment.from_file(file_path)

            # Get audio info
            duration = len(audio) / 1000.0  # Convert to seconds
            channels = audio.channels
            frame_rate = audio.frame_rate

            print(f"   Duration: {duration:.2f}s | Channels: {channels} | Sample Rate: {frame_rate}Hz")

            return audio

        except Exception as e:
            raise ValueError(f"Failed to load audio file: {e}")

    def convert_to_wav(self, audio: AudioSegment, output_path: str = None) -> str:
        """
        Convert audio to WAV format

        Args:
            audio: AudioSegment object
            output_path: Output WAV file path (optional)

        Returns:
            Path to the converted WAV file
        """
        if output_path is None:
            import tempfile
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, "audio_transcriber_temp.wav")

        # Resample if needed
        if audio.frame_rate != self.target_sample_rate:
            print(f"   Resampling from {audio.frame_rate}Hz to {self.target_sample_rate}Hz...")
            audio = audio.set_frame_rate(self.target_sample_rate)

        # Convert to mono if stereo (speech recognition typically works better with mono)
        if audio.channels > 1:
            print(f"   Converting from {audio.channels} channels to mono...")
            audio = audio.set_channels(1)

        # Export as WAV
        try:
            audio.export(output_path, format="wav")
            print(f"✅ Converted to WAV: {output_path}")
            return output_path
        except Exception as e:
            raise ValueError(f"Failed to convert to WAV: {e}")

    def load_and_convert(self, file_path: str, output_path: str = None) -> tuple:
        """
        Load audio file and convert to WAV format

        Args:
            file_path: Path to input audio file
            output_path: Output WAV file path (optional)

        Returns:
            Tuple of (AudioSegment, wav_file_path, duration)
        """
        # Load audio
        audio = self.load_audio(file_path)

        # Convert to WAV
        wav_path = self.convert_to_wav(audio, output_path)

        # Get duration
        duration = len(audio) / 1000.0  # Convert to seconds

        return audio, wav_path, duration

    def split_to_chunks(self, audio: AudioSegment, chunk_duration_sec: int) -> list:
        """
        Split audio into chunks of specified duration

        Args:
            audio: AudioSegment object
            chunk_duration_sec: Duration of each chunk in seconds

        Returns:
            List of tuples: (AudioSegment chunk, start_offset_seconds)
        """
        chunk_duration_ms = chunk_duration_sec * 1000
        chunks = []
        for start_ms in range(0, len(audio), chunk_duration_ms):
            end_ms = min(start_ms + chunk_duration_ms, len(audio))
            chunk = audio[start_ms:end_ms]
            chunks.append((chunk, start_ms / 1000.0))
        return chunks

    def save_chunk(self, chunk: AudioSegment, chunk_index: int, compress: bool = True) -> str:
        """
        Save an audio chunk to a temporary file.
        When compress=True (default), saves as OGG Opus (~8x smaller than WAV).
        Speech quality is preserved at 32kbps which is sufficient for transcription.

        Args:
            chunk: AudioSegment chunk
            chunk_index: Index number for unique filename
            compress: If True, export as OGG Opus. If False, export as WAV.

        Returns:
            Path to temporary audio file
        """
        import tempfile
        temp_dir = tempfile.gettempdir()

        if compress:
            chunk_path = os.path.join(temp_dir, f"transcriber_chunk_{chunk_index}.ogg")
            chunk.export(chunk_path, format="ogg", codec="libopus", bitrate="32k")
        else:
            chunk_path = os.path.join(temp_dir, f"transcriber_chunk_{chunk_index}.wav")
            chunk.export(chunk_path, format="wav")

        return chunk_path

    def get_audio_info(self, file_path: str) -> dict:
        """
        Get audio file information without loading the entire file

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with audio info
        """
        try:
            info = mediainfo(file_path)
            return {
                'format': info.get('format_name', 'unknown'),
                'duration': float(info.get('duration', 0)),
                'bit_rate': info.get('bit_rate', 'unknown'),
                'sample_rate': info.get('sample_rate', 'unknown'),
                'channels': info.get('channels', 'unknown')
            }
        except Exception as e:
            return {
                'error': str(e)
            }


def validate_audio_file(file_path: str) -> bool:
    """
    Quick validation of audio file

    Args:
        file_path: Path to audio file

    Returns:
        True if valid, False otherwise
    """
    try:
        loader = AudioLoader()
        loader.load_audio(file_path)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # Quick test
    import sys
    if len(sys.argv) > 1:
        loader = AudioLoader()
        print(f"Validating: {sys.argv[1]}")
        print(f"Supported: {loader.is_supported_format(sys.argv[1])}")
        print(f"Info: {loader.get_audio_info(sys.argv[1])}")

        if validate_audio_file(sys.argv[1]):
            print("✅ Audio file is valid")
            audio, wav_path, duration = loader.load_and_convert(sys.argv[1])
            print(f"Duration: {duration:.2f}s")
            print(f"WAV file: {wav_path}")
        else:
            print("❌ Audio file is invalid")
    else:
        print("Usage: python audio_loader.py <audio_file>")
