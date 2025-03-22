#!/bin/bash

image=$1

meme_json=$(llm-python-vision.py "Come up with meme text for this image.  It should be in JSON form with a 'top_text' and 'bottom_text'.  Only give one answer with no explanation or preamble." "${image}" | sed '/```.*/d' )

top_text=$(echo "$meme_json" | jq .top_text | sed -e 's/"//g')
bottom_text=$(echo "$meme_json" | jq .bottom_text | sed -e 's/"//g')

# Get image dimensions
width=$(identify -format "%w" "$image")
height=$(identify -format "%h" "$image")

# Set dynamic font size (e.g., 5% of the image height)
font_size=$((height / 12))


convert ${image} \
  -gravity north \
  -stroke black -strokewidth 2 -size "${width}x" -pointsize "${font_size}" -annotate +0+10 "${top_text^^}" \
  -stroke none -fill white -annotate +0+10 "${top_text^^}" \
  -gravity south \
  -stroke black -strokewidth 2 -size "${width}x" -pointsize "${font_size}" -annotate +0+10 "${bottom_text^^}" \
  -stroke none -fill white -annotate +0+10 "${bottom_text^^}" \
  output.jpg
