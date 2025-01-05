import logging
import time
from subprocess import Popen, CalledProcessError
from pathlib import Path


def configure_logging():
    """Configure basic logging for the application."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


VIDEO_SOURCE_DIRECTORIES: list[str] = [
    "/mnt/usb1",
    "/usr/shawn/WaitingRoomTv/videos"
]

VALID_EXTENSIONS = (
    '.mp4', '.mkv', '.avi', '.flv', '.wmv', '.mov', '.webm', '.mpg', '.mpeg',
    '.m4v', '.3gp', '.3g2', '.f4v', '.m4p', '.mp2', '.mpe', '.mpv', '.m2v',
    '.vob', '.ogv', '.ogg', '.drc', '.gif', '.gifv', '.mng', '.qt', '.yuv',
    '.rm', '.rmvb', '.asf', '.amv', '.m2ts', '.ts', '.mts'
)

PLAYLIST_FILE: Path = Path("/tmp/playlist.txt")


def is_valid_directory(directory: Path) -> bool:
    """Check if the provided directory exists."""
    if not directory.exists():
        logging.warning(f"Directory '{directory}' not found. Skipping...")
        return False
    return True


def get_videos(directory: Path) -> list[Path]:
    """Recursively search for video files starting from 'directory', sorting videos within each directory."""
    videos = []
    # List all items in the current directory
    for entry in directory.iterdir():
        if entry.is_dir():
            # Recursively collect videos from subdirectories
            videos += get_videos(entry)
        elif entry.is_file() and entry.suffix.lower() in VALID_EXTENSIONS:
            videos.append(entry)
    # Sort videos in the current directory or accumulated from subdirectories
    videos.sort(key=lambda x: x.name)
    return videos


def gather_videos() -> list[Path]:
    """Gather videos from all configured directories."""
    all_videos = []
    for directory_path in map(Path, VIDEO_SOURCE_DIRECTORIES):
        if is_valid_directory(directory_path):
            # Start the recursive video collection process
            directory_videos = get_videos(directory_path)
            all_videos.extend(directory_videos)
    return all_videos


def write_playlist(videos: list[Path]) -> None:
    """Write the given sorted list of video files to a playlist file."""
    try:
        with PLAYLIST_FILE.open("w") as playlist:
            for video in videos:
                playlist.write(f"{video}\n")
        logging.info(f"Playlist written to {PLAYLIST_FILE}")
    except OSError as e:
        logging.error(f"Failed to write playlist due to an OS error: {e}")


def play_videos() -> None:
    """Fetch video files, create a playlist, and play videos using VLC."""
    videos = gather_videos()
    if not videos:
        logging.info("No videos found in the configured directories. Retrying in 10 seconds...")
        time.sleep(10)
        return

    write_playlist(videos)
    try:
        logging.info(f"Playing videos from playlist: {PLAYLIST_FILE}")
        play_process = Popen(['mpv', '--fullscreen', '--no-terminal', '--loop-file=no', f'--playlist={PLAYLIST_FILE}'])
        play_process.wait()
    except CalledProcessError as e:
        logging.error(f"Failed to play videos: {e}")


if __name__ == "__main__":
    configure_logging()
    logging.info("Starting video playlist loop...")
    try:
        while True:
            play_videos()
    except KeyboardInterrupt:
        logging.info("Video player terminated by user.")
