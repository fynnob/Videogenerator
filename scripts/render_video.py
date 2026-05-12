import subprocess
import json
import os
import glob
import random

CHUNKS_DIR = "chunks"
AUDIO_FILE = "audio.mp3"
SUBS_FILE  = "captions.srt"
OUTPUT     = "output.mp4"

def get_duration(filepath):
    """Uses ffprobe to get the exact duration of a media file."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def build_video():
    # 1. Initialize Durations
    audio_duration = get_duration(AUDIO_FILE)
    print(f"🎬 Audio duration: {audio_duration:.1f}s")

    # 2. Select and Loop Video Footage
    all_chunks = sorted(glob.glob(f"{CHUNKS_DIR}/chunk_*.mp4"))
    if not all_chunks:
        raise FileNotFoundError(f"❌ No chunks found in {CHUNKS_DIR}/")

    start_chunk_index = random.randint(0, len(all_chunks) - 1)
    start_chunk       = all_chunks[start_chunk_index]
    chunk_duration    = get_duration(start_chunk)

    # Pick a random start point
    max_start = max(0, chunk_duration - 10)
    start_offset = round(random.uniform(0, max_start), 2)

    num_chunks = len(all_chunks)
    ordered_chunks = [
        all_chunks[(start_chunk_index + i) % num_chunks]
        for i in range(num_chunks)
    ]

    selected = []
    total    = 0.0
    first_available = chunk_duration - start_offset
    selected.append((ordered_chunks[0], start_offset))
    total += first_available

    chunk_cycle_index = 1
    while total < audio_duration:
        chunk = ordered_chunks[chunk_cycle_index % num_chunks]
        dur   = get_duration(chunk)
        selected.append((chunk, 0))
        total += dur
        chunk_cycle_index += 1

    # 3. Concatenation Process
    first_chunk_path, offset = selected[0]
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(offset), "-i", first_chunk_path,
        "-c", "copy", "first_part.mp4"
    ], check=True)

    with open("concat_list.txt", "w") as f:
        f.write(f"file '{os.path.abspath('first_part.mp4')}'\n")
        for chunk_path, _ in selected[1:]:
            f.write(f"file '{os.path.abspath(chunk_path)}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "concat_list.txt", "-c", "copy", "raw_video.mp4"
    ], check=True)

    # 4. Final Composition (Clean Video + Audio + Captions)
    
    # 🔧 Subtitle Styling (Roboto, Larger Font, moved up for Shorts UI)
    subtitle_style = (
        "FontName=Roboto-Bold,FontSize=24,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,Outline=2.5,BackColour=&H80000000,"
        "Shadow=1.5,Bold=1,Alignment=2,MarginV=120"
    )
    
    if not os.path.exists(SUBS_FILE) or os.path.getsize(SUBS_FILE) == 0:
        raise ValueError(f"❌ Subtitle file '{SUBS_FILE}' is missing or empty!")

    # The Final FFmpeg Render (No Card)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", "raw_video.mp4",
        "-i", AUDIO_FILE,
        "-t", str(audio_duration),
        "-vf", f"subtitles=filename='./{SUBS_FILE}':fontsdir='.':force_style='{subtitle_style}'",
        "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        OUTPUT
    ], check=True)

    print(f"✅ FINAL VIDEO GENERATED: {OUTPUT}")
    return OUTPUT

if __name__ == "__main__":
    build_video()
