"""
backend/main.py — AgriConnect v2 (Agentic Architecture)
"""
import json, base64, traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

import database as db
from auth import hash_password, verify_password, create_token, get_current_user
from services.agent import run_agent, analyze_crop_image
from services.market import get_market_price
from services.weather import get_weather, build_weather_farming_tip
from services.translate import detect_and_translate, translate_to


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield


app = FastAPI(title="AgriConnect API v2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.onrender\.com|http://localhost:3000",  # Allow Render domains and localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _set_auth_cookie(response, token: str):
    response.set_cookie(
        "auth_token", token,
        httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7,
    )


# ── Health ──────────────────────────────────────────────────────────────────────

@app.get("/")
async def health():
    return {"status": "ok", "version": "2.0-agentic"}


# ── Auth ────────────────────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    name: str
    email: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/auth/register")
async def register(body: RegisterBody):
    existing = await db.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user = await db.create_user(body.name, body.email, hash_password(body.password))
    token = create_token(user["id"])
    response = JSONResponse({"user": {"id": user["id"], "name": user["name"], "email": user["email"]}})
    _set_auth_cookie(response, token)
    return response


@app.post("/auth/login")
async def login(body: LoginBody):
    user = await db.get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"])
    response = JSONResponse({"user": {"id": user["id"], "name": user["name"], "email": user["email"]}})
    _set_auth_cookie(response, token)
    return response


@app.post("/auth/logout")
async def logout():
    response = JSONResponse({"status": "logged out"})
    response.delete_cookie("auth_token")
    return response


@app.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "name": user["name"], "email": user["email"]}


# ── Conversations ───────────────────────────────────────────────────────────────

@app.get("/api/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    return await db.get_conversations(user["id"])


@app.post("/api/conversations")
async def new_conversation(user: dict = Depends(get_current_user)):
    return await db.create_conversation(user["id"], "New Chat")


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: int, user: dict = Depends(get_current_user)):
    if not await db.verify_conversation_owner(conv_id, user["id"]):
        raise HTTPException(status_code=403, detail="Not your conversation")
    await db.delete_conversation(conv_id, user["id"])
    return {"status": "deleted"}


@app.get("/api/conversations/{conv_id}/messages")
async def load_messages(conv_id: int, user: dict = Depends(get_current_user)):
    if not await db.verify_conversation_owner(conv_id, user["id"]):
        raise HTTPException(status_code=403, detail="Not your conversation")
    return await db.get_messages(conv_id)


# ── Weather ─────────────────────────────────────────────────────────────────────

@app.get("/api/weather")
async def weather_endpoint(city: str, user: dict = Depends(get_current_user)):
    data = get_weather(city)
    if not data:
        return JSONResponse({"error": "Weather unavailable"}, status_code=503)
    return {**data, "farming_tip": build_weather_farming_tip(data)}


# ── Market ──────────────────────────────────────────────────────────────────────

@app.get("/api/market")
async def market_endpoint(commodity: str, state: str, user: dict = Depends(get_current_user)):
    return get_market_price(commodity, state)


# ── Image Analysis ──────────────────────────────────────────────────────────────

@app.post("/api/analyze-image")
async def analyze_image(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    contents = await file.read()
    encoded = base64.b64encode(contents).decode("utf-8")
    result = await analyze_crop_image(encoded, file.content_type or "image/jpeg")
    return {"analysis": result}


# ── Chat (Agentic SSE Streaming) ────────────────────────────────────────────────

class ChatBody(BaseModel):
    query: str
    conversation_id: int | None = None


@app.post("/api/chat")
async def chat_endpoint(body: ChatBody, user: dict = Depends(get_current_user)):
    query = body.query.strip()
    if not query:
        return JSONResponse({"error": "No query provided"}, status_code=400)

    # Get or create conversation
    conv_id = body.conversation_id
    if conv_id:
        if not await db.verify_conversation_owner(conv_id, user["id"]):
            return JSONResponse({"error": "Invalid conversation"}, status_code=403)
    else:
        conv = await db.create_conversation(user["id"])
        conv_id = conv["id"]

    async def generate() -> AsyncGenerator[str, None]:
        response_parts: list[str] = []
        yield _sse("conv_id", {"conv_id": conv_id})

        try:
            # Detect language & translate query to English for the agent
            detected_lang, translated_query = detect_and_translate(query)

            # Load conversation history
            history = await db.get_history_text(conv_id)

            # ── Agentic loop ───────────────────────────────────────────────────
            async for token, market_data in run_agent(translated_query, history):
                if token.startswith("§status:"):
                    yield _sse("status", {"message": token[8:]})

                elif token.startswith("§market:") and market_data:
                    yield _sse("market_data", market_data)

                else:
                    response_parts.append(token)
                    yield _sse("token", {"text": token})

            # Translate full response back if user wrote in non-English
            raw = "".join(response_parts)
            final = translate_to(raw, detected_lang) if detected_lang != "en" else raw

            # If translated, send corrected full text
            if detected_lang != "en":
                yield _sse("translated", {"full_response": final})

            # Auto-title from first message
            conv_record = await db.get_conversation_by_id(conv_id)
            if conv_record and conv_record["title"] == "New Chat":
                short = query[:50] + ("…" if len(query) > 50 else "")
                await db.update_conversation_title(conv_id, short)

            # Persist to DB
            await db.save_message(conv_id, "user", query)
            await db.save_message(conv_id, "assistant", final)

            yield _sse("done", {"full_response": final, "conv_id": conv_id})

        except Exception:
            print(traceback.format_exc())
            yield _sse("error", {"message": "An error occurred. Please try again."})

    return StreamingResponse(generate(), media_type="text/event-stream")
