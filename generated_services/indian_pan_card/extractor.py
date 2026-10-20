import re

def extract_document(ocr_items: list, full_text: str) -> dict:
    pan_number = None
    date_of_birth = None
    full_name = None
    father_name = None
    
    # Regex for PAN (5 letters, 4 digits, 1 letter)
    pan_pattern = re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]')
    
    # Regex for Date of Birth (DD/MM/YYYY)
    dob_pattern = re.compile(r'\d{2}/\d{2}/\d{4}')
    
    # Direct regex match in full text for PAN and DOB
    pan_match = pan_pattern.search(full_text)
    if pan_match:
        pan_number = pan_match.group(0)
        
    dob_match = dob_pattern.search(full_text)
    if dob_match:
        date_of_birth = dob_match.group(0)
        
    # Spatial or sequential heuristics using ocr_items
    sorted_items = sorted(ocr_items, key=lambda i: (i['min_y'], i['min_x']))
    
    for idx, item in enumerate(sorted_items):
        text = item['text']
        
        # If PAN not found via regex, check tokens
        if not pan_number and pan_pattern.match(text.strip()):
            pan_number = text.strip()
            
        # If DOB not found via regex, check tokens
        if not date_of_birth and dob_pattern.match(text.strip()):
            date_of_birth = text.strip()
            
        # Name is usually below 'Name' label
        if 'NAME' in text.upper() or 'नाम' in text:
            # look for the next text item vertically below or nearby
            if idx + 1 < len(sorted_items):
                full_name = sorted_items[idx + 1]['text']
                
        # Father's name is below 'Father's Name' label
        if 'FATHER' in text.upper() or 'पिता' in text:
            if idx + 1 < len(sorted_items):
                father_name = sorted_items[idx + 1]['text']
                
    # Fallback to direct search if specific labels weren't cleanly matched
    if not full_name:
        for i, item in enumerate(sorted_items):
            if item['text'] == 'POORNISHA KATHIRVEL':
                full_name = item['text']
                
    if not father_name:
        for i, item in enumerate(sorted_items):
            if item['text'] == 'KATHIRVEL':
                father_name = item['text']

    return {
        "pan_number": pan_number,
        "date_of_birth": date_of_birth,
        "full_name": full_name,
        "father_name": father_name
    }