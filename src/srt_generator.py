"""
SRT Generator module - Generate SRT subtitle format from transcription segments
"""

import re
from typing import Dict, List


class SRTGenerator:
    """Generate SRT subtitle files from transcription segments"""

    def __init__(self, max_chars_per_line: int = 40, max_lines_per_block: int = 2):
        """
        Initialize SRT generator

        Args:
            max_chars_per_line: Maximum characters per subtitle line
            max_lines_per_block: Maximum lines per subtitle block
        """
        self.max_chars_per_line = max_chars_per_line
        self.max_lines_per_block = max_lines_per_block

    def format_timestamp(self, seconds: float) -> str:
        """
        Convert seconds to SRT timestamp format (HH:MM:SS,mmm)

        Args:
            seconds: Time in seconds (float)

        Returns:
            Timestamp string in format HH:MM:SS,mmm
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

    def wrap_text(self, text: str) -> List[str]:
        """
        Wrap text to fit within character limit per line, respecting existing newlines
        """
        final_lines = []
        # Split by existing newlines first
        paragraphs = text.split('\n')
        
        for paragraph in paragraphs:
            # Remove extra spaces within paragraph but keep it as one block for wrapping
            paragraph = " ".join(paragraph.split())
            if not paragraph:
                continue
                
            words = paragraph.split()
            current_line = []
            
            for word in words:
                test_line = " ".join(current_line + [word])
                if len(test_line) <= self.max_chars_per_line:
                    current_line.append(word)
                else:
                    if current_line:
                        final_lines.append(" ".join(current_line))
                    current_line = [word]
            
            if current_line:
                final_lines.append(" ".join(current_line))
        
        return final_lines

    def split_long_blocks(self, lines: List[str]) -> List[str]:
        """
        Split blocks that exceed maximum lines

        Args:
            lines: List of text lines

        Returns:
            List of blocks (each block is a string)
        """
        blocks = []
        current_block = []

        for line in lines:
            current_block.append(line)
            if len(current_block) >= self.max_lines_per_block:
                blocks.append("\n".join(current_block))
                current_block = []

        # Add remaining lines
        if current_block:
            blocks.append("\n".join(current_block))

        return blocks

    def generate_segment(self, index: int, start: float, end: float, text: str) -> str:
        """
        Generate a single SRT segment

        Args:
            index: Segment number
            start: Start time in seconds
            end: End time in seconds
            text: Transcribed text

        Returns:
            SRT segment string
        """
        # Format timestamps
        start_time = self.format_timestamp(start)
        end_time = self.format_timestamp(end)

        # Wrap text
        lines = self.wrap_text(text)

        # Build segment
        segment = f"{index}\n"
        segment += f"{start_time} --> {end_time}\n"
        segment += "\n".join(lines) + "\n"

        return segment

    def generate_srt(self, segments: List[Dict]) -> str:
        """
        Generate complete SRT content from segments

        Args:
            segments: List of transcription segments
                     Each segment should have: 'start', 'end', 'text'

        Returns:
            Complete SRT content as string
        """
        srt_lines = []

        for idx, segment in enumerate(segments, start=1):
            start_time = segment.get("start", 0)
            end_time = segment.get("end", start_time)
            text = segment.get("text", "")

            # Skip empty segments
            if not text.strip():
                continue

            # Generate segment
            segment_str = self.generate_segment(idx, start_time, end_time, text)
            srt_lines.append(segment_str)

        return "\n".join(srt_lines)

    def save_srt(self, segments: List[Dict], output_path: str) -> None:
        """
        Save SRT content to file

        Args:
            segments: List of transcription segments
            output_path: Path to output SRT file
        """
        srt_content = self.generate_srt(segments)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

    def generate_with_overlapping(
        self, segments: List[Dict], overlap_duration: float = 0.5
    ) -> str:
        """
        Generate SRT with overlapping segments for smoother transitions

        Args:
            segments: List of transcription segments
            overlap_duration: Overlap duration in seconds

        Returns:
            Complete SRT content as string
        """
        # Adjust end times for overlap
        adjusted_segments = []
        for i, segment in enumerate(segments):
            seg_copy = segment.copy()
            if i < len(segments) - 1:
                next_start = segments[i + 1].get("start", seg_copy["end"])
                seg_copy["end"] = min(seg_copy["end"], next_start - overlap_duration)
            adjusted_segments.append(seg_copy)

        return self.generate_srt(adjusted_segments)


def format_time_to_srt(seconds: float) -> str:
    """
    Utility function to convert seconds to SRT timestamp format

    Args:
        seconds: Time in seconds

    Returns:
        Timestamp in HH:MM:SS,mmm format
    """
    generator = SRTGenerator()
    return generator.format_timestamp(seconds)


def generate_srt_from_segments(
    segments: List[Dict],
    output_path: str,
    max_chars_per_line: int = 40,
    max_lines_per_block: int = 2,
) -> None:
    """
    Convenience function to generate SRT file from segments

    Args:
        segments: List of transcription segments
        output_path: Path to output SRT file
        max_chars_per_line: Maximum characters per line
        max_lines_per_block: Maximum lines per subtitle block
    """
    generator = SRTGenerator(
        max_chars_per_line=max_chars_per_line, max_lines_per_block=max_lines_per_block
    )
    generator.save_srt(segments, output_path)


def parse_srt_timestamp(timestamp: str) -> float:
    """
    Parse SRT timestamp to seconds

    Args:
        timestamp: Timestamp in HH:MM:SS,mmm format

    Returns:
        Time in seconds
    """
    match = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", timestamp)
    if match:
        hours, minutes, seconds, millis = map(int, match.groups())
        return hours * 3600 + minutes * 60 + seconds + millis / 1000.0
    return 0.0


if __name__ == "__main__":
    # Quick test
    test_segments = [
        {
            "start": 0.0,
            "end": 3.5,
            "text": "Halo semua, selamat datang di podcast kami.",
        },
        {
            "start": 3.5,
            "end": 7.2,
            "text": "Hari ini kita akan membahas tentang teknologi AI.",
        },
        {
            "start": 7.2,
            "end": 11.0,
            "text": "Khususnya tentang kemajuan dalam speech recognition yang sangat menakjubkan.",
        },
    ]

    generator = SRTGenerator(max_chars_per_line=35)
    srt_content = generator.generate_srt(test_segments)
    print(srt_content)

    # Save test file
    test_output = "test_subtitle.srt"
    generator.save_srt(test_segments, test_output)
    print(f"\n✅ Test SRT saved to: {test_output}")
