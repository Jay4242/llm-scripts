from flask import Flask, request, jsonify, Response, stream_with_context
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Constants
MODEL_NAME = "Qwen3-30B-A3B-Instruct-2507"
DEFAULT_FLASK_HOST = "localhost"
DEFAULT_HOST = "localhost"
DEFAULT_PORT = "9090"
DEFAULT_API_KEY = "none"

SYSTEM_PROMPT = "You are a Wikipedia HTML author.\\nYour task is to generate a single, complete HTML file for a wiki page.\\nThe page must include embedded CSS to resemble Wikipedia's layout, spacing, and fonts.\\nAll internal links must use the format `/wiki/<topic>`.\\nEvery page must include a search bar at the top.\\nThe search bar must be an HTML `<form>` with `action=\"/search\"` and `method=\"POST\"`.\\nThe form must contain an `<input type=\"text\" name=\"search_term\">` and a submit button.\\nReturn only the raw HTML content, with no preamble, explanation, or markdown code fences."

def get_llm_client():
    """
    Create and return an OpenAI client configured with environment variables.
    """
    host = os.getenv("LLM_BACKEND_HOST", DEFAULT_HOST)
    port = os.getenv("LLM_BACKEND_PORT", DEFAULT_PORT)
    api_key = os.getenv("LLM_BACKEND_API_KEY", DEFAULT_API_KEY)
    return OpenAI(base_url=f"http://{host}:{port}/v1", api_key=api_key)

def call_llm_api(system_prompt, user_prompt):
    """
    Call the LLM API directly using OpenAI client
    """
    try:
        client = get_llm_client()
        
        # Create completion using the same parameters as llm-python-chat.py
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
        )
        
        # Strip any surrounding Markdown code fences that the LLM might add
        content = completion.choices[0].message.content.strip()
        if content.startswith("```html"):
            content = content[len("```html"):].lstrip()
        if content.endswith("```"):
            content = content[:-3].rstrip()
        return content
    except Exception as e:
        return f"Error calling LLM: {str(e)}"

def stream_llm_response(system_prompt, user_prompt):
    """
    Stream LLM response as HTML.
    """
    try:
        client = get_llm_client()
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            stream=True,
        )
        def generate():
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        return Response(stream_with_context(generate()), mimetype='text/html')
    except Exception as e:
        # Return error as HTML for consistency with successful responses
        error_html = f"<html><body><h1>Error</h1><p>Failed to generate content: {str(e)}</p></body></html>"
        return Response(error_html, mimetype='text/html')

@app.route('/')
def hello():
    user_prompt = "Please generate the main page of the wiki."
    return stream_llm_response(SYSTEM_PROMPT, user_prompt)

@app.route('/search', methods=['POST'])
def search():
    try:
        # Handle form data instead of JSON
        query = request.form.get('search_term', '')
        if not query:
            return jsonify({'error': 'No search term provided'}), 400

        user_prompt = f"Generate a Wikipedia search results page for the query '{query}'."
        return stream_llm_response(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        # For API errors, return JSON
        return jsonify({'error': str(e)}), 500

# New endpoint: /wiki/<topic> generates a wiki style page for the given topic.
@app.route('/wiki/<topic>')
def wiki(topic):
    """
    Generate a wiki style page for the given topic.
    """
    user_prompt = f"Generate a Wikipedia page about '{topic}'."
    return stream_llm_response(SYSTEM_PROMPT, user_prompt)

if __name__ == '__main__':
    flask_host = os.getenv("FLASK_HOST", DEFAULT_FLASK_HOST)
    app.run(host=flask_host, port=5000, debug=True)
