#!/bin/python3

# Adapted from OpenAI's Vision example 
from openai import OpenAI
import base64
import requests
import sys

# Retrieve the file path from the parsed arguments
prompt = sys.argv[1]
path = sys.argv[2]
model = "llama3.2-vision:latest"

# Point to the local server
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

# Read the image and encode it to base64:
base64_image = ""
try:
  image = open(path.replace("'", ""), "rb").read()
  base64_image = base64.b64encode(image).decode("utf-8")
except:
  print("Couldn't read the image. Make sure the path is correct and the file exists.")
  exit()

completion = client.chat.completions.create(
  model=model,
  messages=[
    {
      "role": "system",
      "content": "You are a helpful assistant.",
    },
    {
      "role": "user",
      "content": [
        {"type": "text", "text": prompt },
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}"
          },
        },
      ],
    }
  ],
  max_tokens=-1,
  stream=False
)

#for chunk in completion:
#  if chunk.choices[0].delta.content:
#    print(chunk.choices[0].delta.content, end="", flush=True)
#print('\n')

print(completion.choices[0].message.content.strip())

#print(completion)
