from __future__ import annotations

import logging
import json
import httpx
from typing import Any
from dotenv import load_dotenv
import os

from app.services.copilot_context_builder import build_patient_copilot_context, serialize_context_to_text

# Load .env file
load_dotenv()

logger = logging.getLogger("app.gemini_copilot")

GEMINI_MODELS = [
    "gemini-3.1-flash-lite",
]

def get_api_keys() -> list[str]:
    keys = []
    
    # Check GEMINI_API_KEY
    val = os.getenv("GEMINI_API_KEY")
    if val:
        keys.append(val)
        
    # Check GEMINI_API_KEY_1 to 5
    for i in range(1, 6):
        val = os.getenv(f"GEMINI_API_KEY_{i}")
        if val and val not in keys:
            keys.append(val)
            
    # Check GOOGLE_API_KEY
    val = os.getenv("GOOGLE_API_KEY")
    if val and val not in keys:
        keys.append(val)
        
    return keys

async def call_gemini_with_fallback_keys(payload: dict[str, Any], api_keys: list[str]) -> dict[str, Any]:
    last_error = None
    for model in GEMINI_MODELS:
        for idx, api_key in enumerate(api_keys):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = json.loads(text_out)
                        # Log success anonymously
                        logger.info(f"Gemini call succeeded with model={model} key_index={idx+1}")
                        return parsed
                    elif res.status_code == 429:
                        logger.warning(f"Quota exhausted: model={model} key_index={idx+1}")
                        last_error = f"429 quota on {model} key {idx+1}"
                    else:
                        error_detail = f"Status {res.status_code}"
                        logger.warning(f"Gemini model={model} key_index={idx+1} failed: {error_detail}")
                        last_error = error_detail
            except Exception as e:
                error_detail = str(e)
                logger.warning(f"Gemini model={model} key_index={idx+1} raised exception: {error_detail}")
                last_error = error_detail
                
    raise RuntimeError(f"All Gemini API keys and models exhausted. Last error: {last_error}")

async def ask_copilot_gemini(patient_id: str, message: str, conversation_history: list[dict[str, str]]) -> dict[str, Any]:
    # 1. Build patient context
    context = build_patient_copilot_context(patient_id)
    serialized_context = serialize_context_to_text(context)
    
    # 2. Build system instructions
    system_instruction = f"""You are a clinical discharge-planning copilot for a demo portfolio system.
Your user is a Discharge Planner / Care Coordinator, not a data scientist.
Answer in plain clinical operations language.
Always answer in English, even when the user's question is written in Persian, Finglish, or any other language. Preserve patient names and clinical labels exactly, but write the explanation, markdown answer, and follow-up questions in English.

Use the provided patient context only.
Do not invent facts outside the context.
Do not invent diagnoses beyond diag_1, diag_2, and diag_3.
Do not create medical orders.
Do not say "must", "order", "diagnose", or "treat".

Use review language:
- should be reviewed
- worth checking
- visible in discharge planning
- planning consideration
- follow-up readiness

Do not expose raw SHAP feature names (e.g. number_inpatient, prior_outpatient_visits) unless the user explicitly asks for technical model detail.
Instead, translate model explanation into plain language.
Example:
"The model placed extra weight on this patient's previous inpatient use" instead of "SHAP value for number_inpatient is positive".

If user asks a basic factual question (e.g., age, gender, doctor, room number, scheduled discharge, length of stay, destination, risk category), answer directly and briefly.
Example:
User: "how old is this patient?"
Answer: "This patient is **85 years old**. The original dataset age band is **[80-90)**."

If user asks for risk explanation, include:
- plain summary
- key evidence
- what to review before discharge

If user asks for unsupported operational actions like booking appointments, say this demo cannot perform actions yet, but can explain what should be reviewed.

Return markdown only for the answer body (answer_markdown).
Also return exactly 3 follow-up questions that are relevant to the user's last question and the patient context. Follow-up questions must be insight-focused, not action execution. Do not suggest booking appointments, ordering tests, or sending referrals.

Here is the current patient context:
{serialized_context}
"""

    # 3. Format contents and history
    gemini_contents = []
    for msg in conversation_history:
        role = "user" if msg["role"] == "user" else "model"
        gemini_contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
    gemini_contents.append({
        "role": "user",
        "parts": [{"text": message}]
    })

    payload = {
        "contents": gemini_contents,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "answer_markdown": {
                        "type": "STRING"
                    },
                    "follow_up_questions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        }
                    }
                },
                "required": ["answer_markdown", "follow_up_questions"]
            }
        }
    }

    # 4. Invoke Gemini with key rotation
    api_keys = get_api_keys()
    if not api_keys:
        raise RuntimeError("No Gemini API keys found. Set GEMINI_API_KEY or GOOGLE_API_KEY.")
        
    try:
        gemini_res = await call_gemini_with_fallback_keys(payload, api_keys)
        
        # Determine context flags used
        context_used = {
            "structured_patient_data": True,
            "risk_prediction": True,
            "shap_summary": len(context.get("shap_all", [])) > 0,
            "clinical_reviews": True,
            "diagnosis_timeline": len(context.get("chart", {}).get("box_3_clinical_review", {}).get("diagnosis_review", {}).get("diagnosis_timeline", [])) > 0,
            "lab_reports": context.get("lab_report") is not None
        }
        
        return {
            "patient_id": patient_id,
            "mode": "gemini_patient_chat",
            "answer_markdown": gemini_res["answer_markdown"],
            "follow_up_questions": gemini_res["follow_up_questions"][:3],
            "context_used": context_used,
            "safety_note": "This is a demo AI assistant using structured and simulated project data. It does not provide medical orders."
        }
    except Exception as e:
        logger.error(f"Gemini chat failed: {e}")
        # Graceful fallback error response
        return {
            "patient_id": patient_id,
            "mode": "gemini_patient_chat",
            "answer_markdown": "AI Copilot is temporarily unavailable. The rule-based discharge checklist is still available.",
            "follow_up_questions": [
                "Evaluate discharge readiness",
                "Why is this patient high risk?",
                "Review labs"
            ],
            "context_used": {
                "structured_patient_data": False,
                "risk_prediction": False,
                "shap_summary": False,
                "clinical_reviews": False,
                "diagnosis_timeline": False,
                "lab_reports": False
            },
            "safety_note": "This is a demo AI assistant using structured and simulated project data. It does not provide medical orders."
        }
