#!/usr/bin/env python3

import sys
import json
import os
from openai import OpenAI
import httpx

def extract_facts_from_document(document_path):
    """
    Extract facts from a document using an LLM backend.
    
    Args:
        document_path (str): Path to the text document
        temperature (float): Sampling temperature for the LLM
        
    Returns:
        list: List of facts extracted from the document
    """
    
    # Hardcoded system prompt for fact extraction expert
    system_prompt = "You are a concise fact extraction assistant. Given a document, extract every distinct factual statement or description, output each as a single short sentence on its own line. Do not include introductions, explanations, or duplicate information. For any code snippets, describe their purpose in one sentence instead of reproducing the code."
    
    # Hardcoded preprompt
    preprompt = f"Document name: '{os.path.basename(document_path)}'. Analyze its content."
    
    # Hardcoded postprompt to restate the task of extracting facts one line at a time
    postprompt = "List all extracted facts, one per line, using concise sentences. Ensure each fact is self‑contained and omit any extra commentary."
    
    # Read the content of the document file
    try:
        with open(document_path, 'r') as file:
            document = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{document_path}' does not exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    # Point to the local server
    client = OpenAI(
        base_url="http://localhost:9090/v1", 
        api_key="none", 
        timeout=httpx.Timeout(7200)
    )

    # Create the conversation
    completion = client.chat.completions.create(
        model="gemma-2-2b-it-q8_0",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": preprompt},
            {"role": "user", "content": document},
            {"role": "user", "content": postprompt}
        ],
        temperature=1.0,
        stream=False,  # We want the full response, not streaming
    )

    # Extract the response content
    response_content = completion.choices[0].message.content.strip()
    
    # Try to parse as JSON if it's formatted as such
    try:
        facts = json.loads(response_content)
        if isinstance(facts, list):
            return facts
    except json.JSONDecodeError:
        # If not JSON, treat as plain text and split into lines
        return [line.strip() for line in response_content.split('\n') if line.strip()]

    # Fallback: return the raw content as a single fact
    return [response_content]

def create_embeddings_for_facts(facts, document_path):
    """
    Create embeddings for each fact and save to a file.
    
    Args:
        facts (list): List of facts to embed
        document_path (str): Path to the original document
    """
    # Create embedding model name
    embedding_model = "nomic-embed-text-v1.5.q8_0"
    
    # Create output file name based on input document
    base_name = os.path.splitext(document_path)[0]
    embeddings_file = f"{base_name}.embeddings"
    
    # Initialize the OpenAI client for embeddings
    client = OpenAI(
        base_url="http://localhost:9494/v1", 
        api_key="None",
        timeout=httpx.Timeout(7200)
    )
    
    # Process each fact and create embeddings
    with open(embeddings_file, 'w') as f:
        for fact in facts:
            if fact.strip():  # Skip empty facts
                try:
                    # Clean up the fact for embedding
                    cleaned_fact = fact.strip().lower().replace('"', '').replace('*', '').replace('\'', '')
                    
                    # Create embedding
                    completion = client.embeddings.create(
                        model=embedding_model,
                        input=[cleaned_fact],
                    )
                    
                    # Write to file in the format: "document_path","fact","embedding"
                    embedding = completion.data[0].embedding
                    f.write(f'"{document_path}","{fact}","{embedding}"\n')
                    
                except Exception as e:
                    print(f"Error processing fact '{fact}': {e}")
                    # Continue processing other facts even if one fails
                    continue
    
    print(f"Embeddings saved to {embeddings_file}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python llm-chunk.py <document_path>")
        sys.exit(1)

    document_path = sys.argv[1]

    # Extract facts from the document
    facts = extract_facts_from_document(
        document_path
    )

    # Print the facts (these would be used for embedding creation)
    for fact in facts:
        print(fact)
    
    # Create embeddings for the facts
    create_embeddings_for_facts(facts, document_path)

if __name__ == "__main__":
    main()
