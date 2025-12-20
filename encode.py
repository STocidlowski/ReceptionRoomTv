""" Encode.py - A simple video encoder for the Reception Area TV. Encodes in H264 at 480, in order to easily play on a raspberry pi

This output plays well on Raspberry Pi Zero 2W
"""

import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def get_stream_info(filepath: str, stream_type: str) -> list[dict]:
    """Get stream information for audio or subtitles, including codec_name."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', stream_type,
        '-show_entries', 'stream=index,codec_name:stream_tags=language,title',
        '-of', 'json',
        filepath
    ]
    try:
        output = subprocess.check_output(cmd, text=True).strip()
        probe_result = json.loads(output)
        streams = probe_result.get('streams', [])
        stream_info = []
        for stream in streams:
            stream_info.append({
                'index': stream.get('index'),
                'codec_name': stream.get('codec_name'),
                'language': stream.get('tags', {}).get('language'),
                'title': stream.get('tags', {}).get('title')
            })
        return stream_info
    except subprocess.CalledProcessError as e:
        print(f"Error getting {stream_type} stream info: {e}")
        return []


def select_stream(streams: list[dict], preferred_lang: str = 'eng') -> Optional[int]:
    """Select a stream based on preferred language; defaults to the first stream if preferred not found."""
    if not streams:
        return None

    # Check for preferred language first
    for stream in streams:
        if stream.get('language') and stream['language'].lower() == preferred_lang.lower():
            return stream['index']

    # If preferred language not found, return first available stream
    return streams[0]['index']


def get_show_name(filepath: str) -> str:
    """ Returns the first non-generic folder in the path, searching upwards, skipping folders
    like 'season', 'disc', 'extras', etc.
    """
    generic_names = ['season', 'disc', 'extras', 'specials', 'bonus',
                     'S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08', 'S09', 'S10', 'S11', 'S12', 'S13', 'S14', 'S15', 'S16', 'S17', 'S18', 'S19', 'S20', 'S21', 'S22', 'S23', 'S24',
                     ]
    parts = os.path.normpath(filepath).split(os.sep)
    # skip filename itself
    for part in reversed(parts[:-1]):
        lowered = part.lower()
        if not any(generic in lowered for generic in generic_names):
            return part
    # fallback to parent if nothing matched
    return os.path.basename(os.path.dirname(filepath))


def make_safe_name(name: str) -> str:
    name = re.sub(r'[:;,\\\']', '', name)
    name = re.sub(r'\.+', '.', name).strip('.')
    return name


def escape_ffmpeg_subtitle_path(path: Path) -> str:
    """
    Return an FFmpeg-ready subtitle filename that can be embedded like:
        subtitles=filename='<result>':force_style='FontSize=16'
    Works for local, UNC and SMB paths on Windows/macOS/Linux.
    """
    path_str = path.resolve().as_posix()
    path_str = path_str.replace('\\', r'\\')  # Escape Windows backslashes explicitly (may not be needed for POSIX paths)
    special_chars = "\\':;"  # Characters that must be escaped
    for char in special_chars:
        path_str = path_str.replace(char, "\\" + char)
    return path_str


def process_video(filepath: Path, destination_dir: Path) -> None:
    """Process a single video file using pathlib."""
    video_name = filepath.stem
    output_safe = make_safe_name(video_name)

    output_tag = '-transcode-480p'
    output_safe = re.sub(r'\b(480p|720p|1080p|2160p|4k|remux|transcode)\b', '', output_safe, flags=re.IGNORECASE)
    output_safe = re.sub(r'\.+', '.', output_safe).strip('.')

    show_name_safe = make_safe_name(get_show_name(filepath))

    destination_dir = destination_dir / show_name_safe
    destination_dir.mkdir(parents=True, exist_ok=True)

    output_file = Path.joinpath(destination_dir,f'{output_safe}{output_tag}.mp4')

    if output_file.exists():
        print(f"Skipping {filepath.name} - output file already exists")
        return

    try:
        audio_streams = get_stream_info(str(filepath), 'a')
        subtitle_streams = get_stream_info(str(filepath), 's')

        audio_index = select_stream(audio_streams, preferred_lang='eng')

        subtitle_index = None
        for sub in subtitle_streams:
            if sub['codec_name'] not in ['hdmv_pgs_subtitle']:
                subtitle_index = sub['index']
                break

        preferred_sub_index = select_stream(
            [sub for sub in subtitle_streams if sub['codec_name'] not in ['hdmv_pgs_subtitle']],
            preferred_lang='eng'
        )
        subtitle_index = preferred_sub_index if preferred_sub_index is not None else subtitle_index
        encode_command = ['ffmpeg', '-y', '-i', str(filepath.resolve())]
        encode_command.extend(['-map', '0:0'])

        if audio_index is not None:
            encode_command.extend(['-map', f'0:{audio_index}'])
        # Construct video filter chain:
        video_filters = ["scale=-2:480"]

        if "'" in str(filepath):
            print(f"WARNING: Filename contains single quotes, temporarily disabling subtitles: {filepath.name}")
            subtitle_index = None

        # If subtitles exist, carefully add filter
        if subtitle_index is not None:
            encode_command.extend(['-map', f'0:{subtitle_index}', '-c:s', 'mov_text'])

            escaped_sub_file = escape_ffmpeg_subtitle_path(filepath)
            subtitle_filter = f"subtitles={escaped_sub_file}:force_style=FontSize=16"
            video_filters.append(subtitle_filter)

        # Finalize filter command
        if video_filters:
            encode_command.extend(['-vf', ','.join(video_filters)])

        output_file = output_file.resolve()

        # Encoding options
        encode_command.extend([
            '-c:v', 'libx264',
            '-profile:v', 'baseline',
            '-level', '3.0',
            '-preset', 'fast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '128k',
            str(output_file)
        ])

        process = subprocess.Popen(
            encode_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1024
        )

        while True:
            output = process.stderr.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip(), flush=True)

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            print(f"Error: FFmpeg exited with code {process.returncode}")
            if stderr:
                print(f"FFmpeg error output: {stderr}")
            output_file.unlink(missing_ok=True)
        else:
            print(f"Successfully processed {filepath.name}")

    except Exception as e:
        print(f"Error processing {filepath.name}: {str(e)}")
        output_file.unlink(missing_ok=True)



def encode_videos(source_dirs: list[str], destination_dir: str):
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    for source_dir in source_dirs:
        print(f"\nProcessing source directory: {source_dir}\n")
        video_files = [
            os.path.join(dp, f)
            for dp, _, filenames in os.walk(source_dir)
            for f in filenames
            if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))
        ]
        for filepath in video_files:
            process_video(Path(filepath), Path(destination_dir))


if __name__ == "__main__":
    source_dirs = [
        r"G:\Media\Movies\Elf (2003)",
    ]
    # Set your output destination
    destination_dir = "E:\\"

    encode_videos(source_dirs, destination_dir)
