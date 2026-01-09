"""FFmpeg audio/video processing operations."""

from typing import Any

import ffmpeg

from .models import AudioStreamInfo


def probe_video(file_path: str) -> dict[str, Any]:
    """
    Probe a video file and return full metadata.

    Args:
        file_path: Path to the video file

    Returns:
        Dictionary containing ffprobe output

    Raises:
        RuntimeError: If probing fails
    """
    try:
        return ffmpeg.probe(file_path)
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        raise RuntimeError(f"Failed to probe video: {stderr}")


def extract_audio_streams(file_path: str) -> list[AudioStreamInfo]:
    """
    Extract metadata for all audio streams in a video file.

    Args:
        file_path: Path to the video file

    Returns:
        List of AudioStreamInfo objects for each audio stream
    """
    probe_data = probe_video(file_path)
    audio_streams = []
    audio_index = 0

    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "audio":
            tags = stream.get("tags", {})

            audio_streams.append(
                AudioStreamInfo(
                    index=stream["index"],
                    stream_index=audio_index,
                    codec_name=stream.get("codec_name", "unknown"),
                    sample_rate=int(stream.get("sample_rate", 0)),
                    channels=int(stream.get("channels", 0)),
                    channel_layout=stream.get("channel_layout"),
                    language=tags.get("language"),
                    title=tags.get("title"),
                    duration=(
                        float(stream["duration"])
                        if stream.get("duration")
                        else None
                    ),
                )
            )
            audio_index += 1

    return audio_streams


def mix_audio_streams(
    input_path: str,
    output_path: str,
    volume_levels: dict[int, float],
) -> None:
    """
    Mix multiple audio streams with adjusted volumes into a single output.

    Args:
        input_path: Path to input video file
        output_path: Path for output video file
        volume_levels: Dictionary mapping audio stream index to volume level (0.0-2.0)

    Raises:
        ValueError: If no audio streams to mix
        RuntimeError: If FFmpeg processing fails
    """
    if not volume_levels:
        raise ValueError("No audio streams to mix")

    try:
        input_file = ffmpeg.input(input_path)

        # Get video stream (copy without re-encoding)
        video = input_file.video

        # Build audio streams with volume adjustments
        audio_streams = []
        for stream_index in sorted(volume_levels.keys()):
            volume = volume_levels[stream_index]
            audio = input_file[f"a:{stream_index}"].filter("volume", volume)
            audio_streams.append(audio)

        if len(audio_streams) == 1:
            # Single stream - just apply volume
            mixed_audio = audio_streams[0]
        else:
            # Multiple streams - use amix filter
            mixed_audio = ffmpeg.filter(
                audio_streams,
                "amix",
                inputs=len(audio_streams),
                duration="longest",
                normalize=0,  # Disable normalization to respect volume settings
            )

        # Output with video copy and mixed audio
        output = ffmpeg.output(
            video,
            mixed_audio,
            output_path,
            vcodec="copy",
            acodec="aac",
            audio_bitrate="192k",
        )

        # Run with overwrite
        output.overwrite_output().run(quiet=True)

    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        raise RuntimeError(f"FFmpeg processing failed: {stderr}")
