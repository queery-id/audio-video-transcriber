"""
Configuration for Audio Transcriber (Gemini 2.0)
COPY THIS FILE TO config.py AND FILL IN YOUR API KEY
"""

# =============================================================================
# GEMINI 2.0 API SETTINGS
# =============================================================================
# Gemini model to use for transcription
# Options: 'gemini-2.0-flash-exp', 'gemini-2.0-flash-thinking-exp', 'gemini-1.5-pro'
MODEL = 'gemini-2.0-flash'

# Your Gemini API key (get FREE at https://aistudio.google.com/app/apikey)
# 1. Go to https://aistudio.google.com/app/apikey
# 2. Sign in with your Google account
# 3. Create a new API key
# 4. Paste it below
GEMINI_API_KEY = 'YOUR_API_KEY_HERE'

# =============================================================================
# TRANSCRIPTION SETTINGS
# =============================================================================
# Language code: 'id' (Indonesian), 'en' (English), 'ja' (Japanese), 'auto' (auto-detect)
# Auto-detect works but setting explicit language improves accuracy
LANGUAGE = 'auto'

# Segment duration for subtitles (in seconds)
# Shorter segments = more subtitle lines but may break sentences
# Recommended: 3-5 for dialogue, 5-10 for monologues
SEGMENT_DURATION = 5

# Temperature for generation (0.0 = more deterministic, 1.0 = more creative)
# Lower is better for transcription
TEMPERATURE = 0.0

# Maximum tokens to generate per API call
MAX_OUTPUT_TOKENS = 8192

# Duration of each audio chunk for processing (seconds)
# Long audio is split into chunks for better timestamp accuracy
# Recommended: 300 (5 min) for speech-heavy, 600 (10 min) for sparse audio
CHUNK_DURATION = 300

# =============================================================================
# AUDIO PROCESSING SETTINGS
# =============================================================================
# Target sample rate for conversion (Hz)
# Most audio processing works best at 16kHz or 44.1kHz
SAMPLE_RATE = 16000

# Number of audio channels (1 = mono, 2 = stereo)
# Mono is sufficient for speech and reduces file size
CHANNELS = 1

# =============================================================================
# OUTPUT SETTINGS
# =============================================================================
# Default output directory for SRT files
# Leave empty to save in same directory as input file
DEFAULT_OUTPUT_DIR = ''

# Verbose mode: True = show detailed progress, False = show minimal output
VERBOSE = False

# Clean mode: True = delete temp files after processing, False = keep temp files
CLEAN_TEMP_FILES = True

# =============================================================================
# WATCH MODE SETTINGS
# =============================================================================
# Time interval to check for new files (in seconds)
# Only applies when using --watch mode
WATCH_INTERVAL = 5

# File extensions to watch for (comma-separated)
WATCH_EXTENSIONS = ".mp3,.wav,.flac,.m4a,.aac,.ogg,.wma,.mp4,.mkv,.avi,.mov"
