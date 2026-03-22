#!/usr/bin/env python3

import io
import sys
import os
import base64
import argparse
import requests
from typing import List, Dict, Any, Tuple, Optional
from pdfminer.layout import LTTextLine, LTTextBox, LTImage, LTFigure, LAParams
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from openai import OpenAI
import httpx


def download_pdf(url: str) -> io.BytesIO:
    """Downloads a PDF from the given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return io.BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: {e}")
        sys.exit(1)


def extract_images_from_stream(stream: bytes) -> List[Tuple[bytes, str, int]]:
    """Extract images from PDF bytes using pdfminer.six.
    
    Returns list of tuples (image_data, mime_type, page_number).
    """
    images = []
    pdf_file = io.BytesIO(stream)
    
    parser = PDFParser(pdf_file)
    document = PDFDocument(parser)
    
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    
    def find_images_recursive(elem, images_list, page_num):
        if isinstance(elem, LTImage):
            images_list.append((elem, page_num))
        if hasattr(elem, '__iter__'):
            for child in elem:
                find_images_recursive(child, images_list, page_num)
    
    for page_num, page in enumerate(PDFPage.create_pages(document)):
        interpreter.process_page(page)
        layout = device.get_result()
        
        page_images = []
        find_images_recursive(layout, page_images, page_num)
        
        for obj, page_idx in page_images:
            try:
                image_stream = obj.stream
                image_data = image_stream.get_data()
                
                filters = image_stream.get('Filter')
                if filters:
                    if not isinstance(filters, list):
                        filters = [filters]
                    
                    mime_type = 'image/png'
                    for f in filters:
                        f_str = str(f)
                        if '/DCTDecode' in f_str or '/JPXDecode' in f_str:
                            mime_type = 'image/jpeg'
                            break
                        elif '/FlateDecode' in f_str:
                            mime_type = 'image/png'
                            break
                        elif '/CCITTFaxDecode' in f_str:
                            mime_type = 'image/tiff'
                            break
                        elif '/JBIG2Decode' in f_str:
                            mime_type = 'image/jb2'
                            break
                else:
                    mime_type = 'image/png'
                
                images.append((image_data, mime_type, page_idx))
            except Exception as e:
                print(f"Warning: Could not extract image: {e}")
    
    device.close()
    return images


def extract_text_and_images_with_order(pdf_file: io.BytesIO) -> List[Dict[str, Any]]:
    """Extract text and images from PDF, preserving order.
    
    Returns a list of items, each with 'type' ('text' or 'image') and 'content'.
    """
    pdf_file.seek(0)
    raw_bytes = pdf_file.read()
    
    parser = PDFParser(io.BytesIO(raw_bytes))
    document = PDFDocument(parser)
    
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    
    items = []
    
    def find_images_recursive(elem, images_list):
        if isinstance(elem, LTImage):
            images_list.append(elem)
        if hasattr(elem, '__iter__'):
            for child in elem:
                find_images_recursive(child, images_list)
    
    def extract_text_recursive(elem, text_list):
        if isinstance(element, (LTTextLine, LTTextBox)):
            text = elem.get_text()
            if text.strip():
                text_list.append((text, elem.bbox))
        if hasattr(elem, '__iter__'):
            for child in elem:
                extract_text_recursive(child, text_list)
    
    for page_num, page in enumerate(PDFPage.create_pages(document)):
        interpreter.process_page(page)
        layout = device.get_result()
        
        page_items = []
        
        # Collect text
        for element in layout:
            if isinstance(element, (LTTextLine, LTTextBox)):
                text = element.get_text()
                if text.strip():
                    bbox = element.bbox
                    page_items.append({
                        'type': 'text',
                        'content': text,
                        'bbox': bbox,
                        'order': (bbox[1], bbox[0])
                    })
            elif isinstance(element, LTImage):
                bbox = element.bbox
                page_items.append({
                    'type': 'image',
                    'element': element,
                    'bbox': bbox,
                    'order': (bbox[1], bbox[0])
                })
            elif isinstance(element, LTFigure):
                images_in_figure = []
                find_images_recursive(element, images_in_figure)
                for img in images_in_figure:
                    bbox = img.bbox
                    page_items.append({
                        'type': 'image',
                        'element': img,
                        'bbox': bbox,
                        'order': (bbox[1], bbox[0])
                    })
        
        page_items.sort(key=lambda x: x['order'])
        
        for item in page_items:
            if item['type'] == 'text':
                items.append({
                    'type': 'text',
                    'content': item['content'],
                    'page': page_num
                })
            else:
                items.append({
                    'type': 'image_placeholder',
                    'page': page_num
                })
    
    device.close()
    
    images = extract_images_from_stream(raw_bytes)
    
    image_index = 0
    final_items = []
    for item in items:
        if item['type'] == 'image_placeholder':
            if image_index < len(images):
                final_items.append({
                    'type': 'image',
                    'content': images[image_index][0],
                    'mime_type': images[image_index][1],
                    'page': images[image_index][2]
                })
                image_index += 1
            else:
                final_items.append(item)
        else:
            final_items.append(item)
    
    return final_items


def format_content_for_debug(items: List[Dict[str, Any]]) -> str:
    """Format content for debug output."""
    output = []
    output.append("=" * 60)
    output.append("EXTRACTED CONTENT FROM PDF")
    output.append("=" * 60)
    
    for i, item in enumerate(items):
        if item['type'] == 'text':
            content_preview = item['content'][:100].replace('\n', ' ').strip()
            if len(item['content']) > 100:
                content_preview += "..."
            output.append(f"[{i}] TEXT (page {item['page']}):")
            output.append(f"    {content_preview}")
        elif item['type'] == 'image':
            size_kb = len(item['content']) / 1024
            output.append(f"[{i}] IMAGE (page {item['page']}):")
            output.append(f"    MIME: {item['mime_type']}, Size: {size_kb:.1f} KB")
    
    return '\n'.join(output)


def format_messages_for_debug(messages: List[Dict[str, Any]]) -> str:
    """Format full messages structure for debug output."""
    output = []
    output.append("")
    output.append("=" * 60)
    output.append("FULL MESSAGES STRUCTURE FOR LLM")
    output.append("=" * 60)
    
    for msg_idx, msg in enumerate(messages):
        role = msg['role']
        content = msg['content']
        
        if role == 'system':
            output.append(f"\nMessage {msg_idx} (system):")
            output.append(f"  {content}")
        else:
            output.append(f"\nMessage {msg_idx} (user):")
            if isinstance(content, list):
                for item_idx, item in enumerate(content):
                    if item['type'] == 'text':
                        text = item['text']
                        if len(text) > 200:
                            text = text[:200] + "..."
                        output.append(f"  [{item_idx}] text: {text}")
                    elif item['type'] == 'image_url':
                        url = item['image_url']['url']
                        # Truncate base64 data for readability
                        if len(url) > 100:
                            url = url[:50] + "..." + url[-20:]
                        output.append(f"  [{item_idx}] image_url: {url}")
            else:
                output.append(f"  {content}")
    
    output.append("\n" + "=" * 60)
    return '\n'.join(output)


def build_messages(items: List[Dict[str, Any]], pre_prompt: str, post_prompt: str) -> List[Dict[str, Any]]:
    """Build OpenAI-compatible messages with interlaced text and images."""
    user_content = []
    
    # Add pre-prompt
    if pre_prompt:
        user_content.append({'type': 'text', 'text': pre_prompt})
    
    # Add text and images in order
    for item in items:
        if item['type'] == 'text':
            user_content.append({'type': 'text', 'text': item['content']})
        elif item['type'] == 'image':
            # Convert image to base64
            b64_data = base64.b64encode(item['content']).decode('utf-8')
            data_url = f"data:{item['mime_type']};base64,{b64_data}"
            user_content.append({
                'type': 'image_url',
                'image_url': {'url': data_url}
            })
    
    # Add post-prompt
    if post_prompt:
        user_content.append({'type': 'text', 'text': post_prompt})
    
    return [
        {'role': 'system', 'content': 'You are a sophisticated technical paper examiner.'},
        {'role': 'user', 'content': user_content}
    ]


def main():
    """Downloads a PDF, extracts text and images, and sends to multimodal LLM."""
    
    parser = argparse.ArgumentParser(description='Process PDF with multimodal LLM')
    parser.add_argument('pdf_url', help='URL to the PDF file')
    parser.add_argument('--debug', action='store_true', help='Show context being sent to LLM')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be sent to LLM without sending')
    parser.add_argument('--base-url', default="http://localhost:1234", help='Base URL for the LLM API (default: http://localhost:1234)')
    parser.add_argument('--api-key', default="none", help='API key for the LLM (default: none)')
    parser.add_argument('--model', default="qwen3.5", help='Model name to use (default: qwen3.5)')
    args = parser.parse_args()
    
    pre_prompt = "The following is a scientific paper PDF with text and images:"
    post_prompt = "Create an opinion about this paper. Make it short and concise, at most a few sentences."
    temperature = 0.7
    
    pdf_file = download_pdf(args.pdf_url)
    raw_bytes = pdf_file.read()
    
    # Extract text and images with order preserved
    items = extract_text_and_images_with_order(io.BytesIO(raw_bytes))
    
    if not items:
        print("Warning: No text or images extracted from PDF.")
        sys.exit(0)
    
    # Build messages
    messages = build_messages(items, pre_prompt, post_prompt)
    
    if args.debug or args.dry_run:
        print(format_content_for_debug(items))
        print(format_messages_for_debug(messages))
        print()
    
    # OpenAI setup - using the new endpoint
    client = OpenAI(
        base_url=args.base_url, 
        api_key=args.api_key, 
        timeout=httpx.Timeout(3600)
    )
    
    if args.dry_run:
        print(f"Dry run complete. Would have sent to: {client.base_url}")
        sys.exit(0)
    
    try:
        completion = client.chat.completions.create(
            model=args.model,
            messages=messages,
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
