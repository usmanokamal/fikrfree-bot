
"""app/api.py — FastAPI routes for FikrFree Assistant (chat, feedback, translate)."""

import asyncio
import bleach
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from app.bot import chat as bot_chat
from app.bot import translate_to_english, index
from pydantic import BaseModel
import json
import csv
import os

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: str

class FeedbackRequest(BaseModel):
    message_id: str
    user_message: str
    bot_response: str
    feedback: str  # "good" or "bad"
    session_id: str
    timestamp: str

@router.post("/chat/")
@router.post("/chat")
async def chat_post(request: ChatRequest, http_request: Request):
    """Server-sent events style streaming endpoint with disconnect handling."""
    clean_message = bleach.clean(request.message)
    request.message = clean_message

    async def generate():
        try:
            full_response = ""
            async for chunk in bot_chat(request.message):
                if await http_request.is_disconnected():
                    disconnect_data = {
                        "type": "error",
                        "message": "Client disconnected before completion",
                    }
                    yield f"data: {json.dumps(disconnect_data)}\n\n"
                    return

                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'type': 'content'})}\n\n"
                await asyncio.sleep(0.01)

            yield f"data: {json.dumps({'type': 'complete', 'full_response': full_response})}\n\n"

        except asyncio.CancelledError:
            yield f"data: {json.dumps({'type': 'stopped', 'message': 'Response stopped by user'})}\n\n"
            return
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'An error occurred: {str(e)}'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )

@router.get("/chat/")
async def chat_get(prompt: str, request: Request):
    """GET handler for streaming (legacy)."""
    clean_prompt = bleach.clean(prompt)

    async def generate():
        try:
            async for text in bot_chat(clean_prompt):
                if await request.is_disconnected():
                    return
                yield text.encode("utf-8")
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            yield b"Response stopped by user"
        except Exception as e:
            yield f"An error occurred: {str(e)}".encode("utf-8")

    return StreamingResponse(generate(), media_type="text/plain")

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Store user feedback in CSV file (feedback.csv in project root)."""
    try:
        csv_file_path = "feedback.csv"
        file_exists = os.path.isfile(csv_file_path)

        feedback_data = {
            "timestamp": request.timestamp,
            "message_id": request.message_id,
            "session_id": request.session_id,
            "user_message": bleach.clean(request.user_message),
            "bot_response": bleach.clean(request.bot_response),
            "feedback": request.feedback,
        }

        with open(csv_file_path, mode="a", newline="", encoding="utf-8") as file:
            fieldnames = [
                "timestamp",
                "message_id",
                "session_id",
                "user_message",
                "bot_response",
                "feedback",
            ]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(feedback_data)

        return {"status": "success", "message": "Feedback stored successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to store feedback: {str(e)}"}

# --- Translation helpers (English <-> Roman Urdu) ---

async def translate_with_openai(text: str, target_language: str) -> str:
    """Use OpenAI to translate text to/from Roman Urdu with better quality."""
    try:
        from llama_index.llms.openai import OpenAI
        translator_llm = OpenAI(model="gpt-4o-mini", temperature=0.1)

        if target_language == "roman_urdu":
            translation_prompt = f"""
            Translate the following English text to Roman Urdu (Urdu written using English alphabet).
            Use natural Pakistani Roman Urdu. Keep common technical terms in English.

            English: {text}

            Roman Urdu:
            """
        else:
            translation_prompt = f"""
            Translate the following Roman Urdu text to clear, natural English.

            Roman Urdu: {text}

            English:
            """

        response = await translator_llm.acomplete(translation_prompt)
        translated_text = response.text.strip()

        if translated_text.startswith('"') and translated_text.endswith('"'):
            translated_text = translated_text[1:-1]

        return translated_text or text
    except Exception as e:
        print(f"OpenAI translation error: {e}")
        return text

async def translate_text(text, target_language):
    try:
        return await translate_with_openai(text, target_language)
    except Exception as e:
        print(f"Translation error: {e}")
        return text

@router.post("/translate")
async def translate_message(request: dict):
    """Translate message between English and Roman Urdu using OpenAI."""
    try:
        text = request.get("text", "")
        target_language = request.get("target_language", "english")
        translated_text = await translate_text(text, target_language)
        return {
            "status": "success",
            "original_text": text,
            "translated_text": translated_text,
            "target_language": target_language,
        }
    except Exception as e:
        return {"status": "error", "message": f"Translation failed: {str(e)}"}
