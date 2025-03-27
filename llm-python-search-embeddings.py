#!/bin/python3

# Example code for saving embeddings to CSV
import sys
import csv
import openai
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

csv_filename = sys.argv[1]
search_phrase = sys.argv[2]
top_n = sys.argv[3]
top_n = int(top_n)

search_phrase = search_phrase.lower()
client = openai.OpenAI(base_url="http://localhost:9090/v1", api_key="None")


def load_embeddings_from_csv(csv_filename):
    df = pd.read_csv(csv_filename, header=None)
    texts = df[0].tolist()
    embeddings = np.array(df[1].apply(eval).tolist())
    return texts, embeddings

def find_relevant_texts(new_text, texts, embeddings, client, top_n):
    # Generate embedding for new text
    response = client.embeddings.create(
        model="nomic-embed-text-v1.5.q8_0",
        input=[new_text]
    )
    new_embedding = np.array(response.data[0].embedding).reshape(1, -1)
    
    # Compute cosine similarities
    similarities = cosine_similarity(new_embedding, embeddings).flatten()
    
    # Find the most similar text
    top_indices = similarities.argsort()[-top_n:][::-1]
    
    # Collect the top N results
    top_results = [(texts[idx], similarities[idx]) for idx in top_indices]
    
    return top_results

texts, embeddings = load_embeddings_from_csv(csv_filename)

top_results = find_relevant_texts(search_phrase, texts, embeddings, client, top_n)
for i, (text, similarity) in enumerate(top_results):
    print(f"{i + 1}:\"{text}\":{similarity:.2f}")
