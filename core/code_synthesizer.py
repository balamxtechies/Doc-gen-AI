import re
import json
import logging
from typing import List, Tuple, Dict, Any
import numpy as np
import cv2

from .llm_client import gemini_client
from .local_ocr import local_ocr

logger = logging.getLogger(__name__)

CODE_SYNTHESIZER_SYSTEM_PROMPT = """You are an Autonomous Senior Python & Computer Vision Compiler.
An Admin has provided a sample document and an extraction prompt.
Local OCR has already scanned the document and provided every detected text line along with its 2D coordinates (bounding box, cx, cy, min_x, min_y, max_x, max_y).

YOUR MISSION:
Write a 100% STANDALONE, PURE PYTHON extraction script (`extractor.py`).
THIS GENERATED PYTHON SCRIPT WILL RUN LOCALLY WITHOUT ANY LLM OR AI APIS.
It must use regex, string matching, dictionary lookups, and spatial layout heuristics (e.g. finding text adjacent to or below landmark labels) based on the OCR items.

Return a JSON object conforming EXACTLY to this JSON format:
{
  "suggested_slug": "url_safe_name_lowercase_with_underscores",
  "display_name": "Formatted Display Name",
  "document_summary": "Short explanation of the document",
  "fields": [
    {
      "key": "snake_case_key",
      "label": "Human Readable Label",
      "type": "string|number|date|boolean|array|object",
      "description": "What this field captures"
    }
  ],
  "json_schema": {
    "type": "object",
    "properties": {
      "key_name": {"type": "string|number|array|object", "description": "..."}
    },
    "required": ["list_of_keys"]
  },
  "python_code": "COMPLETE_STANDALONE_PYTHON_SCRIPT_AS_A_STRING",
  "preview_extraction": {
    "key_name": "extracted_sample_value"
  }
}

CRITICAL RULES FOR `python_code`:
1. It MUST define a function:
   `def extract_document(ocr_items: list, full_text: str) -> dict:`
2. Each item in `ocr_items` is a dict:
   `{"text": str, "cx": float, "cy": float, "min_x": float, "min_y": float, "max_x": float, "max_y": float, "confidence": float}`
3. Use robust regex, fuzzy keyword matching, and spatial distance checks:
   - For example: To find a value next to "Label:", find the item containing "Label:", then look for items whose `cy` is close (same line) and `min_x` is to the right.
   - Or regex directly on `full_text` for standardized patterns (dates, IDs, amounts, PAN, emails, totals).
4. The function `extract_document` must return a dictionary whose keys match the `json_schema`.
5. The code MUST BE VALID, EXECUTABLE PYTHON 3 with NO dependencies other than standard library (`re`, `math`, `datetime`, `json`, `difflib`).
6. DO NOT include any calls to OpenAI, Gemini, Anthropic, or external networks in `python_code`. It must be 100% offline and deterministic.
"""

def clean_python_code(raw_code: str) -> str:
    """Removes markdown code fences if present"""
    code = raw_code.strip()
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    elif code.startswith("```"):
        code = code[len("```"):].strip()
    if code.endswith("```"):
        code = code[:-3].strip()
    return code

async def synthesize_document_code(
    doc_name: str,
    user_prompt: str,
    sample_images: List[Tuple[bytes, str]],
    model: str = "gemini-flash-latest"
) -> Dict[str, Any]:
    """
    1. Scans sample pages with local RapidOCR to acquire ground-truth text & coordinates.
    2. Sends the OCR tokens + sample image + prompt to Gemini ONCE.
    3. Gemini compiles pure Python extraction code (extractor.py) with zero AI runtime dependencies.
    """
    all_ocr_items: List[Dict[str, Any]] = []
    full_texts: List[str] = []

    # Run local OCR on the sample pages
    for img_bytes, _ in sample_images:
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            items, txt = local_ocr.extract_text_and_boxes(img)
            all_ocr_items.extend(items)
            full_texts.append(txt)

    combined_full_text = "\n-- PAGE BREAK --\n".join(full_texts)

    # Prepare OCR metadata summary for Gemini
    ocr_lines_summary = []
    for it in all_ocr_items[:80]: # Send up to 80 primary landmark tokens
        ocr_lines_summary.append(
            f"Line: \"{it['text']}\" at [x={int(it['min_x'])}-{int(it['max_x'])}, y={int(it['min_y'])}-{int(it['max_y'])}, center=({int(it['cx'])},{int(it['cy'])})]"
        )
    ocr_context = "\n".join(ocr_lines_summary)

    instruction = f"""
ADMIN GOAL:
- Document Type: "{doc_name}"
- Extraction Prompt: "{user_prompt}"

DOCUMENT SCAN RESULT (Local RapidOCR coordinates):
Full Text Detected:
{combined_full_text}

Sample OCR Tokens with Bounding Box Geometry:
{ocr_context}

Please write the complete standalone Python script (`extractor.py`), schema, field list, and preview extraction for this document.
"""

    result = await gemini_client.generate_content(
        prompt=instruction,
        images=sample_images,
        system_instruction=CODE_SYNTHESIZER_SYSTEM_PROMPT,
        model=model
    )

    # Clean and validate python code syntax
    py_code = clean_python_code(result.get("python_code", ""))
    result["python_code"] = py_code

    # Test syntax compilation
    try:
        compile(py_code, "extractor.py", "exec")
        result["syntax_valid"] = True
    except SyntaxError as e:
        logger.error(f"Generated Python code has syntax error: {e}")
        result["syntax_valid"] = False
        result["syntax_error"] = str(e)

    slug = re.sub(r'[^a-zA-Z0-9_\-\s]', '', result.get("suggested_slug", doc_name)).strip().lower()
    result["suggested_slug"] = re.sub(r'[\s\-]+', '_', slug) or "custom_document"

    return result
