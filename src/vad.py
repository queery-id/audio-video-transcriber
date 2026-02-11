"""
Voice Activity Detection (VAD) module
Detects speech regions in audio using energy-based analysis.
Timestamps come from actual audio signal, NOT from AI estimation.

Adapted from Autosub's approach: analyze RMS energy per audio frame,
use percentile threshold to distinguish speech from silence.
"""

import math
import struct
import wave


def _percentile(arr, percent):
    """Calculate percentile value from sorted array"""
    arr = sorted(arr)
    k = (len(arr) - 1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return arr[int(k)]
    d0 = arr[int(f)] * (c - k)
    d1 = arr[int(c)] * (k - f)
    return d0 + d1


def _rms_energy(data, sample_width):
    """Calculate RMS energy of audio data"""
    if sample_width == 2:
        fmt = "<%dh" % (len(data) // 2)
        samples = struct.unpack(fmt, data)
    elif sample_width == 1:
        samples = [s - 128 for s in data]
    elif sample_width == 4:
        fmt = "<%di" % (len(data) // 4)
        samples = struct.unpack(fmt, data)
    else:
        return 0

    if not samples:
        return 0

    sum_sq = sum(s * s for s in samples)
    return math.sqrt(sum_sq / len(samples))


def find_speech_regions(
    wav_path,
    frame_width=4096,
    min_region_size=0.5,
    max_region_size=6.0,
    energy_threshold_percentile=0.2,
):
    """
    Detect speech regions in a WAV file using energy-based VAD.

    Analyzes audio energy per frame. Frames above the energy threshold
    are speech; frames below are silence. Adjacent speech frames are
    grouped into regions.

    Args:
        wav_path: Path to WAV audio file
        frame_width: Number of audio frames per analysis chunk
        min_region_size: Minimum speech region duration in seconds
        max_region_size: Maximum speech region duration in seconds
        energy_threshold_percentile: Percentile of energy values to use as
            silence threshold (0.2 = bottom 20% is silence)

    Returns:
        List of (start_sec, end_sec) tuples for each speech region
    """
    reader = wave.open(wav_path, "rb")
    sample_width = reader.getsampwidth()
    rate = reader.getframerate()
    n_channels = reader.getnchannels()
    total_frames = reader.getnframes()

    total_duration = total_frames / rate
    chunk_duration = float(frame_width) / rate
    n_chunks = int(total_duration / chunk_duration)

    if n_chunks == 0:
        reader.close()
        return [(0, total_duration)]

    # Calculate energy for each chunk
    energies = []
    for _ in range(n_chunks):
        chunk = reader.readframes(frame_width)
        if not chunk:
            break
        energies.append(_rms_energy(chunk, sample_width * n_channels))

    reader.close()

    if not energies:
        return [(0, total_duration)]

    # Determine silence threshold from energy distribution
    threshold = _percentile(energies, energy_threshold_percentile)

    # Find speech regions
    elapsed_time = 0.0
    regions = []
    region_start = None

    for energy in energies:
        is_silence = energy <= threshold
        max_exceeded = region_start is not None and (elapsed_time - region_start) >= max_region_size

        if (max_exceeded or is_silence) and region_start is not None:
            if (elapsed_time - region_start) >= min_region_size:
                regions.append((region_start, elapsed_time))
            region_start = None

        elif region_start is None and not is_silence:
            region_start = elapsed_time

        elapsed_time += chunk_duration

    # Close any open region at the end
    if region_start is not None:
        if (elapsed_time - region_start) >= min_region_size:
            regions.append((region_start, elapsed_time))

    return regions


def group_regions(regions, max_group_duration=30.0, max_gap=2.0):
    """
    Group adjacent speech regions into larger chunks for efficient API calls.

    Adjacent regions with small gaps are merged. Groups are capped at
    max_group_duration to keep Gemini API calls reasonable.

    Args:
        regions: List of (start, end) tuples from find_speech_regions()
        max_group_duration: Maximum duration of a group in seconds
        max_gap: Maximum gap between regions to merge them

    Returns:
        List of dicts: [{'start': float, 'end': float, 'regions': [(s,e), ...]}]
    """
    if not regions:
        return []

    groups = []
    current_group = {
        "start": regions[0][0],
        "end": regions[0][1],
        "regions": [regions[0]],
    }

    for i in range(1, len(regions)):
        r_start, r_end = regions[i]
        gap = r_start - current_group["end"]
        new_duration = r_end - current_group["start"]

        if gap <= max_gap and new_duration <= max_group_duration:
            # Merge into current group
            current_group["end"] = r_end
            current_group["regions"].append(regions[i])
        else:
            # Start new group
            groups.append(current_group)
            current_group = {
                "start": r_start,
                "end": r_end,
                "regions": [regions[i]],
            }

    groups.append(current_group)
    return groups


def regions_to_segments(regions, texts):
    """
    Combine VAD regions with transcription texts into SRT segments.

    Args:
        regions: List of (start, end) tuples
        texts: List of transcription strings (same length as regions)

    Returns:
        List of dicts with 'start', 'end', 'text' keys
    """
    segments = []
    for (start, end), text in zip(regions, texts):
        if text and text.strip():
            segments.append({
                "start": round(start, 3),
                "end": round(end, 3),
                "text": text.strip(),
            })
    return segments


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        regions = find_speech_regions(sys.argv[1])
        total_speech = sum(e - s for s, e in regions)
        print(f"Found {len(regions)} speech regions ({total_speech:.1f}s of speech)")
        for i, (s, e) in enumerate(regions[:20], 1):
            print(f"  {i:3d}. [{s:7.2f}s - {e:7.2f}s] ({e-s:.2f}s)")
        if len(regions) > 20:
            print(f"  ... and {len(regions) - 20} more")

        groups = group_regions(regions)
        print(f"\nGrouped into {len(groups)} chunks:")
        for i, g in enumerate(groups, 1):
            dur = g['end'] - g['start']
            print(f"  {i}. [{g['start']:.2f}s - {g['end']:.2f}s] ({dur:.1f}s, {len(g['regions'])} regions)")
    else:
        print("Usage: python vad.py <audio.wav>")
