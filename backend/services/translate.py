"""
backend/services/translate.py — Language detection and translation.
"""
import requests


def detect_and_translate(text: str, target_lang: str = "en") -> tuple[str, str]:
    url = (
        f"https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=auto&tl={target_lang}&dt=t&q={requests.utils.quote(text)}"
    )
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        return data[2], "".join(item[0] for item in data[0])
    except Exception:
        return "en", text


def translate_to(text: str, target_lang: str) -> str:
    if target_lang == "en":
        return text
    url = (
        f"https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=en&tl={target_lang}&dt=t&q={requests.utils.quote(text)}"
    )
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        return "".join(item[0] for item in data[0])
    except Exception:
        return text
