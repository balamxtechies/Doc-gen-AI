import os
import sys
import json
import time
import socket
import logging
import importlib.util
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

import cv2
import numpy as np

from .config import BASE_DIR, DATA_DIR
from .local_ocr import local_ocr

logger = logging.getLogger(__name__)

SERVICES_STATE_FILE = DATA_DIR / "active_services.json"

class ServiceManager:
    def __init__(self):
        self.services_dir = BASE_DIR / "generated_services"
        self.services_dir.mkdir(exist_ok=True)
        self.running_processes: Dict[str, subprocess.Popen] = {}
        self._ensure_state_file()

    def _ensure_state_file(self):
        if not SERVICES_STATE_FILE.exists():
            with open(SERVICES_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def _load_state(self) -> Dict[str, Any]:
        try:
            with open(SERVICES_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_state(self, state: Dict[str, Any]):
        with open(SERVICES_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def find_free_port(self, start_port: int = 8001) -> int:
        """Finds an unused TCP port starting from 8001"""
        state = self._load_state()
        used_ports = [v.get("port") for v in state.values() if v.get("port")]

        port = start_port
        while port < 8100:
            if port in used_ports:
                port += 1
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                res = s.connect_ex(("127.0.0.1", port))
                if res != 0: # Port is open and free
                    return port
            port += 1
        return 8099

    def start_service(self, slug: str, name: str, port: int, service_dir: Path) -> Dict[str, Any]:
        """
        Launches the generated standalone microservice as a parallel background process.
        Both applications run in parallel on separate ports!
        """
        python_exe = sys.executable

        # Command to start the standalone service on its dedicated port
        cmd = [
            python_exe,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port)
        ]

        logger.info(f"Launching standalone service for '{slug}' on port {port}: {' '.join(cmd)}")
        # On Windows, launch with CREATE_NEW_CONSOLE so the user can physically see the terminal window!
        creation_flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0

        proc = subprocess.Popen(
            cmd,
            cwd=str(service_dir),
            creationflags=creation_flags
        )

        self.running_processes[slug] = proc

        service_info = {
            "slug": slug,
            "name": name,
            "port": port,
            "pid": proc.pid,
            "endpoint_url": f"http://localhost:{port}/extract",
            "service_dir": str(service_dir),
            "status": "RUNNING",
            "mode": "100% Local / Zero AI Service"
        }

        state = self._load_state()
        state[slug] = service_info
        self._save_state(state)

        return service_info

    def get_service_info(self, slug: str) -> Optional[Dict[str, Any]]:
        state = self._load_state()
        return state.get(slug)

    def execute_local_extraction(self, slug: str, file_bytes: bytes) -> Dict[str, Any]:
        """
        Executes document extraction using the generated Python code and local RapidOCR.
        ZERO GEMINI CALLS. 100% OFFLINE, RUNS IN < 200ms.
        """
        service_dir = self.services_dir / slug
        extractor_path = service_dir / "extractor.py"

        if not extractor_path.exists():
            raise FileNotFoundError(f"No generated code found for '{slug}' at {extractor_path}")

        # 1. Run local RapidOCR to get items and full_text
        if file_bytes.startswith(b"%PDF"):
            import pypdfium2
            pdf = pypdfium2.PdfDocument(file_bytes)
            page = pdf[0]
            pil_img = page.render(scale=1.5).to_pil()
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Could not decode document image.")

        ocr_items, full_text = local_ocr.extract_text_and_boxes(img)

        # 2. Dynamically import and execute the generated standalone extractor
        spec = importlib.util.spec_from_file_location(f"extractor_{slug}", str(extractor_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "extract_document"):
            raise AttributeError(f"Generated extractor for '{slug}' does not define 'extract_document'")

        # 3. Call the generated Python code
        extracted_data = module.extract_document(ocr_items, full_text)

        return extracted_data

service_manager = ServiceManager()
