#!/bin/python3

import sys
from openai import OpenAI
import webbrowser
import base64

def main():
    # Check for the correct number of arguments
    if len(sys.argv) < 2:
        print("Usage: llm-mermaid.py <user_prompt>")
        sys.exit(1)

    user_prompt = sys.argv[1]
    temperature = 0.7

    system_prompt = "You are a mermaid.js diagram generator.  You ONLY respond with valid mermaid.js code blocks.  Do not include any other text."

    # Point to the local server
    client = OpenAI(base_url="http://localhost:9090/v1", api_key="none")

    try:
        completion = client.chat.completions.create(
            model="gemma-3-4b-it-q8_0",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
        )

        content = completion.choices[0].message.content.strip()
        lines = content.splitlines()

        # Remove the first line if it's ```mermaid
        if lines and lines[0].strip() == "```mermaid":
            lines.pop(0)

        # Remove the last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines.pop()

        mermaid_code = '\n'.join(lines)

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Mermaid Diagram</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</head>
<body>
    <div class="mermaid">
        {mermaid_code}
    </div>
</body>
</html>
"""

        # Encode the HTML content to base64
        html_content_encoded = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')

        # Create the data URI
        data_uri = f"data:text/html;base64,{html_content_encoded}"

        print("Opening diagram in browser")
        webbrowser.open(data_uri)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
