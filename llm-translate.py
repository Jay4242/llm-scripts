#!/usr/bin/env python3
"""
A simple Flask web UI for translating text using an LLM backend.
"""

import httpx
from openai import OpenAI
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>LLM Translation</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; }
    textarea { width: 100%; height: 150px; }
    .output { background:#f0f0f0; }
  </style>
</head>
<body>
  <h1>LLM Translation</h1>
  <form method="post">
    <label for="source">Text to translate:</label><br>
    <textarea id="source" name="source" required>{{ input_text|default('') }}</textarea><br><br>
    <label for="target_lang">Target language (e.g., French, Spanish):</label><br>
    <input type="text" id="target_lang" name="target_lang" placeholder="French" required
           value="{{ target_lang|default('French') }}"><br><br>
    <button type="submit">Translate</button>
  </form>
  <h2>Translation</h2>
  <textarea class="output" readonly>{{ translation }}</textarea>
  <button id="copyBtn" type="button">Copy Text</button>
<script>
document.querySelector('form').addEventListener('submit', async e => {
  e.preventDefault();
  const source = document.getElementById('source').value;
  const target_lang = document.getElementById('target_lang').value;
  const resp = await fetch('/translate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({source, target_lang})
  });
  const data = await resp.json();
  const outputArea = document.querySelector('.output');
  outputArea.value = data.translation;
});
document.getElementById('copyBtn').addEventListener('click', () => {
  const outputArea = document.querySelector('.output');
  outputArea.select();
  navigator.clipboard.writeText(outputArea.value);
});
</script>
</body>
</html>
"""

# Fixed parameters for the LLM script
SYSTEM_PROMPT = "You are a helpful translation assistant."
TEMPERATURE = "0.2"


def run_translation(text: str, target_lang: str) -> str:
    """Run the LLM translation using the embedded OpenAI client."""
    preprompt = f"Translate the following text to {target_lang}:"
    postprompt = ""

    client = OpenAI(
        base_url="http://localhost:9090/v1",
        api_key="none",
        timeout=httpx.Timeout(120),
    )

    try:
        completion = client.chat.completions.create(
            model="Qwen3-30B-A3B-q8_0",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": preprompt},
                {"role": "user", "content": text},
                {"role": "user", "content": postprompt},
            ],
            temperature=float(TEMPERATURE),
            stream=True,
        )
        output = ""
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                output += chunk.choices[0].delta.content
        return output.strip()
    except Exception as e:
        return f"Error during translation: {str(e)}"


@app.route("/", methods=["GET", "POST"])
def index():
    translation = ""
    source = ""
    target_lang = "French"
    if request.method == "POST":
        source = request.form.get("source", "")
        target_lang = request.form.get("target_lang", "French")
        if source:
            translation = run_translation(source, target_lang)
    return render_template_string(
        HTML_TEMPLATE,
        input_text=source,
        target_lang=target_lang,
        translation=translation,
    )


@app.route("/translate", methods=["POST"])
def translate():
    """AJAX endpoint returning JSON translation."""
    payload = request.get_json(silent=True) or {}
    source = payload.get("source", "")
    target_lang = payload.get("target_lang", "French")
    translation = ""
    if source:
        translation = run_translation(source, target_lang)
    return jsonify({"translation": translation})

if __name__ == "__main__":
    # Run on localhost:5000, accessible from the host machine
    app.run(host="127.0.0.1", port=5000, debug=True)
