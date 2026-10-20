import asyncio
import base64
import json
import logging
from typing import List, Tuple, Dict, Any, Optional
import httpx
from .config import settings

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

class GeminiClient:
    def __init__(self):
        self.timeout = httpx.Timeout(120.0, connect=20.0)

    def _get_api_key(self) -> str:
        key = settings.api_key.strip()
        if not key:
            raise ValueError(
                "Gemini API Key is not configured. Please enter your Gemini API Key in the Admin Settings tab or in .env."
            )
        return key

    async def generate_content(
        self,
        prompt: str,
        images: Optional[List[Tuple[bytes, str]]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 4
    ) -> Dict[str, Any]:
        """
        Calls Gemini API with multimodal input (text + multiple images/PDF pages).
        Forces strict JSON output using responseMimeType="application/json".
        Includes automatic retry for temporary 503 high-demand or rate-limit spikes.
        """
        api_key = self._get_api_key()
        target_model = model or settings.default_model or "gemini-flash-latest"
        url = f"{GEMINI_API_BASE}/{target_model}:generateContent"

        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": api_key
        }

        parts: List[Dict[str, Any]] = []

        # Add images as inlineData base64 parts
        if images:
            for img_bytes, mime_type in images:
                b64_data = base64.b64encode(img_bytes).decode("utf-8")
                parts.append({
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": b64_data
                    }
                })

        # Add text prompt
        parts.append({"text": prompt})

        contents = [{"parts": parts}]

        generation_config: Dict[str, Any] = {
            "responseMimeType": "application/json",
            "temperature": 0.1,
            "maxOutputTokens": 8192
        }

        # If a strict schema is provided, attach it to generationConfig
        if json_schema:
            generation_config["responseSchema"] = json_schema

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        last_error = None
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, headers=headers, json=payload)

                    # If temporary high demand (503) or rate limit (429), retry
                    if resp.status_code == 429:
                        # If primary model hits daily quota, fallback to gemini-flash-lite-latest
                        if "flash-lite" not in target_model:
                            logger.warning(f"Model {target_model} quota reached (429). Falling back to gemini-flash-lite-latest...")
                            target_model = "gemini-flash-lite-latest"
                            url = f"{GEMINI_API_BASE}/{target_model}:generateContent"
                            await asyncio.sleep(1.0)
                            continue

                    if resp.status_code != 200:
                        err_text = resp.text
                        logger.error(f"Gemini API error ({resp.status_code}): {err_text}")
                        try:
                            err_json = resp.json()
                            msg = err_json.get("error", {}).get("message", err_text)
                        except Exception:
                            msg = err_text
                        raise RuntimeError(f"Gemini API Error [{resp.status_code}]: {msg}")

                    result_json = resp.json()
                    try:
                        candidate = result_json["candidates"][0]
                        text_content = candidate["content"]["parts"][0]["text"]
                        return json.loads(text_content)
                    except (KeyError, IndexError, json.JSONDecodeError) as e:
                        logger.error(f"Failed to parse Gemini output: {result_json}")
                        raise ValueError(f"Could not parse valid JSON from AI response: {str(e)}")

            except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_sec = 2.0 * (attempt + 1)
                    logger.warning(f"Connection timeout (attempt {attempt+1}/{max_retries}). Retrying in {wait_sec}s...")
                    await asyncio.sleep(wait_sec)
                else:
                    raise RuntimeError(f"Gemini API request timed out after {max_retries} attempts.")
            except Exception as e:
                last_error = e
                if "503" in str(e) and attempt < max_retries - 1:
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                raise

        raise RuntimeError(f"Gemini API failed after {max_retries} attempts: {str(last_error)}")

    async def test_connection(self, api_key: str, model: str = "gemini-flash-latest") -> Tuple[bool, str]:
        """Validates if the provided API key works with gemini-flash-latest"""
        test_url = f"{GEMINI_API_BASE}/{model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": api_key.strip()
        }
        payload = {
            "contents": [{"parts": [{"text": "Reply with JSON: {\"status\": \"ok\"}"}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
                    res = await client.post(test_url, headers=headers, json=payload)
                    if res.status_code == 200:
                        return True, f"API Key is valid and successfully connected to {model}!"
                    elif res.status_code in (503, 429) and attempt < 3:
                        await asyncio.sleep(2.0 * (attempt + 1))
                        continue
                    else:
                        return False, f"API Key test failed ({res.status_code}): {res.text}"
            except Exception as e:
                if attempt < 3:
                    await asyncio.sleep(2.0)
                    continue
                return False, f"Connection error: {str(e)}"

        return False, "Model is experiencing temporary high demand (503). Please retry in a few seconds."

gemini_client = GeminiClient()
