# Audio-Video Transcriber 🎧🎬

A powerful, batch-processing tool to transcribe and translate audio/video files using **Google Gemini 2.0 Flash**. Supports standard transcription, translation to Indonesian, and bilingual subtitles (Original + Indonesian).

## Features
- **Accurate Transcription**: Powered by Google's Gemini 2.0 Flash model.
- **Multi-Format Support**: Works with MP4, MKV, AVI, MP3, WAV, FLAC, M4A, and more.
- **Smart Chunking**: Automatically splits long files using Voice Activity Detection (VAD) for better accuracy.
- **Translation Modes**:
  - **Transcribe Only**: Standard SRT output in original language.
  - **Translate**: Translates directly to Indonesian.
  - **Bilingual**: Generates two lines per subtitle (Original in Grey, Translation in White).
- **Interactive Menu**: Easy-to-use `run.bat` interface.

## Quick Start
1.  **Clone/Download** this repository.
2.  **Get a API Key**: Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
3.  **Setup Config**:
    - Rename `src/config.example.py` to `src/config.py`.
    - Open `src/config.py` and paste your API Key.
4.  **Run**: Double-click `run.bat`.

## Requirements
- Python 3.10+
- FFmpeg (must be added to system PATH)

## Usage
Simply run `run.bat` and choose an option:
- **[F]**: Input a specific file path (supports Drag & Drop).
- **[I]**: Process all files in `input/` folder (Transcribe only).
- **[T]**: Translate all files in `input/` folder.
- **[B]**: Create bilingual subtitles for all files in `input/` folder.

## License
MIT License