#!/bin/bash

# Select the window and get its ID
echo "Please select the window you want to capture..."
window_id=$(xdotool selectwindow)

if [ -z "$window_id" ]; then
  echo "No window selected. Exiting."
  exit 1
fi

echo "Selected window ID: $window_id"

while true; do
  # Take a screenshot of the selected window
  scrot -o -q 100 -w "$window_id" /dev/shm/llm-screenshot.png

  echo "Screenshot saved."

  # Describe the image using llm-python-vision.py
  description=$(/usr/local/bin/llm-python-vision-ollama.py /dev/shm/llm-screenshot.png "Describe what is in this image.")

  # Print the description
  echo "Image Description:"
  echo "$description"

  # Wait for 60 seconds
  sleep 60
done
