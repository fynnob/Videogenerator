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
                    # 🔧 NEW: Calculate duration based on letter count instead of even split
                    total_letters = sum(len(w) for w in sub_words)
                    current_offset = chunk["offset"]
                    
                    for w in sub_words:
                        # Determine what % of the time this word deserves
                        weight = len(w) / total_letters
                        word_dur = int(chunk["duration"] * weight)
                        
                        words.append({
                            "text": w,
                            "offset": current_offset,
                            "duration": word_dur
                        })
                        current_offset += word_dur # Move the start time for the next word
                else:
                    words.append(chunk)

    # ... (Keep your title_duration.txt logic the same) ...

    # 🔧 NEW: Word limit set to 6
    WORDS_PER_SCREEN = 6
    srt_content = ""
    srt_index = 1

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
