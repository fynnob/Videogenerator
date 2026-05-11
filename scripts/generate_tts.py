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
                
            # 🔧 FIX: Catch both boundary types!
            elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                text_chunk = chunk["text"].strip()
                
                # If it's a full sentence, mathematically split it into individual words
                if " " in text_chunk:
                    sub_words = text_chunk.split()
                    if len(sub_words) > 0:
                        # Estimate how long each word takes by dividing total time
                        word_dur = chunk["duration"] // len(sub_words)
                        for idx, w in enumerate(sub_words):
                            words.append({
                                "text": w,
                                "offset": chunk["offset"] + (idx * word_dur),
                                "duration": word_dur
                            })
                else:
                    # It's already a single word
                    words.append(chunk)

    # ---------------------------------------------------------
    # Custom Subtitle Builder (Karaoke highlighting + word limits)
    # ---------------------------------------------------------
    WORDS_PER_SCREEN = 4
    srt_content = ""
    srt_index = 1

    # Loop through words in batches of 4
    for i in range(0, len(words), WORDS_PER_SCREEN):
        group = words[i:i+WORDS_PER_SCREEN]
        
        # Create a subtitle frame for each spoken word in the current group
        for j, active_word in enumerate(group):
            start_time = active_word["offset"]
            
            # To prevent screen flickering, extend the frame's end time 
            # seamlessly to the start of the next word.
            if j < len(group) - 1:
                end_time = group[j+1]["offset"]
            else:
                end_time = active_word["offset"] + active_word["duration"]

            srt_start = format_srt_time(start_time)
            srt_end = format_srt_time(end_time)
            
            line_text = []
            for k, w in enumerate(group):
                if k == j:
                    # Highlight the active word in yellow
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

    # Add an ellipsis and newlines to force a natural pause after the title
    full_text = f"{post['title']}... \n\n{post['text']}"
    voice     = post["voice"]

    asyncio.run(generate(
        text=full_text,
        voice=voice,
        audio_out="audio.mp3",
        subtitle_out="captions.srt"
    ))
