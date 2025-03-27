#!/bin/python3

import sys
from openai import OpenAI

# Retrieve the document file path from command line arguments
document_file_path = sys.argv[1]

# Initialize the OpenAI client
client = OpenAI(base_url="http://localhost:9090/v1", api_key="None")

# Read the document file line by line
try:
    with open(document_file_path, 'r') as file:
        for line in file:
            # Process each line
            line = line.strip().lower().replace('"', '').replace('*', '').replace('\'', '')  # Clean up the line
            if line:  # Skip empty lines
                try:
                    completion = client.embeddings.create(
                        model="nomic-embed-text-v1.5.q8_0",
                        input=[line],
                    )
                    # Output the result
                    print(f"\"{document_file_path}\",\"{line}\",\"{completion.data[0].embedding}\"")
                except Exception as e:
                    print(f"Error processing line '{line}': {e}")
except FileNotFoundError:
    print(f"Error: The file '{document_file_path}' does not exist.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
