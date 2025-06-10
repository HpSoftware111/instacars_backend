import re

def normalize_price_from_text(text: str) -> dict:
    text = text.lower()
    price_filter = {}

    # Match patterns like "under 10k", "below 5,000", "less than 3k"
    match = re.search(r"(under|below|less than)\s*\$?\s*([\d,]+)(k)?", text)
    if match:
        num = match.group(2).replace(',', '')
        if match.group(3):  # has 'k'
            price_filter["price_max"] = int(num) * 1000
        else:
            price_filter["price_max"] = int(num)
        return price_filter

    # Match patterns like "between 5k and 10k"
    match = re.search(r"between\s*\$?(\d+)(k)?\s*and\s*\$?(\d+)(k)?", text)
    if match:
        min_price = int(match.group(1)) * (1000 if match.group(2) else 1)
        max_price = int(match.group(3)) * (1000 if match.group(4) else 1)
        return {"price_min": min_price, "price_max": max_price}

    # Match vague ranges like "a couple of thousand"
    if "couple of thousand" in text:
        return {"price_max": 3000}
    elif "few thousand" in text:
        return {"price_max": 5000}
    elif "cheap" in text or "budget" in text:
        return {"price_max": 10000}

    return price_filter
