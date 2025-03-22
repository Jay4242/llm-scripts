#!/bin/bash

# Usage: how_its_made.bash <video_file> <output_directory>

VIDEO_FILE="$1"
OUTPUT_DIR="$2"

# Check if arguments are provided
if [ -z "$VIDEO_FILE" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 <video_file> <output_directory>"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Scene detection using ffmpeg
ffmpeg -i "$VIDEO_FILE" -filter:v "select='gt(scene,0.5)',showinfo" -vsync vfr -frame_pts true "$OUTPUT_DIR/scene_%03d.jpg" 2>/dev/null 1>/dev/null

# Find all scene files and sort them numerically
SCENE_FILES=("$OUTPUT_DIR/scene_"*.jpg)
SCENE_FILES=($(printf "%s\n" "${SCENE_FILES[@]}" | sort -n))

# Calculate the number of images per batch (2)
BATCH_SIZE=2

# Construct the prompt
PROMPT="In the style of 'How It's Made', describe these images from the video $(printf '%q' "$VIDEO_FILE") in a funny way. Keep the description concise."

# Initialize the complete description
COMPLETE_DESCRIPTION=""

# Loop through the scene files in batches of 2
for ((i=0; i<NUM_IMAGES; i+=BATCH_SIZE)); do
    # Build the command to execute llm-python-vision.py
    COMMAND=("/usr/bin/python3" "llm-python-vision.py")

    # Add the prompt
    COMMAND+=("--prompt" "$PROMPT")

    # Add each scene file in the current batch as an image
    for ((j=i; j<NUM_IMAGES && j<i+BATCH_SIZE; j++)); do
        SCENE_FILE="${SCENE_FILES[j]}"
        COMMAND+=("--image" "$SCENE_FILE")
    done

    # Execute the command and capture the description
    DESCRIPTION=$("${COMMAND[@]}")

    # Append the description to the complete description
    COMPLETE_DESCRIPTION+="$DESCRIPTION "
done

echo "Description: $COMPLETE_DESCRIPTION"

# Save the complete description to a file
echo "Description: $COMPLETE_DESCRIPTION" > "$OUTPUT_DIR/descriptions.txt"

echo "Scene descriptions saved to $OUTPUT_DIR/descriptions.txt"
