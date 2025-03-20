from moviepy import *
import re
import glob

def split_into_sentences(text):
    """
    Splits a string into a list of sentences. Looks for
    '.', '?', or '!' followed by whitespace. This helps
    captions not overflow from the vertical video.
    """

    sentences = re.split(r'(?<=[.?!])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def generate_video(video_path: str, tts_path: str, caption_duration:list, threads: int, bg = False) -> str:
    '''Used for ICS 31 Generation. bg auto set to False, set to True if want WII music.'''

    result = VideoFileClip(video_path)
    audio = concatenate_audioclips(tts_path)

    if bg: # If chosen to have background music, go ahead and find specified file. For this example, we using wii_shop

        music_files = glob.glob("**/wii_shop.mp3", recursive=True)
        if music_files:
            background_music = AudioFileClip(music_files[0])
        else:
            raise FileNotFoundError("wii_shop.mp3 not found")
        
        background_music = background_music.with_duration(audio.duration) # Edit the duration of file so it matches with tts duration.
        audio = CompositeAudioClip([background_music, audio])

    result = result.with_audio(audio).with_duration(audio.duration).with_fps(60)

    subtitle_clips = []

    font_files = glob.glob("**/OpenSans-ExtraBold.ttf", recursive=True)
    if font_files:
        font_path = font_files[0]
    else:
        raise FileNotFoundError("OpenSans-ExtraBold.ttf not found. Specify in vid.py if you want another font.")

    for start, end, script in caption_duration:
        duration = end - start
        # Split the script into sentences for captions to fit
        sentences = split_into_sentences(script)
        if not sentences:
            continue

        total_chars = sum(len(s) for s in sentences)

        # Ensure broken down captions match TTS voice
        current_time = start
        for sentence in sentences:
            sentence_duration = duration * (len(sentence) / total_chars)
            txt_clip = (
                TextClip(
                    text=sentence,
                    font=font_path,
                    font_size=50,
                    color='white',
                    stroke_color='black',
                    stroke_width=3,
                    size=(int(result.w * 0.9), int(result.h * 0.9)),
                    method='caption'
                )
                .with_position(('center'))
                .with_start(current_time)
                .with_duration(sentence_duration)
            )
            subtitle_clips.append(txt_clip)
            current_time += sentence_duration

    # Add everything together (Video with audio and captions / subtitles)
    final_clip = CompositeVideoClip([result] + subtitle_clips)

    output_path = "../temp/output.mp4" # Can change to any directory you want.

    final_clip.write_videofile(
        output_path,
        threads=threads,
        fps=60,
        codec="libx264",
        preset="ultrafast", # Faster rendering
        audio_codec="aac"
    )

    return output_path
