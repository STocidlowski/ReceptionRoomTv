"""player.py - A simple video player for the Reception Area TV.

This will ignore any files that start with a period or are hidden (e.g. `.ExampleHiddenShow`).

This will not play videos in a file if there are valid subdirectories with videos in the same directory.

"""
import logging
import os
import re
from itertools import cycle, islice
from subprocess import Popen, CalledProcessError
from pathlib import Path
from typing import Optional, List

# from pydantic import BaseModel
from dataclasses import dataclass, field


VIDEO_SOURCE_DIRECTORIES: list[str] = [
    "/mnt",
    "/home/shawn/ReceptionRoomTv/videos",
]

VALID_EXTENSIONS = (
    '.mp4', '.mkv', '.avi', '.flv', '.wmv', '.mov', '.webm', '.mpg', '.mpeg',
    '.m4v', '.3gp', '.3g2', '.f4v', '.m4p', '.mp2', '.mpe', '.mpv', '.m2v',
    '.vob', '.ogv', '.ogg', '.drc', '.gif', '.gifv', '.mng', '.qt', '.yuv',
    '.rm', '.rmvb', '.asf', '.amv', '.m2ts', '.ts', '.mts'
)

PLAYLIST_FILE: Path = Path("/tmp/playlist.txt")

def configure_logging():
    """Configure basic logging for the application."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def is_valid_directory(directory: Path) -> bool:
    """Check if the provided directory exists."""
    if not directory.exists():
        logging.debug(f"Directory '{directory}' not found. Skipping...")
        return False
    if not directory.is_dir():
        logging.debug(f"'{directory}' is not a directory. Skipping...")
        return False
    if directory.name.startswith("."):
        logging.debug(f"Directory '{directory}' is hidden. Skipping...")
        return False
    return True


def get_show_name(path: Path) -> str:
    """Returns the first non-generic folder in the path, searching upwards, skipping folders like 'season', 'disc', 'extras', etc."""
    generic_names = [
        'season', 'disc', 'extras', 'specials', 'bonus',
        's01', 's02', 's03', 's04', 's05', 's06', 's07', 's08', 's09', 's10',
        's11', 's12', 's13', 's14', 's15', 's16', 's17', 's18', 's19', 's20',
        's21', 's22', 's23', 's24', 's25', 's26', 's27', 's28', 's29', 's30',
        's31', 's32', 's33', 's34', 's35', 's36', 's37', 's38', 's39', 's40',
        's41', 's42', 's43', 's44', 's45', 's46', 's47', 's48', 's49', 's50',
    ]
    # Iterate up from the file's parent
    for part in path.parents:
        name = part.name
        if name and not any(generic in name.lower() for generic in generic_names):
            return name
    # fallback to immediate parent if nothing matched
    return path.parent.name


def get_videos(directory: Path) -> list[Path]:
    """Recursively search for video files starting from 'directory', sorting videos within each directory."""
    videos = []
    # List all items in the current directory
    for entry in directory.iterdir():
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            # Recursively collect videos from subdirectories
            videos.extend(get_videos(entry))
        elif entry.is_file() and entry.suffix.lower() in VALID_EXTENSIONS:
            videos.append(entry)
    # Sort videos in the current directory or accumulated from subdirectories
    videos.sort(key=lambda x: x.name)
    return videos


def find_show_directories(source_roots: list[Path]) -> list[Path]:
    show_directories = []
    for root_path in source_roots:
        if not is_valid_directory(root_path):
            continue

        for subdirectory in sorted(root_path.iterdir()):
            if not is_valid_directory(subdirectory):
                continue
            if "season" in subdirectory.name.lower():
                continue

            subdirs_with_videos = find_show_directories([subdirectory])
            if subdirs_with_videos:
                show_directories.extend(subdirs_with_videos)
                continue

            if get_videos(subdirectory):
                show_directories.append(subdirectory)
    return show_directories


def write_playlist(videos: list[Path]) -> None:
    """Write the given sorted list of video files to a playlist file."""
    try:
        with PLAYLIST_FILE.open("w") as playlist:
            for video in videos:
                playlist.write(f"{video}\n")
        logging.info(f"Playlist written to {PLAYLIST_FILE}")
    except OSError as e:
        logging.error(f"Failed to write playlist due to an OS error: {e}")


def play_videos(playlist: list[Path]) -> None:
    """Builds and plays the rotating playlist."""

    write_playlist(playlist)
    # print(f"Playlist written to {PLAYLIST_FILE}\n\n{playlist=}")
    try:
        logging.info(f"Playing videos from playlist: {PLAYLIST_FILE}")
        play_process = Popen(['mpv', '--fullscreen', '--no-terminal', '--loop-file=no', f'--playlist={PLAYLIST_FILE}'])
        play_process.wait()
    except CalledProcessError as e:
        logging.error(f"Failed to play videos: {e}")


# class Playlist(BaseModel):
#     show_name: str
#     videos: list[Path]
#     progress: int = 0
# 
#     def next_video(self):
#         if not self.videos:
#             raise ValueError("Playlist has no videos")
#         video = self.videos[self.progress]
#         self.progress = (self.progress + 1) % len(self.videos)
#         return video

@dataclass
class Playlist:
    show_name: str
    videos: List[Path]
    progress: int = field(default=0)

    def next_video(self):
        if not self.videos:
            raise ValueError("Playlist has no videos")
        video = self.videos[self.progress]
        self.progress = (self.progress + 1) % len(self.videos)
        return video


def build_show_playlists(show_paths: list[Path]) -> list[Playlist]:
    """Builds playlists for each show"""
    show_playlists: list[Playlist] = []

    for show_path in show_paths:
        videos = get_videos(show_path)
        if not videos:
            continue

        show_playlists.append(
            Playlist(
                show_name=get_show_name(show_path),
                videos=videos,
                progress=0
            )
        )
    return show_playlists


def build_unified_playlist(shows: list[Playlist], playlist_length: Optional[int] = 100) -> list[Path]:
    """Builds a playlist of videos from the given shows, with a maximum length of playlist_length."""
    round_robin = (show.next_video() for show in cycle(shows))
    return list(islice(round_robin, playlist_length))


if __name__ == "__main__":
    configure_logging()
    playlist_file_path = Path(os.getenv('PLAYLIST_FILE', str(PLAYLIST_FILE)))

    raw_dirs = os.getenv("VIDEO_SOURCE_DIRECTORIES")
    if raw_dirs:
        # allow colon-, semicolon- or comma-separated lists
        video_source_directories = [
            d for d in re.split(r"[:;,]", raw_dirs) if d.strip()
        ]
    else:
        video_source_directories = VIDEO_SOURCE_DIRECTORIES

    logging.info("Starting video playlist loop...")
    playlists: list[Playlist] = []

    try:
        while True:
            shows = find_show_directories([Path(p) for p in video_source_directories])
            playlists = build_show_playlists(shows)
            master_playlist = build_unified_playlist(playlists)

            play_videos(master_playlist)

    except KeyboardInterrupt:
        logging.info("Video player terminated by user.")
