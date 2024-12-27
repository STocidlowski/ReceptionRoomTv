import os
import random
import time
from subprocess import Popen

# Directory containing the videos
directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'videos')

videos = []


def get_videos():
    """Populate the global 'videos' list with video files from the directory."""
    global videos
    videos = [os.path.join(directory, file) for file in os.listdir(directory) if file.lower().endswith('.mp4')]


def play_videos():
    """Shuffle and play videos using mpv. If no videos are found, retry after a delay."""
    global videos
    if not videos:
        get_videos()
        if not videos:  # If still empty, wait and retry
            print("No videos found. Retrying in 5 seconds...")
            time.sleep(5)
            return
    random.shuffle(videos)
    for video in videos:
        print(f"Playing video: {video}")
        # Launch mpv with no interface and fullscreen
        play_process = Popen(['mpv', '--no-terminal', '--fullscreen', '--loop-file=no', video])
        play_process.wait()  # Wait for the video to finish


if __name__ == "__main__":
    print("Starting video loop...")
    while True:
        play_videos()
