#!/usr/bin/env python3
"""CLI tool for batch processing video audio mixing."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from src.audio_processor import batch_mix_folder, find_video_files


def select_folder(title: str = "Select Folder") -> Path | None:
    """Open a native OS folder picker dialog."""
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    folder_path = filedialog.askdirectory(title=title)
    root.destroy()
    return Path(folder_path) if folder_path else None


def print_progress_bar(current: int, total: int, width: int = 40) -> None:
    """Print a progress bar to the terminal."""
    percent = current / total
    filled = int(width * percent)
    bar = "=" * filled + "-" * (width - filled)
    sys.stdout.write(f"\r[{bar}] {current}/{total} ({percent:.0%})")
    sys.stdout.flush()


def main() -> int:
    """Main CLI entry point."""
    print("Audio Mixer - Batch Processing")
    print("=" * 40)
    print()

    # Select source folder
    print("Select the source folder containing video files...")
    source_folder = select_folder("Select Video Folder")

    if not source_folder:
        print("No folder selected. Exiting.")
        return 1

    print(f"Source: {source_folder}")
    print()

    # Find video files
    print("Scanning for video files...")
    video_files = find_video_files(source_folder)

    if not video_files:
        print("No video files (.mp4, .mkv) found in this folder.")
        return 1

    print(f"Found {len(video_files)} video file(s):")
    for vf in video_files:
        print(f"  - {vf.relative_to(source_folder)}")
    print()

    # Output folder
    output_folder = source_folder.parent / f"{source_folder.name}_mixed"
    print(f"Output: {output_folder}")
    print()

    # Confirm
    response = input("Proceed with batch processing? [Y/n]: ").strip().lower()
    if response and response not in ("y", "yes"):
        print("Cancelled.")
        return 0

    print()
    print("Processing...")

    # Process files
    success_count = 0
    failure_count = 0
    errors: list[tuple[str, str]] = []

    total = len(video_files)
    for i, (input_path, output_path, error) in enumerate(
        batch_mix_folder(str(source_folder), str(output_folder))
    ):
        print_progress_bar(i + 1, total)

        if error:
            failure_count += 1
            rel_path = Path(input_path).relative_to(source_folder)
            errors.append((str(rel_path), error))
        else:
            success_count += 1

    print()  # New line after progress bar
    print()

    # Summary
    print("=" * 40)
    print("Complete!")
    print(f"  Succeeded: {success_count}")
    print(f"  Failed: {failure_count}")
    print(f"  Output: {output_folder}")

    if errors:
        print()
        print("Errors:")
        for file_path, error in errors:
            print(f"  - {file_path}: {error}")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
