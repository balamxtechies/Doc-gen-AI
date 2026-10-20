# DocuGen AI - Autonomous Document API & Extraction Platform 🚀

A zero-code, autonomous **Intelligent Document Processing (IDP)** platform and **Instant REST API Generator** powered by **FastAPI** and **Google Gemini Multimodal AI**.

Instead of writing custom code, regexes, and parsers for each document type, an administrator simply uploads sample documents (multi-page PDF, PNG, JPG), writes an extraction prompt in plain English, and the platform **automatically synthesizes the JSON schema, tunes extraction rules, and provisions a live production REST API endpoint in under 60 seconds** — without developer intervention.

---

## 🌟 Key Features

1. **Autonomous Schema Synthesis (One-Time Learning)**:
   - Admin uploads 1-3 sample documents + plain English prompt (e.g. *"Extract invoice number, vendor, line items table, tax, and total"*).
   - AI visually inspects the layout, tables, and fields, derives a strict JSON Schema, generates field definitions, and presents a live extracted preview.
2. **Instant Zero-Code REST API Generation**:
   - One click on **"Publish & Activate Live REST API"** provisions:
     `POST /api/v1/extract/{document_slug}`
   - External systems (Mendix, ERP, mobile apps, web portals) can immediately start sending documents.
3. **Multi-Page & Multimodal Ingestion**:
   - Native support for multi-page PDFs, high-res scans, camera photos (PNG, JPG, WEBP) using `pypdfium2`.
4. **Universal Ingestion Formats**:
   - Accepts standard `multipart/form-data` file uploads, `application/json` with Base64 document strings, or raw binary streams.
5. **Interactive Testing Studio & APIs Hub**:
   - Modern, high-polish web dashboard with drag-and-drop testing, real-time JSON viewer, and API analytics.
6. **Mendix & Enterprise Integration Ready**:
   - Auto-generates ready-to-copy cURL commands and JSON schemas for Mendix JSON Import Mapping.

---

## 📁 Project Structure

```
AntiGravity P1/
├── main.py                     # FastAPI server, CORS, static UI mounts, health probes
├── run.bat                     # Windows 1-click launcher
├── requirements.txt            # Python dependencies (FastAPI, pypdfium2, httpx, etc.)
├── .env.example                # Configuration template
├── core/
│   ├── config.py               # Runtime settings & dynamic API key manager
│   ├── llm_client.py           # Google Gemini Multimodal client with strict JSON schema support
│   ├── schema_engine.py        # Autonomous schema synthesizer & preview extractor
│   ├── document_store.py       # File-based persistent registry (data/documents.json)
│   └── pdf_processor.py        # Multi-page PDF renderer & image optimizer
├── api/
│   ├── admin_routes.py         # Admin endpoints: /analyze, /publish, /documents, /settings
│   └── dynamic_routes.py       # Universal runtime endpoint: POST /api/v1/extract/{slug}
├── static/
│   ├── index.html              # Sleek Admin Studio & Active APIs Hub (Tailwind CSS)
│   └── app.js                  # Frontend workflow, file upload, API publishing & test modal
├── data/
│   └── documents.json          # Persistent registry of created APIs
└── tests/
    └── test_server.py          # Automated integration test suite
```

---

## ⚡ Quick Start

### 1. Launch the Server
Double-click `run.bat` or run:
```bash
venv\Scripts\python.exe main.py
```

The server will start at:
- **Admin Document Studio**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Configure Your Gemini API Key
1. Open [http://localhost:8000](http://localhost:8000) in your browser.
2. Click the **Settings** tab.
3. Paste your Google Gemini API Key (get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey)) and click **"Save & Verify API Key"**.

---

## 🛠️ How to Create & Use an Instant Document API

### Step 1: In the Admin Studio (`http://localhost:8000`)
1. Enter a **Document Type Name** (e.g. `Vendor Invoice`).
2. Enter your **Prompt** (or click a quick preset like Invoice, Identity Card, Receipt, Payslip).
3. Drag & drop 1-3 sample documents (PDF or images).
4. Click **"Analyze & Generate Schema with AI"**.
5. Review the discovered fields and live preview JSON.
6. Click **"Publish & Activate Live REST API"**.

### Step 2: Call the Live API from External Apps
Your new API is immediately active at `http://localhost:8000/api/v1/extract/{document_slug}`:

#### Example cURL:
```bash
curl -X POST "http://localhost:8000/api/v1/extract/vendor_invoice" \
     -F "file=@sample_invoice.pdf"
```

#### Example JSON Response:
```json
{
  "success": true,
  "status": "SUCCESS",
  "document_type": "vendor_invoice",
  "document_name": "Vendor Invoice",
  "page_count": 2,
  "processing_time_ms": 1420,
  "data": {
    "invoice_number": "INV-2026-0891",
    "invoice_date": "2026-10-12",
    "vendor_name": "Acme Industrial Supplies",
    "total_amount": 14250.00,
    "items": [
      {
        "description": "High Precision Bearings",
        "quantity": 10,
        "unit_price": 950.00,
        "amount": 9500.00
      }
    ]
  }
}
```
