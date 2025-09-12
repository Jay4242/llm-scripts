#!/bin/python3

import sys
# Example: reuse your existing OpenAI setup
from openai import OpenAI
import httpx

document_file_path = sys.argv[1]
system = sys.argv[2]
preprompt = sys.argv[3]
postprompt = sys.argv[4]
temp = float(sys.argv[5])
# Read the content of the document file
try:
    with open(document_file_path, 'r') as file:
        document = file.read()
except FileNotFoundError:
    print(f"Error: The file '{document_file_path}' does not exist.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)


# Point to the local server
client = OpenAI(base_url="http://localhost:9090/v1", api_key="lm-studio", timeout=httpx.Timeout(7200))

completion = client.chat.completions.create(
  model="gemma-2-2b-it-q8_0",
  messages=[
    {"role": "system", "content": system },
    {"role": "user", "content": preprompt },
    {"role": "user", "content": document },
    {"role": "user", "content": postprompt }
  ],
  temperature=temp,
  stream=True,
)

#print(completion.choices[0].message.content.strip())

for chunk in completion:
  if chunk.choices and chunk.choices[0].delta.content:
    print(chunk.choices[0].delta.content, end="", flush=True)
print('\n')

