#!/usr/bin/env python3

import io
import sys
import os
import base64
import argparse
import requests
import subprocess
import tempfile
from typing import List, Dict, Any, Tuple, Optional
from pdfminer.layout import LTTextLine, LTTextBox, LTImage, LTFigure, LAParams, LTRect, LTCurve
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


def detect_tables_in_layout(layout) -> List[Dict[str, Any]]:
    """Detect table regions in a pdfminer layout.
    
    Detects tables drawn as:
    1. LTLine elements forming a grid pattern (horizontal + vertical lines)
    
    Returns a list of table regions with their bounding boxes.
    """
    from pdfminer.layout import LTLine
    
    def collect_lines(elem):
        if isinstance(elem, LTLine):
            all_lines.append(elem)
        if hasattr(elem, '__iter__') and not isinstance(elem, str):
            for child in elem:
                collect_lines(child)
    
    all_lines = []
    for elem in layout:
        collect_lines(elem)
    
    if len(all_lines) < 4:
        return []
    
    horizontal_lines = []
    vertical_lines = []
    
    for line in all_lines:
        width = abs(line.x1 - line.x0)
        height = abs(line.y1 - line.y0)
        
        if width >= height and width > 30:
            horizontal_lines.append(line)
        elif height > width and height > 3:
            vertical_lines.append(line)
    
    if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
        return []
    
    def line_center(line):
        return ((line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2)
    
    def bbox_center(bbox):
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    def distance(p1, p2):
        return ((p1[0] - p2[0])**2 + **(p1[1] - p2[1])2) ** 0.5
    
    def lines_to_bbox(lines_h, lines_v):
        if not lines_h and not lines_v:
            return None
        all_lines = lines_h + lines_v
        min_x0 = min(min(l.x0, l.x1) for l in all_lines)
        min_y0 = min(min(l.y0, l.y1) for l in all_lines)
        max_x1 = max(max(l.x0, l.x1) for l in all_lines)
        max_y1 = max(max(l.y0, l.y1) for l in all_lines)
        return (min_x0, min_y0, max_x1, max_y1)
    
    def bbox_area(bbox):
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    
    def bboxes_overlap(bbox1, bbox2, threshold=0.3):
        x_overlap = max(0, min(bbox1[2], bbox2[2]) - max(bbox1[0], bbox2[0]))
        y_overlap = max(0, min(bbox1[3], bbox2[3]) - max(bbox1[1], bbox2[1]))
        overlap_area = x_overlap * y_overlap
        area1 = bbox_area(bbox1)
        area2 = bbox_area(bbox2)
        if area1 == 0 or area2 == 0:
            return False
        return overlap_area / min(area1, area2) > threshold
    
    def cluster_lines_into_tables(h_lines, v_lines, gap_threshold=50):
        if not h_lines or not v_lines:
            return []
        
        line_groups = []
        
        for h_line in h_lines:
            h_center = line_center(h_line)
            new_group = None
            
            for i, group in enumerate(line_groups):
                group_h_center = line_center(group['h_lines'][0])
                if abs(h_center[1] - group_h_center[1]) < gap_threshold:
                    if not new_group:
                        new_group = i
                    else:
                        line_groups[new_group]['h_lines'].extend(group['h_lines'])
                        line_groups[new_group]['v_lines'].extend(group['v_lines'])
                        line_groups.pop(i)
                        break
            
            if new_group is not None:
                line_groups[new_group]['h_lines'].append(h_line)
            else:
                line_groups.append({'h_lines': [h_line], 'v_lines': []})
        
        for v_line in v_lines:
            v_center = line_center(v_line)
            best_group = None
            best_dist = float('inf')
            
            for i, group in enumerate(line_groups):
                if not group['h_lines']:
                    continue
                group_bbox = lines_to_bbox(group['h_lines'], group['v_lines'])
                if group_bbox:
                    group_center = bbox_center(group_bbox)
                    dist = distance(v_center, group_center)
                    if dist < best_dist and dist < gap_threshold * 2:
                        best_dist = dist
                        best_group = i
            
            if best_group is not None:
                line_groups[best_group]['v_lines'].append(v_line)
            else:
                for i, group in enumerate(line_groups):
                    group_bbox = lines_to_bbox(group['h_lines'], group['v_lines'])
                    if group_bbox:
                        group_center = bbox_center(group_bbox)
                        if distance(v_center, group_center) < gap_threshold:
                            group['v_lines'].append(v_line)
                            break
        
        return [g for g in line_groups if len(g['h_lines']) >= 2 and len(g['v_lines']) >= 2]
    
    def validate_and_format_table(h_lines, v_lines):
        if len(h_lines) < 2 or len(v_lines) < 2:
            return None
        
        bbox = lines_to_bbox(h_lines, v_lines)
        if not bbox:
            return None
        
        table_width = bbox[2] - bbox[0]
        table_height = bbox[3] - bbox[1]
        
        if table_width < 50 or table_height < 15:
            return None
        
        h_spanning = [l for l in h_lines if abs(l.x1 - l.x0) > table_width * 0.4]
        
        v_cell_borders = [l for l in v_lines if abs(l.y1 - l.y0) >= 5]
        v_spanning = [l for l in v_lines if abs(l.y1 - l.y0) >= table_height * 0.5]
        
        v_final = v_cell_borders if len(v_cell_borders) >= 2 else v_spanning
        
        if len(h_spanning) < 2 or len(v_final) < 2:
            return None
        
        final_bbox = lines_to_bbox(h_spanning, v_final)
        if not final_bbox:
            return None
        
        return {
            'bbox': final_bbox,
            'source': 'lines',
            'count': len(h_spanning) + len(v_final),
            'details': f"{len(h_spanning)}H x {len(v_final)}V"
        }
    
    clustered_groups = cluster_lines_into_tables(horizontal_lines, vertical_lines)
    
    tables = []
    for group in clustered_groups:
        table_info = validate_and_format_table(group['h_lines'], group['v_lines'])
        if table_info:
            tables.append(table_info)
    
    return tables
    
    # Group lines into potential table regions
    # A table needs both horizontal and vertical lines forming a grid
    horizontal_lines = []
    vertical_lines = []
    
    for line in all_lines:
        width = abs(line.x1 - line.x0)
        height = abs(line.y1 - line.y0)
        
        if width >= height and width > 50:
            horizontal_lines.append(line)
        elif height > width and height > 5:
            vertical_lines.append(line)
    
    # Need both horizontal and vertical lines for a proper table
    if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
        return tables
    
    # Group lines by Y-position (horizontal) and X-position (vertical) to find grid structure
    h_y_positions = sorted(set(round(l.y0, 0) for l in horizontal_lines))
    v_x_positions = sorted(set(round(l.x0, 0) for l in vertical_lines))
    
    # A real table has multiple distinct horizontal and vertical grid lines
    if len(h_y_positions) < 2 or len(v_x_positions) < 2:
        return tables
    
    # Find connected components of lines that form table regions
    def group_lines_into_tables(h_lines, v_lines, y_positions, x_positions):
        if not h_lines or not v_lines:
            return []
        
        min_x0 = min(min(l.x0, l.x1) for l in h_lines + v_lines)
        min_y0 = min(min(l.y0, l.y1) for l in h_lines + v_lines)
        max_x1 = max(max(l.x0, l.x1) for l in h_lines + v_lines)
        max_y1 = max(max(l.y0, l.y1) for l in h_lines + v_lines)
        
        table_width = max_x1 - min_x0
        table_height = max_y1 - min_y0
        
        # Filter out very small detections (likely noise)
        if table_width < 80 or table_height < 20:
            return []
        
        # Check that horizontal lines span most of the table width
        h_spanning = [l for l in h_lines if abs(l.x1 - l.x0) > table_width * 0.5]
        
        # For vertical lines, accept both:
        # 1. Lines spanning full table height (column dividers)
        # 2. Lines spanning at least one cell height (cell borders)
        num_rows = len(h_y_positions) - 1 if len(h_y_positions) > 1 else 1
        min_cell_height = table_height / max(num_rows, 1)
        
        # Accept vertical lines that are at least 10px tall (small cell borders)
        v_cell_borders = [l for l in v_lines if abs(l.y1 - l.y0) >= 10]
        v_spanning = [l for l in v_lines if abs(l.y1 - l.y0) >= table_height * 0.8]
        
        # Use cell borders if we have enough, otherwise use spanning lines
        v_final = v_cell_borders if len(v_cell_borders) >= 2 else v_spanning
        
        if len(h_spanning) < 2 or len(v_final) < 2:
            return []
        
        # Recalculate bbox with spanning lines only
        min_x0 = min(min(l.x0, l.x1) for l in h_spanning + v_final)
        min_y0 = min(min(l.y0, l.y1) for l in h_spanning + v_final)
        max_x1 = max(max(l.x0, l.x1) for l in h_spanning + v_final)
        max_y1 = max(max(l.y0, l.y1) for l in h_spanning + v_final)
        
        return [{
            'bbox': (min_x0, min_y0, max_x1, max_y1),
            'source': 'lines',
            'count': len(h_spanning) + len(v_final),
            'details': f"{len(h_spanning)}H x {len(v_final)}V"
        }]
    
    tables = group_lines_into_tables(horizontal_lines, vertical_lines, h_y_positions, v_x_positions)
    
    return tables


def convert_page_to_image(pdf_path: str, page_num: int, dpi: int = 200) -> Optional[str]:
    """Convert a PDF page to JPEG using pdftoppm.
    
    Returns path to the generated image or None on failure.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = tmp.name
        
        output_prefix = tmp_path.rsplit('.', 1)[0]
        
        result = subprocess.run(
            ['pdftoppm', '-jpeg', '-f', str(page_num + 1), '-l', str(page_num + 1), 
             '-r', str(dpi), pdf_path, output_prefix],
            capture_output=True, timeout=60
        )
        
        if result.returncode == 0:
            jpg_path = f"{output_prefix}-{page_num + 1}.jpg"
            if os.path.exists(jpg_path):
                return jpg_path
        
        os.unlink(tmp_path)
        return None
    except Exception as e:
        print(f"Warning: Could not convert page to image: {e}")
        return None


def crop_table_region(image_path: str, table_bbox: Tuple[float, float, float, float], 
                      page_size: Tuple[float, float], dpi: int = 200) -> Optional[bytes]:
    """Crop a table region from a page image.
    
    Args:
        image_path: Path to the full page image
        table_bbox: Table bounding box in PDF coordinates (x0, y0, x1, y1)
        page_size: Page size in PDF points (width, height)
        dpi: DPI used for image conversion
    
    Returns:
        Image bytes or None on failure
    """
    try:
        from PIL import Image
        
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        pdf_width, pdf_height = page_size
        scale_x = img_width / pdf_width
        scale_y = img_height / pdf_height
        
        x0, y0, x1, y1 = table_bbox
        
        img_x0 = int(x0 * scale_x)
        img_y0 = int((pdf_height - y1) * scale_y)
        img_x1 = int(x1 * scale_x)
        img_y1 = int((pdf_height - y0) * scale_y)
        
        table_img = img.crop((img_x0, img_y0, img_x1, img_y1))
        
        output = io.BytesIO()
        table_img.save(output, format='JPEG', quality=90)
        return output.getvalue()
    except Exception as e:
        print(f"Warning: Could not crop table region: {e}")
        return None


def extract_tables_with_images(pdf_path: str, pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """Extract tables from PDF as images using pdfminer detection and pdftoppm rendering.
    
    Returns list of table images with metadata.
    """
    tables = []
    
    try:
        from PIL import Image
    except ImportError:
        print("Warning: PIL not available for table extraction")
        return tables
    
    parser = PDFParser(io.BytesIO(pdf_bytes))
    document = PDFDocument(parser)
    
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    
    for page_num, page in enumerate(PDFPage.create_pages(document)):
        interpreter.process_page(page)
        layout = device.get_result()
        
        detected_tables = detect_tables_in_layout(layout)
        
        if detected_tables:
            page_size = (layout.width, layout.height)
            image_path = convert_page_to_image(pdf_path, page_num, dpi=200)
            
            if image_path:
                for table_info in detected_tables:
                    table_bytes = crop_table_region(
                        image_path, table_info['bbox'], page_size, dpi=200
                    )
                    if table_bytes:
                        tables.append({
                            'page': page_num,
                            'bbox': table_info['bbox'],
                            'content': table_bytes,
                            'mime_type': 'image/jpeg'
                        })
                os.unlink(image_path)
    
    device.close()
    return tables


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
        if isinstance(elem, (LTTextLine, LTTextBox)):
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
        elif item['type'] == 'table':
            size_kb = len(item['content']) / 1024
            output.append(f"[{i}] TABLE (page {item['page']}):")
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
    """Build OpenAI-compatible messages with interlaced text, images and tables."""
    user_content = []
    
    # Add pre-prompt
    if pre_prompt:
        user_content.append({'type': 'text', 'text': pre_prompt})
    
    # Add text, images and tables in order
    for item in items:
        if item['type'] == 'text':
            user_content.append({'type': 'text', 'text': item['content']})
        elif item['type'] in ('image', 'table'):
            b64_data = base64.b64encode(item['content']).decode('utf-8')
            data_url = f"data:{item['mime_type']};base64,{b64_data}"
            item_type = 'table' if item['type'] == 'table' else 'image'
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
    parser.add_argument('--extract-tables', action='store_true', help='Detect and extract tables as images')
    args = parser.parse_args()
    
    pre_prompt = "The following is a scientific paper PDF with text and images:"
    post_prompt = "Create an opinion about this paper. Make it short and concise, at most a few sentences."
    temperature = 0.7
    
    pdf_file = download_pdf(args.pdf_url)
    raw_bytes = pdf_file.read()
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_pdf_path = tmp.name
    
    try:
        items = extract_text_and_images_with_order(io.BytesIO(raw_bytes))
        
        if args.extract_tables:
            table_images = extract_tables_with_images(tmp_pdf_path, raw_bytes)
            if args.debug:
                print(f"\nExtracted {len(table_images)} table images")
            
            for table_img in table_images:
                items.append({
                    'type': 'table',
                    'content': table_img['content'],
                    'mime_type': table_img['mime_type'],
                    'page': table_img['page']
                })
    finally:
        os.unlink(tmp_pdf_path)
    
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
