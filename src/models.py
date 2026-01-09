"""Data models for audio stream information."""

from dataclasses import dataclass


@dataclass
class AudioStreamInfo:
    """Represents metadata for a single audio stream in a video file."""

    index: int
    stream_index: int  # The audio-specific index (0, 1, 2...)
    codec_name: str
    sample_rate: int
    channels: int
    channel_layout: str | None = None
    language: str | None = None
    title: str | None = None
    duration: float | None = None

    @property
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        parts = [f"Stream {self.stream_index}"]

        if self.title:
            parts.append(f"({self.title})")

        if self.language:
            parts.append(f"[{self.language.upper()}]")

        parts.append(f"- {self.codec_name.upper()}")
        parts.append(f"{self.channels}ch")

        if self.sample_rate:
            parts.append(f"@ {self.sample_rate // 1000}kHz")

        return " ".join(parts)
