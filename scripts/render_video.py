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

    # Pick a random start point, leaving at least 10s of buffer
    max_start = max(0, chunk_duration - 10)
    start_offset = round(random.uniform(0, max_start), 2)

    print(f"📍 Starting at {start_chunk} offset {start_offset:.1f}s")

    num_chunks = len(all_chunks)
    ordered_chunks = [
        all_chunks[(start_chunk_index + i) % num_chunks]
        for i in range(num_chunks)
    ]

    selected = []
    total    = 0.0

    # Handle the first partial chunk
    first_available = chunk_duration - start_offset
    selected.append((ordered_chunks[0], start_offset))
    total += first_available

    # Cycle through chunks until the audio is fully covered
    chunk_cycle_index = 1
    while total < audio_duration:
        chunk = ordered_chunks[chunk_cycle_index % num_chunks]
        dur   = get_duration(chunk)
        selected.append((chunk, 0))
        total += dur
        chunk_cycle_index += 1

    print(f"🎞️  Stitching {len(selected)} chunk(s) to cover {total:.1f}s of footage")

    # 3. Concatenation Process
    # Trim the first chunk to the starting offset
    first_chunk_path, offset = selected[0]
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(offset),
        "-i", first_chunk_path,
        "-c", "copy",
        "first_part.mp4"
    ], check=True)

    # Build the concat list for FFmpeg
    with open("concat_list.txt", "w") as f:
        f.write(f"file '{os.path.abspath('first_part.mp4')}'\n")
        for chunk_path, _ in selected[1:]:
            f.write(f"file '{os.path.abspath(chunk_path)}'\n")

    # Merge video chunks into one raw file
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "concat_list.txt",
        "-c", "copy", "raw_video.mp4"
    ], check=True)

    # 4. Final Composition (Card, Subtitles, Audio)
    
    # Custom Subtitle Styling (Roboto Bold, Shadow, High Positioning)
    subtitle_style = (
        "FontName=Roboto,FontSize=22,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,Outline=2.5,BackColour=&H80000000,"
        "Shadow=1.5,Bold=1,Alignment=2,MarginV=80"
    )
    
    if not os.path.exists(SUBS_FILE) or os.path.getsize(SUBS_FILE) == 0:
        raise ValueError(f"❌ Subtitle file '{SUBS_FILE}' is missing or empty!")

    subs_filter_path = f"./{SUBS_FILE}"

    # Read the dynamic title end-time from the TTS script
    title_duration = 4.0
    if os.path.exists("title_duration.txt"):
        with open("title_duration.txt", "r") as f:
            title_duration = float(f.read().strip())
            
    print(f"📺 Displaying Reddit Card for the first {title_duration} seconds.")

    # The Final FFmpeg Render
    subprocess.run([
        "ffmpeg", "-y",
        "-i", "raw_video.mp4",
        "-i", AUDIO_FILE,
        "-i", "card.png", 
        "-t", str(audio_duration),
        "-filter_complex", 
        # Layer 1: Overlay the card over the video for title_duration
        f"[0:v][2:v]overlay=(W-w)/2:(H-h)/2:enable='between(t,0,{title_duration})'[with_card];"
        # Layer 2: Burn subtitles using Roboto font from local directory
        f"[with_card]subtitles=filename='{subs_filter_path}':fontsdir='.':force_style='{subtitle_style}'[final_v]",
        "-map", "[final_v]", 
        "-map", "1:a:0",
        "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        OUTPUT
    ], check=True)

    print(f"✅ FINAL VIDEO GENERATED: {OUTPUT}")
    return OUTPUT

if __name__ == "__main__":
    build_video()
