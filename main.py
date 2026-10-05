from gpt_api import generate_script
import os
import glob
import gc
from uuid import uuid4
from tiktokvoice import tts

# Configure ImageMagick for MoviePy (must be done before importing MoviePy text classes)
import moviepy_config

from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.AudioClip import concatenate_audioclips, CompositeAudioClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.video.fx.resize import resize

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
FONT_PATH = os.path.join(BASE_DIR, "OpenSans-ExtraBold.ttf")

# Video dimensions - reduced for lower memory usage
VIDEO_WIDTH = 576  # Reduced from 720
VIDEO_HEIGHT = 1024  # Reduced from 1280


def ensure_directories():
    """Ensure temp and videos directories exist"""
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)


def find_background_video():
    """Find the minecraft background video"""
    video_files = glob.glob(os.path.join(BASE_DIR, "**", "minecraft1*.mp4"), recursive=True)
    if video_files:
        return video_files[0]
    # Fallback to videos directory
    fallback = os.path.join(VIDEOS_DIR, "minecraft1.mp4")
    if os.path.exists(fallback):
        return fallback
    raise FileNotFoundError("minecraft1.mp4 not found. Please add it to the videos folder.")


def find_timer_audio():
    """Find the clock/timer audio file"""
    timer_files = glob.glob(os.path.join(BASE_DIR, "**", "clock.mp3"), recursive=True)
    if timer_files:
        return timer_files[0]
    # Fallback to audio directory
    fallback = os.path.join(AUDIO_DIR, "clock.mp3")
    if os.path.exists(fallback):
        return fallback
    raise FileNotFoundError("clock.mp3 not found. Please add it to the audio folder.")


def find_background_music():
    """Find the Wii Shop background music file"""
    music_files = glob.glob(os.path.join(BASE_DIR, "**", "wii_shop.mp3"), recursive=True)
    if music_files:
        return music_files[0]
    # Fallback to audio directory
    fallback = os.path.join(AUDIO_DIR, "wii_shop.mp3")
    if os.path.exists(fallback):
        return fallback
    return None  # Background music is optional


def create_tts_audio_file(text, temp_files_list):
    """Create TTS audio file and return path (not clip) to save memory"""
    ensure_directories()
    filepath = os.path.join(TEMP_DIR, f"{uuid4()}.mp3")
    tts(text, "en_us_001", filename=filepath)
    temp_files_list.append(filepath)
    return filepath


def get_audio_duration(filepath):
    """Get duration of audio file without keeping it in memory"""
    clip = AudioFileClip(filepath)
    duration = clip.duration
    clip.close()
    return duration


def create_caption_text_clip(text, duration, position='center'):
    """Create a styled caption text clip for overlay on video"""
    # Clean up text formatting
    formatted_text = text.replace("\\n", "\n")

    # Use @ prefix to tell ImageMagick to read font directly from file path
    font_reference = f"@{FONT_PATH}"

    text_clip = TextClip(
        txt=formatted_text,
        fontsize=65,  # Reduced from 80 for smaller resolution
        color='white',
        font=font_reference,
        size=(VIDEO_WIDTH - 30, None),
        method='caption',
        align='center',
        stroke_color='black',
        stroke_width=1
    ).set_duration(duration).set_position(('center', position))

    return text_clip


def cleanup_temp_files(file_paths):
    """Clean up temporary audio files"""
    for filepath in file_paths:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Warning: Could not delete temp file {filepath}: {e}")


def generate(topic: str, progress_callback=None) -> str:
    """
    Generate a quiz video for the given topic with minecraft background.
    Optimized for low-memory environments (t3.small instances).

    Args:
        topic: The ICS 31 topic to generate questions about
        progress_callback: Optional callback function(progress, message) for status updates

    Returns:
        Path to the generated video file
    """
    ensure_directories()
    temp_files = []

    def update_progress(progress, message):
        if progress_callback:
            progress_callback(progress, message)
        print(f"[{progress}%] {message}")

    try:
        update_progress(5, "Generating quiz questions...")
        script = generate_script(topic)

        # Find background video, timer audio, and background music
        video_path = find_background_video()
        timer_path = find_timer_audio()
        bg_music_path = find_background_music()

        update_progress(15, "Generating audio files...")

        # Intro text
        intro1 = "Welcome to the ICS 31 Brain Rot Quiz!"
        intro2 = "Score a 4 out of 5 to graduate Rizz University"

        # Store audio file paths and timing info (not clips - saves memory)
        audio_file_paths = []
        captions_durations = []  # (start_time, end_time, caption_text)
        current_time = 0

        # Generate intro audio files
        intro1_path = create_tts_audio_file(intro1, temp_files)
        intro1_duration = get_audio_duration(intro1_path)
        audio_file_paths.append(intro1_path)
        captions_durations.append((current_time, current_time + intro1_duration, "Welcome to the ICS31 BrainRot Quiz!"))
        current_time += intro1_duration

        intro2_path = create_tts_audio_file(intro2, temp_files)
        intro2_duration = get_audio_duration(intro2_path)
        audio_file_paths.append(intro2_path)
        captions_durations.append((current_time, current_time + intro2_duration, "Score a 4/5 to Graduate Rizz University!"))
        current_time += intro2_duration

        update_progress(30, "Generating question audio...")

        # Get timer duration once
        timer_duration = get_audio_duration(timer_path)

        # Generate audio for each question and answer
        for i, item in enumerate(script):
            update_progress(30 + (i * 8), f"Processing question {i + 1}...")

            # Question audio
            question_path = create_tts_audio_file(item["question"], temp_files)
            question_duration = get_audio_duration(question_path)
            audio_file_paths.append(question_path)

            # Timer audio path (will be loaded later)
            audio_file_paths.append(timer_path)

            # Caption for question + choices (shown during question + timer)
            question_caption = item["question"] + item["choices"]
            question_total_duration = question_duration + timer_duration
            captions_durations.append((current_time, current_time + question_total_duration, question_caption))
            current_time += question_total_duration

            # Correct answer audio
            correct_path = create_tts_audio_file(item["correct"], temp_files)
            correct_duration = get_audio_duration(correct_path)
            audio_file_paths.append(correct_path)
            captions_durations.append((current_time, current_time + correct_duration, item["correct"]))
            current_time += correct_duration

        # Force garbage collection to free memory
        gc.collect()

        update_progress(70, "Combining audio...")

        # Now load all audio clips and concatenate
        audio_clips = [AudioFileClip(path) for path in audio_file_paths]
        voice_audio = concatenate_audioclips(audio_clips)
        total_duration = voice_audio.duration

        # Add background music (Wii Shop) if available
        bg_music = None
        if bg_music_path:
            bg_music = AudioFileClip(bg_music_path)
            # Loop background music if needed
            if bg_music.duration < total_duration:
                loops_needed = int(total_duration / bg_music.duration) + 1
                bg_music_clips = [AudioFileClip(bg_music_path) for _ in range(loops_needed)]
                bg_music.close()
                bg_music = concatenate_audioclips(bg_music_clips)
            # Trim to match duration and lower volume (15% of original)
            bg_music = bg_music.subclip(0, total_duration)
            bg_music = bg_music.fl(lambda gf, t: gf(t) * 0.15, keep_duration=True)
            # Combine voice audio with background music
            final_audio = CompositeAudioClip([voice_audio, bg_music])
        else:
            final_audio = voice_audio

        gc.collect()

        update_progress(75, "Processing background video...")

        # Load and prepare background video
        bg_video = VideoFileClip(video_path)

        # Resize to fit vertical format while maintaining aspect ratio
        bg_video = bg_video.fx(resize, width=VIDEO_WIDTH)

        # If video is shorter than audio, loop it
        if bg_video.duration < total_duration:
            loops_needed = int(total_duration / bg_video.duration) + 1
            bg_video = concatenate_videoclips([bg_video] * loops_needed)

        # Trim to match audio duration
        bg_video = bg_video.subclip(0, total_duration)

        update_progress(80, "Adding captions...")

        # Create text overlays for each caption
        text_clips = []
        for start, end, caption in captions_durations:
            duration = end - start
            text_clip = create_caption_text_clip(caption, duration, position='center')
            text_clip = text_clip.set_start(start)
            text_clips.append(text_clip)

        update_progress(85, "Composing final video...")

        # Composite video with text overlays
        final_video = CompositeVideoClip([bg_video] + text_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
        final_video = final_video.set_audio(final_audio)

        # Generate output filename
        video_id = str(uuid4())
        output_path = os.path.join(VIDEOS_DIR, f"{video_id}.mp4")

        update_progress(90, "Exporting video...")

        # Optimized encoding settings for low-memory environments
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',  # Fastest encoding, lowest memory
            threads=2,  # Reduced threads for low-memory
            bitrate='1500k',  # Lower bitrate for smaller files
            audio_bitrate='128k',
            ffmpeg_params=['-crf', '28']  # Higher CRF = smaller file, slightly lower quality
        )

        # Close all clips to free resources
        final_video.close()
        bg_video.close()
        final_audio.close()
        if bg_music is not None:
            try:
                bg_music.close()
            except:
                pass
        voice_audio.close()
        for clip in audio_clips:
            try:
                clip.close()
            except:
                pass
        for clip in text_clips:
            clip.close()

        # Force final garbage collection
        gc.collect()

        update_progress(100, "Video generation complete!")

        return output_path

    except Exception as e:
        # Clean up on error
        gc.collect()
        raise Exception(f"Video generation failed: {str(e)}")

    finally:
        # Cleanup temp files
        cleanup_temp_files(temp_files)
        gc.collect()


if __name__ == "__main__":
    # Interactive mode for command-line usage
    user_input = input("Please enter an ICS 31 Topic!\n")
    video_path = generate(user_input)
    print(f"Video successfully generated: {video_path}")
