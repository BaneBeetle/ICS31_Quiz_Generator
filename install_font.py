"""
Font Installation Script for ICS31 Quiz Generator

This script installs the OpenSans-ExtraBold font for use with MoviePy/ImageMagick.
Run this script once before using the quiz generator on a new machine.
"""

import os
import shutil
import platform
import subprocess

def install_font_windows():
    """Install font on Windows"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_source = os.path.join(base_dir, "OpenSans-ExtraBold.ttf")

    if not os.path.exists(font_source):
        print(f"Error: Font file not found at {font_source}")
        return False

    # Get user fonts directory
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    fonts_dir = os.path.join(local_app_data, 'Microsoft', 'Windows', 'Fonts')

    # Create fonts directory if it doesn't exist
    os.makedirs(fonts_dir, exist_ok=True)

    # Copy font file
    font_dest = os.path.join(fonts_dir, "OpenSans-ExtraBold.ttf")
    try:
        shutil.copy2(font_source, font_dest)
        print(f"Font copied to: {font_dest}")
    except Exception as e:
        print(f"Error copying font: {e}")
        return False

    # Register font in registry
    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "OpenSans ExtraBold (TrueType)", 0, winreg.REG_SZ, font_dest)
        print("Font registered in Windows registry")
    except Exception as e:
        print(f"Error registering font: {e}")
        return False

    print("\nFont installation complete!")
    print("Note: You may need to restart your terminal/IDE for the font to be recognized.")
    return True


def install_font_linux():
    """Install font on Linux"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_source = os.path.join(base_dir, "OpenSans-ExtraBold.ttf")

    if not os.path.exists(font_source):
        print(f"Error: Font file not found at {font_source}")
        return False

    # User fonts directory
    fonts_dir = os.path.expanduser("~/.local/share/fonts")
    os.makedirs(fonts_dir, exist_ok=True)

    # Copy font file
    font_dest = os.path.join(fonts_dir, "OpenSans-ExtraBold.ttf")
    try:
        shutil.copy2(font_source, font_dest)
        print(f"Font copied to: {font_dest}")
    except Exception as e:
        print(f"Error copying font: {e}")
        return False

    # Update font cache
    try:
        subprocess.run(["fc-cache", "-f", "-v"], check=True, capture_output=True)
        print("Font cache updated")
    except Exception as e:
        print(f"Warning: Could not update font cache: {e}")

    print("\nFont installation complete!")
    return True


def install_font_mac():
    """Install font on macOS"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_source = os.path.join(base_dir, "OpenSans-ExtraBold.ttf")

    if not os.path.exists(font_source):
        print(f"Error: Font file not found at {font_source}")
        return False

    # User fonts directory
    fonts_dir = os.path.expanduser("~/Library/Fonts")
    os.makedirs(fonts_dir, exist_ok=True)

    # Copy font file
    font_dest = os.path.join(fonts_dir, "OpenSans-ExtraBold.ttf")
    try:
        shutil.copy2(font_source, font_dest)
        print(f"Font copied to: {font_dest}")
    except Exception as e:
        print(f"Error copying font: {e}")
        return False

    print("\nFont installation complete!")
    return True


def main():
    print("ICS31 Quiz Generator - Font Installer")
    print("=" * 40)

    system = platform.system()
    print(f"Detected OS: {system}\n")

    if system == "Windows":
        success = install_font_windows()
    elif system == "Linux":
        success = install_font_linux()
    elif system == "Darwin":
        success = install_font_mac()
    else:
        print(f"Unsupported operating system: {system}")
        success = False

    if success:
        print("\nYou can now run the quiz generator!")
    else:
        print("\nFont installation failed. The generator will use a fallback font.")


if __name__ == "__main__":
    main()
