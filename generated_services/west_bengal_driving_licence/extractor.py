import re

def extract_document(ocr_items: list, full_text: str) -> dict:
    data = {
        "driving_licence_number": None,
        "name": None,
        "date_of_birth": None
    }
    
    # Extract Driving Licence Number
    dl_match = re.search(r'([A-Z]{2}\d{2}\d{11})', full_text)
    if dl_match:
        data["driving_licence_number"] = dl_match.group(1)
    else:
        # Fallback search for WB76 format
        for item in ocr_items:
            text = item["text"].replace(" ", "")
            if re.match(r'^[A-Z]{2}\d{2}\d{8,}$', text):
                data["driving_licence_number"] = text
                break

    # Extract Name using spatial layout (item right of 'Name:')
    name_idx = -1
    for i, item in enumerate(ocr_items):
        if "Name:" in item["text"]:
            name_idx = i
            break
    
    if name_idx != -1 and name_idx + 1 < len(ocr_items):
        # Look for the closest item to the right or immediately following
        candidate = ocr_items[name_idx + 1]
        data["name"] = candidate["text"].strip()
    
    if not data["name"]:
        # Fallback regex search
        match_name = re.search(r'Name:\s*([A-Z\s]+)', full_text)
        if match_name:
            data["name"] = match_name.group(1).strip()

    # Extract Date of Birth
    dob_match = re.search(r'Date of\s*Birth:\s*([0-9\-]+)', full_text)
    if dob_match:
        data["date_of_birth"] = dob_match.group(1).strip()
    else:
        # Fallback standard date format in document (dd-mm-yyyy)
        dates = re.findall(r'\d{2}-\d{2}-\d{4}', full_text)
        if len(dates) >= 2:
            # Usually second or third date is DOB depending on issue date
            data["date_of_birth"] = dates[1]

    return data