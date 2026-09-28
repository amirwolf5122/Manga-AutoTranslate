#!/usr/bin/env bash
# ============================================
#   Manga Translator - Linux/macOS launcher
# ============================================
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[X] python3 not found. Install: sudo apt install python3 python3-pip python3-tk"
    exit 1
fi

has_display() {
    if [ "$(uname)" = "Darwin" ]; then
        return 0
    fi
    if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ] || [ "$XDG_SESSION_TYPE" = "x11" ] || [ "$XDG_SESSION_TYPE" = "wayland" ]; then
        return 0
    fi
    return 1
}

check_libgl() {
    
    if [ "$(uname)" = "Darwin" ]; then
        return 0
    fi
    if python3 -c "import ctypes.util,sys; sys.exit(0 if ctypes.util.find_library('GL') else 1)" 2>/dev/null; then
        if ldconfig -p 2>/dev/null | grep -q "libGL.so.1"; then
            return 0
        fi
        return 0
    fi
    if ldconfig -p 2>/dev/null | grep -q "libGL.so.1"; then
        return 0
    fi
    echo "[i] libGL.so.1 not found - installing (needed by OpenCV)..."
    if command -v apt-get >/dev/null 2>&1; then
        (sudo apt-get update -qq && sudo apt-get install -y -qq libgl1 libglib2.0-0) \
            || apt-get install -y libgl1 libglib2.0-0 \
            || echo "[!] could not install libgl1 automatically. Run: sudo apt install libgl1"
    elif command -v dnf >/dev/null 2>&1; then
        (sudo dnf install -y mesa-libGL || echo "[!] Run: sudo dnf install mesa-libGL")
    elif command -v pacman >/dev/null 2>&1; then
        (sudo pacman -S --noconfirm mesa || echo "[!] Run: sudo pacman -S mesa")
    elif command -v apk >/dev/null 2>&1; then
        (apk add --no-cache mesa-gl || echo "[!] Run: apk add mesa-gl")
    else
        echo "[!] unknown package manager - install libgl1 (or mesa) manually."
    fi
}

deps() {
    echo "[i] Checking dependencies (first run may take a while)..."
    check_libgl
    python3 -c "import gradio" 2>/dev/null || python3 -m pip install -q gradio
    
    python3 -c "import cv2" 2>/dev/null || python3 -m pip install -q opencv-python-headless pillow numpy
    python3 -c "import cv2" 2>/dev/null || {
        echo "[X] cv2 import failed (missing system lib?). Run: sudo apt install libgl1 libglib2.0-0"
        return 1
    }
    return 0
}

while true; do
    clear
    echo ""
    echo "  ============================================"
    echo "     Manga Translator"
    echo "  ============================================"
    echo ""
    if has_display; then
        echo "    [1] App    - desktop window"
        echo "    [2] Web    - browser interface"
        echo "    [3] CLI    - asks for input in terminal"
        echo "    [4] Exit"
        echo ""
        read -rp "  Choose [1/2/3/4]: " choice
        case "$choice" in
            1)
                if ! python3 -c "import tkinter" 2>/dev/null; then
                    echo "[X] tkinter not available - install python3-tk. Use option 2 (Web)."
                    read -rp "Enter to continue..."
                    continue
                fi
                deps && python3 manga_app.py --desktop
                read -rp "Enter to continue..."
                ;;
            2)
                deps || { read -rp "Enter to continue..."; continue; }
                python3 -u manga_app.py --web
                read -rp "Enter to continue..."
                ;;
            3)
                deps || { read -rp "Enter to continue..."; continue; }
                python3 manga_app.py --cli
                read -rp "Enter to continue..."
                ;;
            4) exit 0 ;;
        esac
    else
        echo "    [1] Web    - browser interface (no display detected - App hidden)"
        echo "    [2] CLI    - asks for input in terminal"
        echo "    [3] Exit"
        echo ""
        read -rp "  Choose [1/2/3]: " choice
        case "$choice" in
            1)
                deps || { read -rp "Enter to continue..."; continue; }
                python3 -u manga_app.py --web
                read -rp "Enter to continue..."
                ;;
            2)
                deps || { read -rp "Enter to continue..."; continue; }
                python3 manga_app.py --cli
                read -rp "Enter to continue..."
                ;;
            3) exit 0 ;;
        esac
    fi
done
