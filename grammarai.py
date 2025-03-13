import sys
import os
from dotenv import load_dotenv
from openai import OpenAI
import httpx
import re

load_dotenv()

def llm_call(system_prompt, user_prompt, temperature=0.7):
    """
    Calls the LLM with the given system prompt and user prompt.

    Args:
        system_prompt (str): The system prompt for the LLM.
        user_prompt (str): The user prompt for the LLM.
        temperature (float, optional): The temperature for the LLM. Defaults to 0.7.
    """

    base_url = os.getenv("OPENAI_BASE_URL")
    client = OpenAI(base_url=base_url, api_key="none", timeout=httpx.Timeout(3600))

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": "The following is the sentence. It may seem strange or archaic, but it is the sentence as provided and should be judged as is. If it is too archaic to fix, leave it as it is. There are no further rules or instructions. The following is the sentence you are correcting:"})
    messages.append({"role": "user", "content": user_prompt})

    completion = client.chat.completions.create(
      model="gemma-2-2b-it-q8_0",
      messages=messages,
      temperature=temperature,
      stream=True,
    )

    response = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            response += chunk.choices[0].delta.content
            #print(chunk.choices[0].delta.content, end="", flush=True)
    #print('\n')
    return response

def split_into_sentences(text):
    """
    Splits a text into sentences using a regular expression.
    """
    sentence_endings = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s')
    sentences = sentence_endings.split(text)
    return sentences

def check_grammar(file_path):
    """
    Reads a file, splits it into sentences, and checks the grammar of each sentence using the LLM.

    Args:
        file_path (str): The path to the file to check.
    """
    try:
        with open(file_path, 'r') as file:
            text = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    sentences = split_into_sentences(text)

    system_prompt = "You are a grammar checking assistant. You will be provided with a sentence, and you should respond with the corrected sentence. If the sentence is already grammatically correct, respond with the original sentence."

    for sentence in sentences:
        if sentence.strip():  # Ignore empty sentences
            print(f"Original: {sentence.strip()}")
            corrected_sentence = llm_call(system_prompt, sentence.strip())
            print(f"Corrected: {corrected_sentence.strip()}")
            print("-" * 20)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python grammarai.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    check_grammar(file_path)
