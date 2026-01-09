"""Temporary file management for video processing."""

import shutil
import tempfile
from pathlib import Path

import streamlit as st


class TempFileManager:
    """Manages temporary files for video processing."""

    def __init__(self):
        self._temp_dir = tempfile.mkdtemp(prefix="audio_mixer_")

    @property
    def temp_dir(self) -> Path:
        return Path(self._temp_dir)

    def save_uploaded_file(self, uploaded_file) -> str:
        """
        Save a Streamlit uploaded file to temp directory.

        Args:
            uploaded_file: Streamlit UploadedFile object

        Returns:
            Path to saved file
        """
        file_path = self.temp_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return str(file_path)

    def get_output_path(self, suffix: str = ".mp4") -> str:
        """Generate a path for output file."""
        return str(self.temp_dir / f"mixed_output{suffix}")

    def cleanup(self) -> None:
        """Remove all temporary files."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


def get_file_manager() -> TempFileManager:
    """Get or create the file manager in session state."""
    if "file_manager" not in st.session_state:
        st.session_state.file_manager = TempFileManager()
    return st.session_state.file_manager
