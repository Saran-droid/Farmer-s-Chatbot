"""
backend/services/llm.py — Groq LLM with streaming support.
"""
from groq import Groq
from typing import AsyncGenerator
from config import GROQ_API_KEY

_client = Groq(api_key=GROQ_API_KEY)

CLASSIFY_MODEL = "llama-3.1-8b-instant"
ANSWER_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def classify_query(user_query: str, previous_context: str) -> str:
    """Classify query into farming category — returns structured text."""
    prompt = f"""Analyze the conversation and classify the latest query.

Conversation History:
{previous_context}

New User Query:
"{user_query}"

Classify into exactly ONE category:
- Market Price
- Pest Control
- Fertilizer Recommendation
- General Farming Information
- Pesticide and Related Explanation
- Irrelevant

Strictly follow this response format:
Follow-Up: <YES/NO>
Context: <Brief Summary>
Category: <Category>
Crop: <Crop Name or "None">
State: <State Name or "None">
"""
    try:
        response = _client.chat.completions.create(
            model=CLASSIFY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"


async def stream_farming_answer(user_query: str, previous_context: str) -> AsyncGenerator[str, None]:
    """Stream a farming answer token by token using Groq streaming."""
    prompt = f"""You are an expert farming assistant. Answer helpfully and in detail.

Conversation History:
{previous_context}

User Question:
"{user_query}"

Give a practical, detailed farming answer. Use bullet points and bold text where useful.
"""
    try:
        stream = _client.chat.completions.create(
            model=ANSWER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        yield f"\n\nError: {str(e)}"


async def analyze_crop_image(image_base64: str, mime_type: str = "image/jpeg") -> str:
    """Analyze a crop/leaf image for disease detection using Groq vision."""
    try:
        response = _client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "You are an expert agricultural pathologist. "
                                "Analyze this crop/plant image and:\n"
                                "1. Identify any visible disease, pest damage, or nutrient deficiency\n"
                                "2. Name the condition clearly\n"
                                "3. Describe the symptoms you see\n"
                                "4. Recommend treatment (pesticides, fungicides, or organic remedies)\n"
                                "5. Suggest preventive measures\n"
                                "If the plant looks healthy, say so.\n"
                                "Format with clear sections using bold headers."
                            ),
                        },
                    ],
                }
            ],
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not analyze image: {str(e)}"
