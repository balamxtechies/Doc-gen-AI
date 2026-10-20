import re
import json
import logging
from typing import List, Tuple, Dict, Any
from .llm_client import gemini_client

logger = logging.getLogger(__name__)

META_SCHEMA_PROMPT = """You are an elite Intelligent Document Processing (IDP) Architect.
An Admin has provided one or more sample document images and an extraction prompt.

Your mission is to:
1. Examine the visual layout, fields, tables, and content of the sample document(s).
2. Interpret the Admin's extraction requirement prompt.
3. Produce a production-grade, strictly typed JSON extraction configuration.
4. Extract the actual real values from this sample document as a live preview.

Return a JSON object conforming EXACTLY to this structure:
{
  "suggested_slug": "url_safe_slug_lowercase_with_underscores (e.g. vendor_invoice)",
  "display_name": "Formatted Display Name",
  "document_summary": "1-2 sentence description of what this document type is",
  "fields": [
    {
      "key": "snake_case_key_name",
      "label": "Human Readable Label",
      "type": "string|number|date|boolean|array|object",
      "description": "Short explanation of what this field captures",
      "is_required": true
    }
  ],
  "json_schema": {
    "type": "object",
    "properties": {
      "key_name": {
        "type": "string|number|boolean|array|object",
        "description": "field description"
      }
    },
    "required": ["list_of_mandatory_keys"]
  },
  "runtime_system_prompt": "Precise, unambiguous extraction instructions for future instances of this document",
  "preview_extraction": {
    "key_name": "Actual extracted value from the provided sample document"
  }
}

Important Rules:
- If line items or repeating tabular data are requested, use an array of objects for `items`.
- Use clean, standard snake_case for field keys.
- Make sure `json_schema` is a valid JSON Schema object.
- Make sure `preview_extraction` strictly matches the generated `json_schema`.
"""

def slugify(text: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9_\-\s]', '', text).strip().lower()
    slug = re.sub(r'[\s\-]+', '_', slug)
    return slug or "custom_document"

async def analyze_and_generate_schema(
    doc_name: str,
    user_prompt: str,
    sample_images: List[Tuple[bytes, str]],
    model: str = None
) -> Dict[str, Any]:
    """
    Takes sample document pages and user extraction prompt,
    derives the formal schema, extraction prompt, and preview extraction data.
    """
    admin_instruction = f"""
ADMIN INPUT:
- Document Type Name: "{doc_name}"
- Extraction Instructions: "{user_prompt}"

Please analyze the attached sample document pages, determine the optimal schema, generate field definitions, and extract the sample data.
"""

    result = await gemini_client.generate_content(
        prompt=admin_instruction,
        images=sample_images,
        system_instruction=META_SCHEMA_PROMPT,
        model=model
    )

    # Ensure slug is safe and valid
    suggested_slug = result.get("suggested_slug", "")
    if not suggested_slug:
        suggested_slug = slugify(doc_name)
    else:
        suggested_slug = slugify(suggested_slug)

    result["suggested_slug"] = suggested_slug
    return result
