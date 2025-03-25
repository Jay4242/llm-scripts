#!/usr/bin/env python3

import io
import sys
import requests
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from openai import OpenAI
import httpx

def download_pdf(url):
    """Downloads a PDF from the given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return io.BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: {e}")
        sys.exit(1)

def extract_text_from_pdf(pdf_file):
    """Extracts text from a PDF file using pdfminer.six."""
    resource_manager = PDFResourceManager()
    output_string = io.StringIO()
    laparams = LAParams()
    converter = TextConverter(resource_manager, output_string, laparams=laparams)
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    parser = PDFParser(pdf_file)
    document = PDFDocument(parser)

    for page in PDFPage.create_pages(document):
        page_interpreter.process_page(page)

    text = output_string.getvalue()

    converter.close()
    output_string.close()
    return text

def main():
    """Downloads a PDF, extracts text, and sends it to an LLM."""

    if len(sys.argv) < 2:
        print("Usage: llm-pdf.py <pdf_url>")
        sys.exit(1)

    pdf_url = sys.argv[1]
    system_prompt = "You are a sophistocated technical paper examiner."  # Replace with your system prompt
    pre_prompt = "The following is a scientific paper PDF we converted to text:"  # Replace with your pre-prompt
    post_prompt = "What is the main novel finding of this paper?  Output only the novel finding with no preamble or explanation."  # Replace with your post-prompt
    temperature = 0.7  # Replace with your desired temperature

    pdf_file = download_pdf(pdf_url)
    pdf_text = extract_text_from_pdf(pdf_file)

    # OpenAI setup
    client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))

    try:
        completion = client.chat.completions.create(
            model="gemma-3-4b-it-q8_0",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pre_prompt},
                {"role": "user", "content": pdf_text},
                {"role": "user", "content": post_prompt},
            ],
            temperature=temperature,
            stream=True,
        )

        for chunk in completion:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print('\n')

    except Exception as e:
        print(f"Error during OpenAI completion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
