"""
Tests that run the real MoviePy code the video pipeline (main.py) relies on.

They encode a tiny synthetic clip with the FFmpeg binary bundled with
imageio-ffmpeg, so they need no media files, API key, ImageMagick or network.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from moviepy.audio.AudioClip import AudioClip
from moviepy.video.VideoClip import ColorClip

ROOT = Path(__file__).resolve().parent.parent


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# conftest.py replaces the `main` module with a mock (and stubs tiktokvoice
# and moviepy_config), so load the real file under another name.
pipeline = load_module("quiz_pipeline", "main.py")


def tone(t):
    """Quiet stereo 440 Hz tone. MoviePy passes t as a scalar or an array."""
    wave = 0.1 * np.sin(2 * np.pi * 440 * np.asarray(t))
    return np.array([wave, wave]).T


@pytest.fixture
def short_clip():
    audio = AudioClip(tone, duration=0.5, fps=44100)
    return ColorClip(size=(64, 64), color=(0, 128, 255), duration=0.5).set_audio(audio)


def test_write_video_keeps_temp_soundtrack_out_of_working_dir(tmp_path, monkeypatch, short_clip):
    """Regression: MoviePy wrote its temporary soundtrack to the current
    working directory, which is read-only under the systemd unit."""
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    monkeypatch.setattr(pipeline, "TEMP_DIR", str(temp_dir))
    monkeypatch.chdir(workdir)

    soundtracks = []
    write_audiofile = short_clip.audio.write_audiofile

    def recording_write_audiofile(filename, *args, **kwargs):
        soundtracks.append(Path(filename).resolve())
        return write_audiofile(filename, *args, **kwargs)

    short_clip.audio.write_audiofile = recording_write_audiofile
    output = tmp_path / "quiz.mp4"

    pipeline.write_video(short_clip, str(output))

    assert output.stat().st_size > 0
    assert [path.parent for path in soundtracks] == [temp_dir.resolve()]
    assert list(workdir.iterdir()) == []
    assert list(temp_dir.iterdir()) == []  # MoviePy deletes it when done
