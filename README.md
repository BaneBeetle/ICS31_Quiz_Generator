# 🎓 ICS31 Quiz Generator — AI-Powered Educational Video Creator

Welcome to the **ICS31 Quiz Generator**, a tool designed to automatically generate engaging, quiz-style educational videos powered by AI. Created during my time as a Teaching Assistant at UC Irvine, this project showcases how artificial intelligence can be used to enhance student learning through interactive and entertaining content.

## 🚀 Overview

As a TA for **ICS 31: Introduction to Programming**, I wanted to make review sessions more exciting and accessible. So I built this tool to generate TikTok-style quiz videos that explain concepts, test knowledge, and keep students engaged — all with a bit of humor and creativity.

Using **OpenAI's GPT models**, **text-to-speech synthesis**, and **automated video creation**, the Quiz Generator outputs short, personalized review videos that feel more like content students actually enjoy.

---

## 📚 Features

- ✅ **AI-Generated Questions** — Uses GPT to generate programming-related quiz questions on demand.
- 🎙️ **Voice Synthesis** — Converts text to voice (in TikTok-style tones) to make the videos more fun and conversational.
- 🎬 **Automated Video Creation** — Combines audio, captions, and visuals into a polished video format.
- 🧠 **Customizable Topics** — Easily adaptable for different subjects or course content.

---

## 🛠️ How It Works

1. **`gpt_api.py`**  
   Generates quiz questions using OpenAI's API.

2. **`tiktokvoice.py`**  
   Converts quiz text into realistic speech using voice synthesis APIs.

3. **`vid.py`**  
   Creates videos using pre-defined templates, audio overlays, and captions.

4. **`main.py`**  
   Orchestrates the full pipeline from question generation to video output.

---

## 🎯 Motivation

> "Education doesn't have to be dry. If our students are scrolling TikTok, why not bring learning to that format?"

This project started as a creative side project during my TAship, blending my interests in **AI**, **multimedia**, and **teaching**. It’s proof that educational tools can be both **technically impressive** and **fun**.

---

## 📂 Project Structure

├── main.py # Orchestrates full pipeline
├── gpt_api.py # Handles AI question generation
├── tiktokvoice.py # Text-to-speech generation
├── vid.py # Video composition
├── audio/ # Temporary audio files
├── generated_videos/ # Final video output
├── assets/ (optional) # Visual or background assets

---

## ⚡ Getting Started

1. Clone the repo:
   ```bash
   git clone https://github.com/BaneBeetle/ICS31_Quiz_Generator
   cd ICS31_Quiz_Generator

2. Install dependencies:
   pip install -r requirements.txt

3. Set up your API keys (for OpenAI, TTS provider, etc.) in a .env file.
4. Run: python main.py

🤖 Tech Stack
Python

OpenAI API (GPT-3.5/4)

Text-to-Speech API (e.g. TikTok, ElevenLabs)

FFmpeg / moviepy for video creation

📽️ Demo
Want to see it in action? Check out a sample output here:
👉 Sample Quiz Video https://www.youtube.com/shorts/uhuTbJ2Sr0c

❤️ Acknowledgements
Thanks to my ICS31 students for inspiring this.
Special shoutout to the UCI CS department and my fellow TAs.
And props to the open-source community for all the tools used!

📌 Future Improvements
GUI for non-technical users
Support for multiple languages and voice tones
Drag-and-drop question input
Real-time video previews

📫 Contact
Made by Brian Phan —
Connect with me: phan.brian.minh@gmail.com
Or visit: www.banebeetle.com
