#!/usr/bin/env python3

import sys
from openai import OpenAI
import httpx
import os
import shutil

SYSTEM_PROMPT = "You are a helpful assistant."
UNSORTED_DIR = "unsorted"
SORTED_DIR = "sorted"
TEMPERATURE = 0.7

def process_document(document_file_path, category_directories):
    """
    Processes a document by sending its content to an LLM server and printing the response.

    Args:
        document_file_path (str): The path to the document file.
        category_directories (list): A list of directories in the 'sorted' directory.
    """
    # Read the content of the document file
    try:
        with open(document_file_path, 'r') as file:
            document = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{document_file_path}' does not exist.")
        return None  # Indicate failure
    except Exception as e:
        print(f"Error: {e}")
        return None  # Indicate failure

    filename = os.path.basename(document_file_path)
    preprompt = f"The following is the contents of {filename}:\n\n"

    # Construct the postprompt with category directories
    categories_str = ", ".join(category_directories)
    postprompt = f"Based on the content of this document, which subdirectory in '{SORTED_DIR}' should it be placed in?  The options are: {categories_str}.  Just respond with the name of the directory."

    # Point to the local server
    client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))

    try:
        completion = client.chat.completions.create(
            model="gemma-3-4b-it-q8_0",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": preprompt},
                {"role": "user", "content": document},
                {"role": "user", "content": postprompt}
            ],
            temperature=TEMPERATURE,
            stream=True,
        )

        response_text = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                response_text += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end="", flush=True)
        print('\n')

        return response_text.strip()  # Return the LLM's chosen category

    except Exception as e:
        print(f"Error during LLM completion: {e}")
        return None  # Indicate failure


def main():
    if len(sys.argv) != 1:
        print("Usage: llm-document-sort.py")
        sys.exit(1)

    # Ensure 'unsorted' and 'sorted' directories exist
    if not os.path.isdir(UNSORTED_DIR):
        print(f"Error: '{UNSORTED_DIR}' directory not found.")
        sys.exit(1)
    if not os.path.isdir(SORTED_DIR):
        print(f"Error: '{SORTED_DIR}' directory not found.")
        sys.exit(1)

    # Get list of files in 'unsorted'
    try:
        unsorted_files = [f for f in os.listdir(UNSORTED_DIR) if os.path.isfile(os.path.join(UNSORTED_DIR, f))]
    except OSError as e:
        print(f"Error reading '{UNSORTED_DIR}' directory: {e}")
        sys.exit(1)

    # Get list of directories in 'sorted'
    try:
        sorted_directories = [d for d in os.listdir(SORTED_DIR) if os.path.isdir(os.path.join(SORTED_DIR, d))]
    except OSError as e:
        print(f"Error reading '{SORTED_DIR}' directory: {e}")
        sys.exit(1)

    # Process each file
    for filename in unsorted_files:
        file_path = os.path.join(UNSORTED_DIR, filename)
        chosen_category = process_document(file_path, sorted_directories)

        if chosen_category:
            destination_dir = os.path.join(SORTED_DIR, chosen_category)
            if not os.path.isdir(destination_dir):
                print(f"Error: Category directory '{chosen_category}' does not exist in '{SORTED_DIR}'.")
            else:
                destination_path = os.path.join(destination_dir, filename)
                try:
                    shutil.copy(file_path, destination_path)
                    print(f"Copied '{filename}' to '{destination_dir}'.")
                except Exception as e:
                    print(f"Error copying '{filename}' to '{destination_dir}': {e}")
        else:
            print(f"Failed to process '{filename}'.")


if __name__ == '__main__':
    main()
