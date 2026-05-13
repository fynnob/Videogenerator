import asyncio
import json
import edge_tts

def load_post():
    with open("post.json", "r") as f:
        return json.load(f)

def ticks_to_ass(t_100ns):
    """Converts 100-nanosecond ticks to ASS time format H:MM:SS.cc"""
    s = t_100ns / 10000000.0
    h = int(s / 3600)
    m = int((s % 3600) / 60)
    sec = int(s % 60)
    cs = int((s * 100) % 100)  # centiseconds
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

# How many 100ns ticks to shave off the last word of each group.
# 500ms = 5_000_000 ticks. Tune up/down if still drifting.
END_OF_GROUP_PAUSE_TICKS = 5_000_000

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
                    total_letters = sum(len(w) for w in sub_words)
                    current_offset = chunk["offset"]
                    for w in sub_words:
                        weight = len(w) / total_letters
                        word_dur = int(chunk["duration"] * weight)
                        words.append({
                            "text": w,
                            "offset": current_offset,
                            "duration": word_dur
                        })
                        current_offset += word_dur
                else:
                    words.append({
                        "text": chunk["text"].strip(),
                        "offset": chunk["offset"],
                        "duration": chunk["duration"]
                    })

    # --- Write ASS subtitle file ---
    ass_header = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,68,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,100,100,360,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    WORDS_PER_SCREEN = 6
    ass_events = ""

    for i in range(0, len(words), WORDS_PER_SCREEN):
        group = words[i:i + WORDS_PER_SCREEN]

        for j, active_word in enumerate(group):
            start_time = ticks_to_ass(active_word["offset"])

            if j < len(group) - 1:
                # Not the last word in the group — next word's offset is the end, this is fine
                end_time = ticks_to_ass(group[j + 1]["offset"])
            else:
                # Last word in the group: trim the pause that punctuation adds.
                # Without this, the highlight sits too long and drifts behind the audio.
                trimmed_duration = max(active_word["duration"] - END_OF_GROUP_PAUSE_TICKS, 100_000)
                end_time = ticks_to_ass(active_word["offset"] + trimmed_duration)

            # Build line: highlighted word in yellow, rest in white
            line_parts = []
            for k, w in enumerate(group):
                if k == j:
                    line_parts.append(r"{\c&H0000FFFF&}" + w["text"] + r"{\c&H00FFFFFF&}")
                else:
                    line_parts.append(w["text"])

            line_text = " ".join(line_parts)
            ass_events += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{line_text}\n"

    with open(subtitle_out, "w", encoding="utf-8") as f:
        f.write(ass_header + ass_events)

    print(f"Audio saved: {audio_out}")
    print(f"Subtitles saved: {subtitle_out} ({len(words)} words, ASS format)")

if __name__ == "__main__":
    post = load_post()
    full_text = f"{post['title']}... \n\n{post['text']}"
    voice     = post["voice"]

    asyncio.run(generate(
        text=full_text,
        voice=voice,
        audio_out="audio.mp3",
        subtitle_out="captions.ass"
    ))