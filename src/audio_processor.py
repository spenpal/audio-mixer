"""FFmpeg audio/video processing operations."""

from collections.abc import Generator
from pathlib import Path
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


def find_video_files(
    folder: Path,
    extensions: tuple[str, ...] = (".mp4", ".mkv"),
) -> list[Path]:
    """
    Recursively find all video files in a folder.

    Args:
        folder: Path to the folder to search
        extensions: Tuple of video file extensions to include

    Returns:
        Sorted list of video file paths
    """
    video_files = []
    for ext in extensions:
        video_files.extend(folder.rglob(f"*{ext}"))
        video_files.extend(folder.rglob(f"*{ext.upper()}"))
    return sorted(set(video_files))


def batch_mix_folder(
    source_folder: str,
    output_folder: str,
    video_extensions: tuple[str, ...] = (".mp4", ".mkv"),
) -> Generator[tuple[str, str | None, str | None], None, None]:
    """
    Process all videos in a folder recursively, mixing audio at default volumes.

    Args:
        source_folder: Path to the source folder containing videos
        output_folder: Path to the output folder for processed videos
        video_extensions: Tuple of video file extensions to process

    Yields:
        Tuples of (input_path, output_path | None, error_message | None)
        - On success: (input_path, output_path, None)
        - On failure: (input_path, None, error_message)
    """
    source_path = Path(source_folder)
    output_path = Path(output_folder)

    video_files = find_video_files(source_path, video_extensions)

    for video_file in video_files:
        input_path_str = str(video_file)

        try:
            # Calculate relative path and create output path
            relative_path = video_file.relative_to(source_path)
            # Always output as .mp4 since we're encoding to AAC
            output_file = output_path / relative_path.with_suffix(".mp4")

            # Create parent directories if needed
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Extract audio streams
            audio_streams = extract_audio_streams(input_path_str)

            if not audio_streams:
                yield (input_path_str, None, "No audio streams found")
                continue

            # Create default volume levels (100% for all streams)
            volume_levels = {stream.stream_index: 1.0 for stream in audio_streams}

            # Mix audio
            mix_audio_streams(input_path_str, str(output_file), volume_levels)

            yield (input_path_str, str(output_file), None)

        except Exception as e:
            yield (input_path_str, None, str(e))
