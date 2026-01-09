# Audio Mixer

A Streamlit app for mixing video audio streams with adjustable volumes.

## Requirements

- Python 3.13+
- FFmpeg installed on your system (`brew install ffmpeg` on macOS)

## Installation

```bash
uv sync
```

## Usage

```bash
uv run streamlit run app.py
```

1. Upload a video file (MP4 or MKV) with multiple audio streams
2. Adjust the volume sliders for each audio stream (0-200%)
3. Click "Mix Audio" to combine the streams
4. Preview the mixed video and download it
