import logging
from typing import List, Dict, Any, Tuple
import numpy as np
import cv2
from rapidocr_onnxruntime import RapidOCR

logger = logging.getLogger(__name__)

class LocalOCREngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalOCREngine, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        logger.info("Initializing Local RapidOCR ONNX Runtime...")
        self.engine = RapidOCR(
            det_limit_side_len=720,
            det_limit_type="max",
            rec_batch_num=16
        )

    def extract_text_and_boxes(self, image: np.ndarray) -> Tuple[List[Dict[str, Any]], str]:
        """
        Runs local CPU OCR on an image and returns structured line items with spatial coordinates.
        """
        raw_results, _ = self.engine(image)
        if not raw_results:
            return [], ""

        items: List[Dict[str, Any]] = []
        for box, text, conf in raw_results:
            clean_text = str(text).strip()
            if not clean_text:
                continue

            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            cx = sum(xs) / 4.0
            cy = sum(ys) / 4.0

            items.append({
                "text": clean_text,
                "confidence": float(conf),
                "box": box,
                "cx": float(cx),
                "cy": float(cy),
                "min_x": float(min(xs)),
                "max_x": float(max(xs)),
                "min_y": float(min(ys)),
                "max_y": float(max(ys)),
                "width": float(max(xs) - min(xs)),
                "height": float(max(ys) - min(ys))
            })

        # Sort top-to-bottom
        items.sort(key=lambda x: x["cy"])
        full_text = "\n".join(item["text"] for item in items)
        return items, full_text

local_ocr = LocalOCREngine()
