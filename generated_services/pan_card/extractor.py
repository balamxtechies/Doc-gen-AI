import re

def extract_document(ocr_items: list, full_text: str) -> dict:
    pan_number = None
    
    # Strategy 1: Regex on full text for standard PAN format (5 letters, 4 digits, 1 letter)
    pan_pattern = re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]')
    match = pan_pattern.search(full_text)
    if match:
        pan_number = match.group(0)
    
    # Strategy 2: If regex fails, inspect ocr_items near keywords or standalone format
    if not pan_number:
        for item in ocr_items:
            text = item.get('text', '').replace(' ', '')
            if pan_pattern.fullmatch(text):
                pan_number = text
                break
                
    return {
        "pan_number": pan_number
    }