import os
import random
import time
from subprocess import Popen

# USB directory path
usb_directory = "/mnt/usb1"

videos = []


def get_videos():
    """Populate the global 'videos' list with video files from the USB directory."""
    global videos
    videos = []
    if os.path.exists(usb_directory):
        for file in os.listdir(usb_directory):
            if file.lower().endswith(('.mp4', '.mkv')):
                videos.append(os.path.join(usb_directory, file))
    else:
        print(f"USB directory '{usb_directory}' not found. Ensure the USB is connected and mounted.")


def play_videos():
    """Shuffle and play videos using mpv. If no videos are found, retry after a delay."""
    global videos
    if not videos:
        get_videos()
        if not videos:  # If still empty, wait and retry
            print("No videos found in the USB directory. Retrying in 5 seconds...")
            time.sleep(5)
            return
    random.shuffle(videos)
    for video in videos:
        print(f"Playing video: {video}")
        # Launch mpv with no interface and fullscreen
        # rpi hardware decoding
        # play_process = Popen(['mpv', '--vo=rpi', '--hwdec=mmal', '--no-terminal', '--fullscreen', '--loop-file=no', video])
        # rpi hardware decoding on rpi4
        play_process = Popen(['mpv', '--vo=drm', '--drm-connector=0.HDMA-A-1', '--hwdec=mmal', '--no-terminal', '--fullscreen', '--loop-file=no', video])
        # play_process = Popen(['mpv', '--no-terminal', '--fullscreen', '--loop-file=no', video])
        play_process.wait()  # Wait for the video to finish


if __name__ == "__main__":
    print("Starting video loop...")
    while True:
        play_videos()
