# MoviePy ImageMagick Configuration
# This file configures MoviePy to find ImageMagick on Windows

import os

# Common ImageMagick installation paths on Windows
IMAGEMAGICK_PATHS = [
    r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe",
    r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
    r"C:\Program Files\ImageMagick-7.1.0-Q16-HDRI\magick.exe",
    r"C:\Program Files\ImageMagick-7.0.11-Q16-HDRI\magick.exe",
    r"C:\Program Files (x86)\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
]

def find_imagemagick():
    """Find ImageMagick binary path"""
    # First check if it's in PATH
    from shutil import which
    magick_path = which("magick")
    if magick_path:
        return magick_path

    # Check common installation paths
    for path in IMAGEMAGICK_PATHS:
        if os.path.exists(path):
            return path

    # Check Program Files for any ImageMagick version
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    if os.path.exists(program_files):
        for folder in os.listdir(program_files):
            if folder.startswith("ImageMagick"):
                magick_path = os.path.join(program_files, folder, "magick.exe")
                if os.path.exists(magick_path):
                    return magick_path

    return None

def configure_moviepy():
    """Configure MoviePy to use ImageMagick"""
    magick_path = find_imagemagick()

    if magick_path:
        # Set environment variable for MoviePy
        os.environ["IMAGEMAGICK_BINARY"] = magick_path
        print(f"ImageMagick found at: {magick_path}")
        return True
    else:
        print("WARNING: ImageMagick not found. Text rendering may fail.")
        print("Please install ImageMagick from: https://imagemagick.org/script/download.php#windows")
        return False

# Auto-configure when imported
configure_moviepy()
