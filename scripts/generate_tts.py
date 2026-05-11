import asyncio
import json
import edge_tts

def load_post():
    with open("post.json", "r") as f:
        return json.load(f)

def format_srt_time(t_100ns):
    """Converts 100-nanosecond ticks to SRT time format HH:MM:SS,mmm"""
    s = t_100ns / 10000000.0
    h = int(s / 3600)
    m = int((s % 3600) / 60)
    sec = int(s % 60)
    ms = int((s * 1000) % 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

async def generate(text, voice, audio_out, subtitle_out):
    communicate = edge_tts.Communicate(text, voice)
    words = []

    with open(audio_out, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                text_chunk = chunk["text"].strip()
                if " " in text_chunk:
                    sub_words = text_chunk.split()
                    if len(sub_words) > 0:
                        word_dur = chunk["duration"] // len(sub_words)
                        for idx, w in enumerate(sub_words):
                            words.append({
                                "text": w,
                                "offset": chunk["offset"] + (idx * word_dur),
                                "duration": word_dur
                            })
                else:
                    words.append(chunk)

    # ---------------------------------------------------------
    # 🔧 NEW: Dynamically find the exact end of the title!
    # ---------------------------------------------------------
    title_duration_sec = 4.0 # Safe fallback
    for i in range(len(words) - 1):
        end_current = words[i]["offset"] + words[i]["duration"]
        start_next = words[i+1]["offset"]
        
        # We added "... \n\n" after the title, which causes a pause longer than 0.4 seconds. 
        # When we detect that specific pause, we know the title is finished!
        if (start_next - end_current) > 4000000: 
            title_duration_sec = end_current / 10000000.0
            break

    # Add a tiny 0.2s visual buffer so it doesn't vanish mid-breath
    title_duration_sec += 0.2
    
    with open("title_duration.txt", "w") as f:
        f.write(str(round(title_duration_sec, 2)))

    # ---------------------------------------------------------
    # Custom Subtitle Builder (Karaoke highlighting + word limits)
    # ---------------------------------------------------------
    WORDS_PER_SCREEN = 4
    srt_content = ""
    srt_index = 1

    # Loop through words in batches of 4
    for i in range(0, len(words), WORDS_PER_SCREEN):
        group = words[i:i+WORDS_PER_SCREEN]
        
        for j, active_word in enumerate(group):
            start_time = active_word["offset"]
            
            if j < len(group) - 1:
                end_time = group[j+1]["offset"]
            else:
                end_time = active_word["offset"] + active_word["duration"]

            srt_start = format_srt_time(start_time)
            srt_end = format_srt_time(end_time)
            
            line_text = []
            for k, w in enumerate(group):
                if k == j:
                    line_text.append(f'<font color="#ffff00">{w["text"]}</font>')
                else:
                    line_text.append(w["text"])
            
            srt_content += f"{srt_index}\n{srt_start} --> {srt_end}\n{' '.join(line_text)}\n\n"
            srt_index += 1

    with open(subtitle_out, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"✅ Audio saved to {audio_out}")
    print(f"✅ Subtitles saved to {subtitle_out}")

if __name__ == "__main__":
    post = load_post()

    full_text = f"{post['title']}... \n\n{post['text']}"
    voice     = post["voice"]

    asyncio.run(generate(
        text=full_text,
        voice=voice,
        audio_out="audio.mp3",
        subtitle_out="captions.srt"
    ))
