import subprocess
import json
import os
import glob

CHUNKS_DIR = "chunks"       # folder with chunk_01.mp4, chunk_02.mp4 etc.
AUDIO_FILE = "audio.mp3"
SUBS_FILE  = "captions.srt"
OUTPUT     = "output.mp4"

def get_duration(filepath):
    """Get duration of a media file in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def build_video():
    audio_duration = get_duration(AUDIO_FILE)
    print(f"🎙️  Audio duration: {audio_duration:.1f}s")

    # Sort chunks
    chunks = sorted(glob.glob(f"{CHUNKS_DIR}/chunk_*.mp4"))
    if not chunks:
        raise FileNotFoundError(f"No chunks found in {CHUNKS_DIR}/")

    # Figure out how many chunks we need
    selected = []
    total = 0.0
    while total < audio_duration:
        for chunk in chunks:
            selected.append(chunk)
            total += get_duration(chunk)
            if total >= audio_duration:
                break

    print(f"📹 Using {len(selected)} chunk(s) = {total:.1f}s of video")

    # Write ffmpeg concat list
    with open("concat_list.txt", "w") as f:
        for c in selected:
            f.write(f"file '{os.path.abspath(c)}'\n")

    # Step 1: Concatenate chunks → raw_video.mp4
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "concat_list.txt",
        "-c", "copy", "raw_video.mp4"
    ], check=True)

    # Step 2: Trim to exact audio length, add audio, burn captions
    # Subtitle style: white bold text, black outline, bottom-center
    subtitle_style = (
        "FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,Outline=2,Bold=1,"
        "Alignment=2,MarginV=40"
    )
    abs_subs = os.path.abspath(SUBS_FILE)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", "raw_video.mp4",
        "-i", AUDIO_FILE,
        "-t", str(audio_duration),
        "-vf", f"subtitles={abs_subs}:force_style='{subtitle_style}'",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        OUTPUT
    ], check=True)

    print(f"✅ Final video: {OUTPUT}")
    return OUTPUT

if __name__ == "__main__":
    build_video()
