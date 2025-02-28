import requests
def detect_language_and_translate(text, target_lang="en"):
    """
    Detects the language of the input text and translates it to the target language (default: English).

    :param text: The text to translate.
    :param target_lang: The target language for translation (default is English).
    :return: A tuple (detected_language, translated_text)
    """
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={requests.utils.quote(text)}"

    response = requests.get(url)
    if response.status_code == 200:
        try:
            json_data = response.json()
            detected_language = json_data[2]  # The detected language code
            translated_text = ''.join([item[0] for item in json_data[0]])  # Extract translated text
            return detected_language, translated_text
        except Exception as e:
            return None, f"Error parsing response: {e}"
    else:
        return None, "Error in translation request"

def translate_back(text, source_lang):
    """
    Translates the given text back to the original detected language.

    :param text: The text to translate back.
    :param source_lang: The original detected language.
    :return: Translated text in the original language.
    """
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={source_lang}&dt=t&q={requests.utils.quote(text)}"

    response = requests.get(url)
    if response.status_code == 200:
        try:
            json_data = response.json()
            translated_text = ''.join([item[0] for item in json_data[0]])
            return translated_text
        except Exception as e:
            return f"Error parsing response: {e}"
    else:
        return "Error in translation request"