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
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def build_video():
    audio_duration = get_duration(AUDIO_FILE)
    print(f"Audio duration: {audio_duration:.1f}s")

    # Sort all available chunks
    all_chunks = sorted(glob.glob(f"{CHUNKS_DIR}/chunk_*.mp4"))
    if not all_chunks:
        raise FileNotFoundError(f"No chunks found in {CHUNKS_DIR}/")

    # Pick a random starting chunk and a random start time within it
    start_chunk_index = random.randint(0, len(all_chunks) - 1)
    start_chunk       = all_chunks[start_chunk_index]
    chunk_duration    = get_duration(start_chunk)

    # Don't start in the last 10 seconds of a chunk to avoid a tiny useless slice
    max_start = max(0, chunk_duration - 10)
    start_offset = round(random.uniform(0, max_start), 2)

    print(f"Starting at {start_chunk} offset {start_offset:.1f}s")

    # Build the ordered chunk list starting from the chosen chunk,
    # wrapping around to the beginning if we run out
    num_chunks = len(all_chunks)
    ordered_chunks = [
        all_chunks[(start_chunk_index + i) % num_chunks]
        for i in range(num_chunks)
    ]

    # Keep adding chunks (cycling if needed) until we have enough footage
    selected = []
    total    = 0.0

    # First chunk starts at the random offset so only counts partial duration
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

    print(f"Using {len(selected)} chunk(s) = {total:.1f}s of video")

    # Write a concat list where each entry uses -ss for the start offset
    # We do this by re-encoding the first chunk trimmed, then concat the rest
    # Step 1: trim the first chunk from the random offset → first_part.mp4
    first_chunk_path, offset = selected[0]
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(offset),
        "-i", first_chunk_path,
        "-c", "copy",
        "first_part.mp4"
    ], check=True)

    # Step 2: build concat list (first_part + remaining full chunks)
    with open("concat_list.txt", "w") as f:
        f.write(f"file '{os.path.abspath('first_part.mp4')}'\n")
        for chunk_path, _ in selected[1:]:
            f.write(f"file '{os.path.abspath(chunk_path)}'\n")

    # Step 3: concatenate everything → raw_video.mp4
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "concat_list.txt",
        "-c", "copy", "raw_video.mp4"
    ], check=True)

    # Step 4: trim to exact audio length, layer audio, burn captions
    subtitle_style = (
        "FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,Outline=2,Bold=1,"
        "Alignment=2,MarginV=40"
    )
    
    # 🔧 FIX: Using relative path to avoid FFmpeg path parsing bugs
    subs_filter_path = SUBS_FILE

    subprocess.run([
        "ffmpeg", "-y",
        "-i", "raw_video.mp4",
        "-i", AUDIO_FILE,
        "-t", str(audio_duration),
        "-vf", f"subtitles={subs_filter_path}:force_style='{subtitle_style}'",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        OUTPUT
    ], check=True)

    print(f"Final video: {OUTPUT}")
    return OUTPUT

if __name__ == "__main__":
    build_video()
