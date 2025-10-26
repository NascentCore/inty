#!/bin/bash

# Android Studio Launcher Script
# Launches Android Studio to open the current working directory

TARGET_DIR="${1:-$(pwd)}"
STUDIO_PATH="/Applications/Android Studio.app/Contents/MacOS/studio"

"$STUDIO_PATH" --trusted "$TARGET_DIR" &
