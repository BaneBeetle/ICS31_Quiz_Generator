from gpt_api import generate_script
import os
from uuid import uuid4
from tiktokvoice import *
from moviepy import AudioFileClip
from vid import *
import glob

def generate():
    # Ask what ICS 31 topic the user wants. Examples: "Loops", "Data Structures", etc
    user_input = input("Please enter a ICS 31 Topic!\n")

    # Generate based on user_input
    script = generate_script(user_input) # Script will be a list with 5 dictionaries.

    #script = generate_script("Loops") # Testing with topic Loops
    temp_dir = "../temp"

    intro = "Welcome to the ICS 31 Brain Rot Quiz!"
    intro2 = "Score a 4 out of 5 to graduate Rizz University"

    All_TTS = []
    captions = [] # combination with question and answers
    audio_paths = []
    captions_durations = []
    current_time = 0

    # CAN CONDENSE
    intro_tts = os.path.join(temp_dir, f"{uuid4()}.mp3")
    tts(intro, "en_us_001", filename=intro_tts)
    i1 = AudioFileClip(intro_tts)
    audio_paths.append(i1)
    captions_durations.append((current_time, (current_time + i1.duration), "Welcome to the ICS31 BrainRot Quiz!"))
    current_time += i1.duration

    intro2_tts = os.path.join(temp_dir, f"{uuid4()}.mp3")
    tts(intro2, "en_us_001", filename=intro2_tts)
    i2 = AudioFileClip(intro2_tts)
    audio_paths.append(i2)
    captions_durations.append((current_time, (current_time + i2.duration), "Score a 4/5 to Graduate Rizz University!"))
    current_time += i2.duration

    for dict in script:
        captions.append(dict["question"] + dict["choices"]) 

        All_TTS.append(dict["question"])
        
        current_tts = os.path.join(temp_dir, f"{uuid4()}.mp3")
        tts(dict["question"], "en_us_001", filename=current_tts)
        question = AudioFileClip(current_tts)
        audio_paths.append(question)

        timer_files = glob.glob("**/clock.mp3", recursive=True) # Find the clock.mp3 file
        if timer_files:
            timer = timer_files[0]
        else:
            raise FileNotFoundError("clock.mp3 not found")
        
        timer = AudioFileClip(timer)
        audio_paths.append(timer)
    
        captions_durations.append((current_time, (current_time + question.duration + timer.duration), dict["question"] + dict["choices"]))
        current_time += (question.duration + timer.duration)

        All_TTS.append(dict["correct"])
        current_tts1 = os.path.join(temp_dir, f"{uuid4()}.mp3")
        tts(dict["correct"], "en_us_001", filename=current_tts1)

        correct = AudioFileClip(current_tts1)
        audio_paths.append(correct)
        captions_durations.append((current_time, current_time + correct.duration, dict["correct"]))
        current_time += correct.duration

    video_files = glob.glob("**/minecraft1.mp4", recursive=True)
    if video_files:
        video_path = video_files[0]
    else:
        raise FileNotFoundError("minecraft1.mp4 not found")

    combined_video_path = generate_video(user_input, video_path, audio_paths, captions_durations, 8, bg=True)

    print(f"Video successfully generated {combined_video_path}!")

if __name__ == "__main__":
    generate()
