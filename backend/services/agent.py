"""
backend/services/agent.py — Agentic loop using Groq tool calling.

The agent receives a user query and iterates:
  1. LLM decides which tool(s) to call (or answers directly).
  2. Tools are executed and results appended to the conversation.
  3. Repeat until LLM produces a final text answer.
  4. Final answer is streamed token-by-token.
"""
import json
from typing import AsyncGenerator
from groq import Groq
from config import GROQ_API_KEY

from services.market import get_market_price
from services.agri_data import fetch_fertilizer_recommendations, fetch_pesticide_recommendations
from services.weather import get_weather, build_weather_farming_tip

_client = Groq(api_key=GROQ_API_KEY)
AGENT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# ─── Tool Definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_market_price",
            "description": (
                "Fetch current/recent mandi market prices for a crop in an Indian state. "
                "Call this multiple times to compare prices across crops or states. "
                "Use this for queries like 'most expensive vegetable in Kerala', "
                "'price of wheat in Punjab', or 'compare tomato prices'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "Crop or commodity name (e.g. 'Tomato', 'Cotton', 'Rice')"},
                    "state": {"type": "string", "description": "Indian state name (e.g. 'Kerala', 'Punjab', 'Gujarat')"},
                },
                "required": ["crop", "state"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fertilizer_info",
            "description": "Get fertilizer recommendations for a specific crop from agronomic database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "Crop name"},
                },
                "required": ["crop"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pesticide_info",
            "description": "Get pesticide and pest control recommendations for a specific crop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "Crop name"},
                },
                "required": ["crop"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather conditions and farming advice for a city/district in India.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City or district name in India"},
                },
                "required": ["city"],
            },
        },
    },
]


# ─── Tool Executor ─────────────────────────────────────────────────────────────
def _execute_tool(name: str, args: dict) -> tuple[str, dict | None]:
    """Execute a tool and return (text_result, optional_market_data)."""
    market_payload = None
    try:
        if name == "get_market_price":
            data = get_market_price(args["crop"], args["state"])
            market_payload = {"crop": args["crop"], "state": args["state"], "records": data["records"]}
            return data["text"], market_payload

        elif name == "get_fertilizer_info":
            result = fetch_fertilizer_recommendations(args["crop"])
            return result or f"No specific fertilizer data found for {args['crop']}. Will use general knowledge.", None

        elif name == "get_pesticide_info":
            result = fetch_pesticide_recommendations(args["crop"])
            return result or f"No specific pesticide data found for {args['crop']}. Will use general knowledge.", None

        elif name == "get_weather":
            data = get_weather(args["city"])
            if not data:
                return f"Weather data unavailable for {args['city']}.", None
            tip = build_weather_farming_tip(data)
            summary = (
                f"Weather in {data.get('city', args['city'])}: "
                f"{data.get('description', 'N/A')}, "
                f"{data.get('temp', 'N/A')}°C, "
                f"Humidity {data.get('humidity', 'N/A')}%, "
                f"Wind {data.get('wind_speed', 'N/A')} m/s. "
                f"Farming tip: {tip}"
            )
            return summary, None

    except Exception as e:
        return f"Tool error: {str(e)}", None

    return "Unknown tool.", None


# ─── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are AgriConnect AI — an expert AI assistant for Indian farmers.

You have access to real tools to answer questions that need data:
- Market prices for crops across Indian states
- Fertilizer and pesticide recommendations from agronomic databases
- Live weather conditions for any city

**ALWAYS use tools when the query involves:**
- Comparing prices ("most expensive", "cheapest", "price of X in Y")
- Specific market data (call get_market_price for each crop/state needed)
- Weather-based advice (call get_weather first)
- Fertilizer or pest queries (check the database first)

**For comparison queries** (e.g. "most expensive vegetable in Kerala"):
- Call get_market_price for each relevant crop separately
- Summarize and compare the results in your final answer

**Answer in the same language the user wrote in.**
Be practical, specific, and helpful. Use bullet points and bold for clarity."""


# ─── Main Agentic Generator ────────────────────────────────────────────────────
async def run_agent(
    user_query: str,
    history: str,
) -> AsyncGenerator[tuple[str, dict | None], None]:
    """
    Agentic loop that yields (token_or_status, market_data_or_None).
    Caller inspects the first element:
      - Starts with "§status:" → yield as status SSE
      - Starts with "§market:" → yield as market_data SSE (data in second element)
      - Otherwise → yield as token SSE
    """
    messages = []
    if history.strip():
        messages.append({"role": "user", "content": f"[Previous conversation]\n{history}"})
        messages.append({"role": "assistant", "content": "Understood. I'll use this context."})
    messages.append({"role": "user", "content": user_query})

    market_payloads: list[dict] = []
    max_rounds = 5  # Prevent infinite loops

    for round_num in range(max_rounds):
        yield ("§status:Thinking…", None)

        # ── Ask the LLM (non-streaming for tool-call round) ──────────────────
        response = _client.chat.completions.create(
            model=AGENT_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.4,
            max_tokens=4096,
        )

        msg = response.choices[0].message

        # ── No tool calls → produce final answer ─────────────────────────────
        if not msg.tool_calls:
            # Emit any collected market chart payloads first
            for payload in market_payloads:
                yield ("§market:", payload)

            if market_payloads:
                # Tool calls happened in previous rounds → stream a synthesis
                yield ("§status:Analyzing results…", None)
                stream = _client.chat.completions.create(
                    model=AGENT_MODEL,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                    temperature=0.6,
                    max_tokens=2048,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield (delta, None)
            else:
                # No tool calls at all — LLM answered directly in msg.content
                if msg.content:
                    yield (msg.content, None)
            return

        # ── Tool calls → execute and append results ───────────────────────────
        tool_calls = msg.tool_calls
        # Append assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            yield (f"§status:Calling {fn_name.replace('_', ' ')}…", None)
            result_text, market_data = _execute_tool(fn_name, fn_args)

            if market_data:
                market_payloads.append(market_data)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_text,
            })

    # Safety fallback if max rounds hit
    yield ("I gathered the information but reached the processing limit. Please try a more specific question.", None)


# ─── Image Analysis ────────────────────────────────────────────────────────────
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
                            "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
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
