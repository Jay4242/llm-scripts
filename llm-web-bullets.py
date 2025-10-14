#!/usr/bin/env python3
"""
llm-web-bullets.py

Fetch one or more webpages, extract the visible text from the <body> using BeautifulSoup,
and send each to a local LLM backend (compatible with OpenAI's client API) for summarization.
The script accepts multiple URLs as positional arguments and an optional ``--debug`` flag.
Prompts, model, and temperature are hard‑coded within the script.

Usage:
    python llm-web-bullets.py <url1> [<url2> ...] [--debug]

Example:
    python llm-web-bullets.py https://example.com https://example.org --debug
"""

import argparse
import sys
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import httpx
from typing import Dict

# Base URL for the local LLM backend – change in one place if needed.
BASE_URL = "http://localhost:9090/v1"

# Configuration variables – adjust here to change the LLM client behavior.
API_KEY = "None"
TIMEOUT = httpx.Timeout(3600)
USER_AGENT = "llm-web-bullets/1.0"
MODEL = "Qwen3-30B-A3B-Instruct-2507-Q8_0"
TEMPERATURE = 0.0  # default temperature, adjust as needed

def fetch_body_text(url: str) -> str:
    """Download the page at *url* and return the cleaned body text."""
    response = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    # Prefer the <body> tag; fall back to the whole document if missing.
    if soup.body:
        return soup.body.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)


def summarize(document: str, url: str) -> str:
    """Send *document* to the local LLM backend and return the streamed summary."""
    system_prompt = "You are a helpful assistant."
    pre_prompt = f"The following is the text from {url}:"
    post_prompt = "Create a complete but concise multi-tier bullet point summary of this article."
    temperature = TEMPERATURE  # configurable temperature

    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=TIMEOUT,
    )

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pre_prompt},
            {"role": "user", "content": document},
            {"role": "user", "content": post_prompt},
        ],
        temperature=temperature,
        stream=True,
    )

    result = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            result += chunk.choices[0].delta.content
    return result


def reconcile(summaries: Dict[str, str]) -> str:
    """
    Send the collected bullet‑point summaries to the LLM backend and ask it to
    reconcile them into a cohesive summary.

    *summaries* is a mapping of URL → bullet‑point summary.
    """
    system_prompt = "You are a helpful assistant."
    # Build the message list with a separate user entry for each URL and its summary.
    messages = [{"role": "system", "content": system_prompt}]

    for url, summary in summaries.items():
        messages.append(
            {"role": "user", "content": f"The following is the bullet point summary of {url}:"}
        )
        messages.append({"role": "user", "content": summary})

    # Final instruction to the model.
    messages.append(
        {
            "role": "user",
            "content": "Please reconcile these summaries into a single concise multi‑tier bullet point summary.",
        }
    )

    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=TIMEOUT,
    )

    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        stream=True,
    )

    result = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            result += chunk.choices[0].delta.content
    return result

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch webpages, summarize them with an LLM, and reconcile the summaries."
    )
    parser.add_argument(
        "urls",
        nargs="+",
        help="One or more URLs to process.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug information to stderr.",
    )
    args = parser.parse_args()

    urls = args.urls
    debug = args.debug

    # Collect summaries for each URL.
    summaries: Dict[str, str] = {}
    for url in urls:
        document = fetch_body_text(url)
        if debug:
            print(f"[DEBUG] Cleaned body text for {url}:", file=sys.stderr)
            print(document, file=sys.stderr)
            print("-" * 80, file=sys.stderr)

        summary = summarize(document, url)
        if debug:
            print(f"[DEBUG] Bullet‑point summary for {url}:", file=sys.stderr)
            print(summary, file=sys.stderr)
            print("-" * 80, file=sys.stderr)

        summaries[url] = summary

    # Reconcile all summaries into a single output.
    final_summary = reconcile(summaries)

    print(final_summary)


if __name__ == "__main__":
    main()
