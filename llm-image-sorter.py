#!/usr/bin/env python3
"""
LLM Image Sorter - Sorts images into subdirectories using an OpenAI-compatible LLM backend.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

import httpx
from openai import OpenAI


def encode_image(image_path: str) -> str:
    """Encode an image file to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_subdirectory_options(source_dir: str) -> list[str]:
    """Recursively get all subdirectory paths relative to source directory."""
    source_path = Path(source_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")
    
    subdirs = []
    for item in source_path.rglob("*"):
        if item.is_dir():
            rel_path = item.relative_to(source_path)
            subdirs.append(str(rel_path))
    
    return sorted(subdirs)


def build_messages(subdirectories: list[str], image_name: str, base64_image: str) -> list[dict]:
    """Build the system prompt and user messages for the LLM."""
    system_prompt = """You are an intelligent image sorting assistant. Your task is to analyze images and categorize them into appropriate subdirectories.

When given an image, examine its content carefully and determine which subdirectory it belongs in.

Respond with a JSON array containing exactly one element - the subdirectory name. Format: ["subdirectory_name"]"""
    
    subdir_list = "\n".join(f"  - {d}" for d in subdirectories)
    
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"I'm about to send you an image named: {image_name}"}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Available subdirectories to sort it into:\n{subdir_list}"}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Examine the image and tell me which subdirectory it belongs in. Respond with a JSON array containing exactly one element - the subdirectory name. Format: [\"subdirectory_name\"]"}
            ]
        }
    ]
    
    return messages


def query_llm(
    messages: list[dict],
    base_url: str,
    model: str,
    api_key: str = "not-needed",
    timeout: float = 1800
) -> str:
    """Query the LLM backend with messages."""
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=httpx.Timeout(timeout)
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    
    return response.choices[0].message.content.strip()


def parse_llm_response(response: str) -> str | None:
    """Parse JSON array response and return the subdirectory name if valid."""
    import json
    
    try:
        parsed = json.loads(response)
        if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], str):
            return parsed[0]
        return None
    except json.JSONDecodeError:
        return None


def move_image(source_dir: str, image_name: str, category: str) -> str:
    """Move image to the sorted subdirectory."""
    source_path = Path(source_dir) / image_name
    dest_dir = source_path.parent / category
    dest_path = dest_dir / image_name
    
    if not dest_dir.exists():
        dest_dir.mkdir(parents=True)
    
    if dest_path.exists():
        base, ext = os.path.splitext(image_name)
        counter = 1
        while dest_path.exists():
            new_name = f"{base}_{counter}{ext}"
            dest_path = dest_dir / new_name
            counter += 1
    
    import shutil
    shutil.move(str(source_path), str(dest_path))
    
    return str(dest_path)


SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}


def get_images_in_directory(source_dir: str) -> list[str]:
    """Get all image files in the root of the source directory (not recursive)."""
    source_path = Path(source_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")
    
    images = []
    for item in source_path.iterdir():
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            images.append(item.name)
    
    return sorted(images)


def main():
    parser = argparse.ArgumentParser(
        description="Sort images into subdirectories using an LLM"
    )
    parser.add_argument(
        "source_dir",
        help="Source directory containing images and subdirectories"
    )
    parser.add_argument(
        "--base-url", "-b",
        default="http://localhost:11434",
        help="Base URL of the OpenAI-compatible API (default: http://localhost:11434)"
    )
    parser.add_argument(
        "--model", "-m",
        default="qwen3.5",
        help="Model name to use (default: qwen3.5)"
    )
    parser.add_argument(
        "--api-key", "-k",
        default="",
        help="API key for the backend (optional)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without moving the file"
    )
    
    args = parser.parse_args()
    
    try:
        subdirectories = get_subdirectory_options(args.source_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not subdirectories:
        print(f"Error: No subdirectories found in {args.source_dir}", file=sys.stderr)
        sys.exit(1)
    
    images = get_images_in_directory(args.source_dir)
    
    if not images:
        print(f"No images found in {args.source_dir}", file=sys.stderr)
        sys.exit(0)
    
    print(f"Found {len(images)} images to sort")
    print(f"Available categories: {', '.join(subdirectories)}")
    print(f"Using LLM at {args.base_url} with model {args.model}")
    print("-" * 50)
    
    for i, image_name in enumerate(images, 1):
        image_path = os.path.join(args.source_dir, image_name)
        
        print(f"\n[{i}/{len(images)}] Sorting: {image_name}")
        
        try:
            base64_image = encode_image(image_path)
        except Exception as e:
            print(f"  Error encoding image: {e}")
            continue
        
        messages = build_messages(subdirectories, image_name, base64_image)
        
        try:
            raw_response = query_llm(
                messages,
                args.base_url,
                args.model,
                args.api_key
            )
        except Exception as e:
            print(f"  Error querying LLM: {e}")
            continue
        
        print(f"  Raw response: {raw_response}")
        
        category = parse_llm_response(raw_response)
        
        if category is None:
            print(f"  Warning: Failed to parse JSON array response, skipping")
            continue
        
        print(f"  Parsed category: {category}")
        
        if category not in subdirectories:
            print(f"  Warning: '{category}' not in subdirectories, skipping")
            continue
        
        if args.dry_run:
            print(f"  (dry run) Would move to: {args.source_dir}/{category}/{image_name}")
        else:
            dest_path = move_image(args.source_dir, image_name, category)
            print(f"  Moved to: {dest_path}")


if __name__ == "__main__":
    main()
