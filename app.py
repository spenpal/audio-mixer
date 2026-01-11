"""Audio Mixer - Streamlit application for mixing video audio streams."""

from pathlib import Path

import streamlit as st

from src.audio_processor import (
    batch_mix_folder,
    extract_audio_streams,
    find_video_files,
    mix_audio_streams,
)
from src.file_manager import get_file_manager


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        # Single file mode
        "uploaded_file_path": None,
        "uploaded_file_name": None,
        "audio_streams": [],
        "mixed_output_path": None,
        # Batch mode
        "batch_source_folder": "",
        "batch_results": [],
        "batch_complete": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_audio_controls() -> dict[int, float]:
    """Render volume sliders for each audio stream and return volume levels."""
    volume_levels: dict[int, float] = {}

    for stream in st.session_state.audio_streams:
        st.markdown(f"**{stream.display_name}**")

        volume_percent = st.slider(
            label=f"Volume for {stream.display_name}",
            min_value=0,
            max_value=200,
            value=100,
            step=5,
            key=f"volume_stream_{stream.stream_index}",
            format="%d%%",
            label_visibility="collapsed",
        )

        volume_levels[stream.stream_index] = volume_percent / 100.0
        st.divider()

    return volume_levels


def handle_file_upload(uploaded_file) -> bool:
    """Handle file upload and extract audio streams. Returns True if successful."""
    # Check if this is a new file
    if st.session_state.uploaded_file_name == uploaded_file.name:
        return True

    file_manager = get_file_manager()

    try:
        # Save uploaded file
        st.session_state.uploaded_file_path = file_manager.save_uploaded_file(
            uploaded_file
        )
        st.session_state.uploaded_file_name = uploaded_file.name

        # Extract audio streams
        st.session_state.audio_streams = extract_audio_streams(
            st.session_state.uploaded_file_path
        )

        # Reset mixed output
        st.session_state.mixed_output_path = None

        return True

    except RuntimeError as e:
        st.error(f"Error reading video file: {e}")
        return False


def handle_mix_audio(volume_levels: dict[int, float]):
    """Process the audio mixing operation."""
    file_manager = get_file_manager()
    output_path = file_manager.get_output_path()

    try:
        mix_audio_streams(
            input_path=st.session_state.uploaded_file_path,
            output_path=output_path,
            volume_levels=volume_levels,
        )
        st.session_state.mixed_output_path = output_path
        st.success("Audio mixed successfully!")
        st.rerun()

    except (RuntimeError, ValueError) as e:
        st.error(f"Error mixing audio: {e}")


def render_mixed_output():
    """Render the mixed output video and download button."""
    output_path = st.session_state.mixed_output_path

    if not output_path or not Path(output_path).exists():
        return

    st.divider()
    st.subheader("Mixed Output")

    col_output, col_download = st.columns([3, 1])

    with col_output:
        st.video(output_path)

    with col_download:
        with open(output_path, "rb") as f:
            video_bytes = f.read()

        original_name = Path(st.session_state.uploaded_file_name).stem
        output_name = f"{original_name}_mixed.mp4"

        st.download_button(
            label="Download Mixed Video",
            data=video_bytes,
            file_name=output_name,
            mime="video/mp4",
            type="primary",
            use_container_width=True,
        )


def render_single_file_mode():
    """Render the single file upload and mixing interface."""
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Video File",
        type=["mp4", "mkv"],
        help="Upload a video file with multiple audio streams (MP4 or MKV)",
    )

    if uploaded_file is None:
        st.info("Please upload a video file to get started.")
        return

    if not handle_file_upload(uploaded_file):
        return

    # Check for audio streams
    num_streams = len(st.session_state.audio_streams)

    if num_streams == 0:
        st.error("No audio streams found in this video file.")
        return

    if num_streams == 1:
        st.warning(
            "This video has only one audio stream. You can still adjust its volume."
        )

    # Main layout: Video player | Audio controls
    col_video, col_controls = st.columns([2, 1])

    with col_video:
        st.subheader("Original Video")
        st.video(st.session_state.uploaded_file_path)

    with col_controls:
        st.subheader("Audio Streams")
        volume_levels = render_audio_controls()

        if st.button("Mix Audio", type="primary", use_container_width=True):
            with st.spinner("Processing video... This may take a moment."):
                handle_mix_audio(volume_levels)

    # Show mixed output if available
    render_mixed_output()


def render_batch_mode():
    """Render the batch processing interface."""
    st.markdown(
        "Process all videos in a folder recursively. "
        "Audio streams will be mixed at 100% volume (default levels)."
    )

    # Folder input
    source_folder = st.text_input(
        "Source Folder Path",
        value=st.session_state.batch_source_folder,
        placeholder="/path/to/your/video/folder",
        help="Enter the full path to the folder containing video files",
    )

    # Validate folder
    source_path = Path(source_folder) if source_folder else None
    folder_valid = source_path and source_path.exists() and source_path.is_dir()

    if source_folder and not folder_valid:
        st.error("Invalid folder path. Please enter a valid directory.")
        return

    if not source_folder:
        st.info("Enter a folder path to get started.")
        return

    # Show folder info
    video_files = find_video_files(source_path)
    num_files = len(video_files)

    if num_files == 0:
        st.warning("No video files (.mp4, .mkv) found in this folder.")
        return

    # Output folder preview
    output_folder = source_path.parent / f"{source_path.name}_mixed"

    st.markdown(f"**Found {num_files} video file(s)**")
    st.markdown(f"**Output folder:** `{output_folder}`")

    # Show file list in expander
    with st.expander("View files to process"):
        for vf in video_files:
            relative = vf.relative_to(source_path)
            st.text(str(relative))

    # Process button
    if st.button("Start Processing", type="primary", use_container_width=True):
        st.session_state.batch_source_folder = source_folder
        st.session_state.batch_results = []
        st.session_state.batch_complete = False

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()

        success_count = 0
        failure_count = 0

        for i, (input_path, output_path, error) in enumerate(
            batch_mix_folder(source_folder, str(output_folder))
        ):
            # Update progress
            progress = (i + 1) / num_files
            progress_bar.progress(progress)

            # Get relative path for display
            rel_path = Path(input_path).relative_to(source_path)
            status_text.text(f"Processing: {rel_path}")

            if error:
                failure_count += 1
                st.session_state.batch_results.append((str(rel_path), False, error))
            else:
                success_count += 1
                st.session_state.batch_results.append((str(rel_path), True, None))

        # Complete
        st.session_state.batch_complete = True
        status_text.empty()

        # Show results
        with results_container:
            if failure_count == 0:
                st.success(f"All {success_count} files processed successfully!")
            else:
                st.warning(
                    f"Completed: {success_count} succeeded, {failure_count} failed"
                )

            st.markdown(f"**Output saved to:** `{output_folder}`")

            # Show failures if any
            if failure_count > 0:
                with st.expander("View errors"):
                    for file_path, success, error in st.session_state.batch_results:
                        if not success:
                            st.error(f"**{file_path}**: {error}")


def main():
    st.set_page_config(
        page_title="Audio Mixer",
        page_icon="🎚️",
        layout="wide",
    )

    init_session_state()

    st.title("Audio Mixer")

    # Tab navigation
    tab_single, tab_batch = st.tabs(["Single File", "Batch Process"])

    with tab_single:
        st.markdown(
            "Upload a video with multiple audio streams, adjust volumes, and export."
        )
        render_single_file_mode()

    with tab_batch:
        render_batch_mode()


if __name__ == "__main__":
    main()
