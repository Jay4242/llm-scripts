from flask import Flask, request, jsonify, Response, stream_with_context
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

def call_llm_api(system_prompt, user_prompt):
    """
    Call the LLM API directly using OpenAI client
    """
    try:
        # Point to the local server
        host = os.getenv("LLM_BACKEND_HOST", "localhost")
        port = os.getenv("LLM_BACKEND_PORT", "9090")
        client = OpenAI(base_url=f"http://{host}:{port}/v1", api_key=os.getenv("LLM_BACKEND_API_KEY", "none"))
        
        # Create completion using the same parameters as llm-python-chat.py
        completion = client.chat.completions.create(
            model="gemma-2-2b-it-q8_0",
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
        host = os.getenv("LLM_BACKEND_HOST", "localhost")
        port = os.getenv("LLM_BACKEND_PORT", "9090")
        client = OpenAI(base_url=f"http://{host}:{port}/v1", api_key=os.getenv("LLM_BACKEND_API_KEY", "none"))
        completion = client.chat.completions.create(
            model="gemma-2-2b-it-q8_0",
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
        return f"Error calling LLM: {str(e)}"

@app.route('/')
def hello():
    system_prompt = "You are a Wikipedia HTML author. Create the main/front page of a wiki. Return only HTML with no preamble or explanation. Include a search box at the top of every page for users to search topics. All internal links must use the format /wiki/<topic>. The page should be structured like a Wikipedia main page with featured content and navigation."
    user_prompt = "Please generate the main page of the wiki. Include a search box at the top for users to search topics. All internal links must use the format /wiki/<topic>."
    return stream_llm_response(system_prompt, user_prompt)

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('search_term', '')
        if not query:
            return jsonify({'error': 'No search term provided'}), 400

        host = os.getenv("LLM_BACKEND_HOST", "localhost")
        port = os.getenv("LLM_BACKEND_PORT", "9090")
        client = OpenAI(base_url=f"http://{host}:{port}/v1", api_key=os.getenv("LLM_BACKEND_API_KEY", "none"))

        system_prompt = "You are a Wikipedia HTML author. Generate a search results page for the query. Return only HTML with no preamble or explanation. Include a search box at the top of every page for new searches. All internal links must use the format /wiki/<topic>. Display results in a clean, Wikipedia-style layout with titles and summaries."
        user_prompt = f"Generate a Wikipedia search results page for the query '{query}'."

        return stream_llm_response(system_prompt, user_prompt)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# New endpoint: /wiki/<topic> generates a wiki style page for the given topic.
@app.route('/wiki/<topic>')
def wiki(topic):
    """
    Generate a wiki style page for the given topic.
    """
    host = os.getenv("LLM_BACKEND_HOST", "localhost")
    port = os.getenv("LLM_BACKEND_PORT", "9090")
    client = OpenAI(base_url=f"http://{host}:{port}/v1", api_key=os.getenv("LLM_BACKEND_API_KEY", "none"))

    system_prompt = "You are a Wikipedia HTML author. Generate a complete wiki page for the topic. Return only HTML with no preamble or explanation. Include a search box at the top of every page for new searches. All internal links must use the format /wiki/<topic>. Structure the content like a Wikipedia article with proper headings and formatting."
    user_prompt = f"Generate a Wikipedia page about '{topic}'."

    return stream_llm_response(system_prompt, user_prompt)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
