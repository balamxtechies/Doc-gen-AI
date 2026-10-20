import io
import logging
from typing import List, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

def process_document_to_images(file_bytes: bytes, max_pages: int = 10, max_dim: int = 1600) -> List[Tuple[bytes, str]]:
    """
    Converts uploaded document bytes (PDF, JPG, PNG, WEBP) into a list of
    processed (image_bytes, mime_type) tuples suitable for multimodal LLM processing.
    """
    if not file_bytes:
        return []

    results: List[Tuple[bytes, str]] = []

    # Check if PDF
    if file_bytes.startswith(b'%PDF'):
        try:
            import pypdfium2
            pdf = pypdfium2.PdfDocument(file_bytes)
            num_pages = min(len(pdf), max_pages)
            for page_idx in range(num_pages):
                page = pdf[page_idx]
                pil_image = page.render(scale=1.5).to_pil()
                
                # Resize if page is unnecessarily huge
                w, h = pil_image.size
                if max(w, h) > max_dim:
                    scale = max_dim / float(max(w, h))
                    pil_image = pil_image.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

                img_buf = io.BytesIO()
                pil_image.save(img_buf, format="JPEG", quality=88)
                results.append((img_buf.getvalue(), "image/jpeg"))
            return results
        except Exception as e:
            logger.error(f"Error rendering PDF pages: {e}")
            raise ValueError(f"Could not parse PDF document: {str(e)}")

    # Otherwise process as standard image
    try:
        pil_image = Image.open(io.BytesIO(file_bytes))
        # Convert RGBA/Palette to RGB
        if pil_image.mode in ("RGBA", "P"):
            pil_image = pil_image.convert("RGB")

        w, h = pil_image.size
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            pil_image = pil_image.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        img_buf = io.BytesIO()
        pil_image.save(img_buf, format="JPEG", quality=90)
        results.append((img_buf.getvalue(), "image/jpeg"))
        return results
    except Exception as e:
        logger.error(f"Error processing image bytes: {e}")
        raise ValueError(f"Unsupported or corrupted image file: {str(e)}")
