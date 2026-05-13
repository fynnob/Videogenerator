import asyncio
import json
import re
import edge_tts

def load_post():
    with open("post.json", "r") as f:
        return json.load(f)

def ticks_to_ass(t_100ns):
    s = t_100ns / 10000000.0
    h = int(s / 3600)
    m = int((s % 3600) / 60)
    sec = int(s % 60)
    cs = int((s * 100) % 100)
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

def spoken_len(word):
    """Letter count excluding trailing punctuation."""
    return max(len(re.sub(r"[^a-zA-Z0-9']", "", word)), 1)

def is_punctuation_only(word):
    return bool(re.match(r"^[^a-zA-Z0-9']+$", word))

END_OF_GROUP_PAUSE_TICKS = 5_000_000

def split_chunk_into_words(text_chunk, offset, duration):
    """
    Split a multi-word chunk into timed words.
    Punctuation at the end of a word (like the dot in 'blah.')
    has no sound — its time is absorbed into the word before it,
    not spread across all words equally.
    """
    sub_words = text_chunk.split()
    if not sub_words:
        return []

    # Calculate spoken length for each word (no punctuation)
    spoken_lengths = [spoken_len(w) for w in sub_words]
    total_spoken   = sum(spoken_lengths)

    # Distribute duration proportionally by spoken length only
    word_durations = [int(duration * (sl / total_spoken)) for sl in spoken_lengths]

    # Fix rounding so total matches exactly
    diff = duration - sum(word_durations)
    word_durations[-1] += diff

    # Build words list
    result = []
    current_offset = offset
    for w, dur in zip(sub_words, word_durations):
        result.append({
            "text":     w,
            "offset":   current_offset,
            "duration": dur
        })
        current_offset += dur

    return result

async def generate(text, voice, audio_out, subtitle_out):
    communicate = edge_tts.Communicate(text, voice, rate="+20%")
    words = []

    with open(audio_out, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                text_chunk = chunk["text"].strip()
                if not text_chunk:
                    continue

                if " " in text_chunk:
                    words.extend(split_chunk_into_words(
                        text_chunk, chunk["offset"], chunk["duration"]
                    ))
                else:
                    words.append({
                        "text":     text_chunk,
                        "offset":   chunk["offset"],
                        "duration": chunk["duration"]
                    })

    # Remove any punctuation-only tokens (e.g. a lone "." returned as its own chunk)
    words = [w for w in words if not is_punctuation_only(w["text"])]

    # --- Write ASS subtitle file ---
    ass_header = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,78,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,100,100,360,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    WORDS_PER_SCREEN = 6
    ass_events = ""

    for i in range(0, len(words), WORDS_PER_SCREEN):
        group = words[i:i + WORDS_PER_SCREEN]

        last_word   = group[-1]
        trimmed_end = last_word["offset"] + max(
            last_word["duration"] - END_OF_GROUP_PAUSE_TICKS, 100_000
        )

        for j, active_word in enumerate(group):
            start_time = ticks_to_ass(active_word["offset"])
            end_time   = ticks_to_ass(
                group[j + 1]["offset"] if j < len(group) - 1 else trimmed_end
            )

            line_parts = []
            for k, w in enumerate(group):
                if k == j:
                    line_parts.append(r"{\c&H0000FFFF&}" + w["text"] + r"{\c&H00FFFFFF&}")
                else:
                    line_parts.append(w["text"])

            ass_events += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{' '.join(line_parts)}\n"

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
