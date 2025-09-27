from flask import Flask, request, jsonify
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
        
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error calling LLM: {str(e)}"

@app.route('/')
def hello():
    system_prompt = "You are a Wikipedia HTML author. You are making the main/front page of the wiki. Expect HTML output only, no preamble or explanation. You can use the /search endpoint by sending a POST request to /search with JSON body containing 'search_term'. The endpoint will return a Wikipedia search results page."
    user_prompt = "Please generate the main page of the wiki.\n\nAdditionally, you can use the /search endpoint by sending a POST request to /search with JSON body containing 'search_term'. The endpoint will return a Wikipedia search results page."
    html = call_llm_api(system_prompt, user_prompt)
    return html

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('search_term', '')
        
        if not query:
            return jsonify({'error': 'No search term provided'}), 400
        
        # Call the LLM API to generate a search results page
        system_prompt = "You are a Wikipedia HTML author. Generate a search results page for the query. Expect HTML output only, no preamble or explanation. Include a search text box that allows the user to search for a different topic. You can use the /search endpoint by sending a POST request to /search with JSON body containing 'search_term'. The endpoint will return a Wikipedia search results page."
        user_prompt = f"Generate a Wikipedia search results page for the query '{query}'."
        html = call_llm_api(system_prompt, user_prompt)
        
        return html
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# New endpoint: /wiki/<topic> generates a wiki style page for the given topic.
@app.route('/wiki/<topic>')
def wiki(topic):
    """
    Generate a wiki style page for the given topic.
    """
    system_prompt = "You are a Wikipedia HTML author. Generate a wiki style page for the topic. Expect HTML output only, no preamble or explanation. Include a search text box that allows the user to search for a different topic. You can use the /search endpoint by sending a POST request to /search with JSON body containing 'search_term'. The endpoint will return a Wikipedia search results page."
    user_prompt = f"Generate a Wikipedia page about '{topic}'."
    html = call_llm_api(system_prompt, user_prompt)
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
