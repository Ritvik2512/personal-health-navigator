import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

MAX_MESSAGES = 20
SUMMARIZE_AFTER = 16

PATIENT_CONTEXT_KEYS = ["allergies", "medications", "conditions", "age"]


def format_patient_context(context: Dict) -> Optional[str]:
    """
    Format patient context into a string to inject into every system prompt.
    Returns None if context is empty.
    """
    if not context or not any(context.values()):
        return None

    lines = ["## PATIENT CONTEXT — Always factor this into every response, never ignore it"]
    if context.get("allergies"):
        lines.append(f"- Allergies: {', '.join(context['allergies'])}")
    if context.get("medications"):
        lines.append(f"- Current medications: {', '.join(context['medications'])}")
    if context.get("conditions"):
        lines.append(f"- Known conditions: {', '.join(context['conditions'])}")
    if context.get("age"):
        lines.append(f"- Age: {context['age']}")

    return "\n".join(lines)


async def maybe_summarize(history: List[Dict], provider) -> List[Dict]:
    """
    Layer 2: sliding window with summarization.
    Patient context is never in history — it lives in the system prompt separately.
    """
    if len(history) <= SUMMARIZE_AFTER:
        return history

    to_summarize = history[:-8]
    recent = history[-8:]

    convo_text = "\n".join(
        f"{msg['role'].upper()}: {msg.get('content', '')[:500]}"
        for msg in to_summarize
    )

    try:
        summary_text = await provider.summarize(convo_text)
        summary_message = {
            "role": "user",
            "content": f"[CONVERSATION SUMMARY — earlier context]\n{summary_text}",
        }
        model_ack = {
            "role": "assistant",
            "content": "Understood. I have the context from our earlier conversation.",
        }
        return [summary_message, model_ack] + recent

    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}")
        return history[-MAX_MESSAGES:]


async def extract_context_from_message(message: str, current_context: Dict, provider) -> Dict:
    """
    After each user message, extract any new patient facts.
    Merges into existing context — never overwrites, only appends.
    """
    extraction_prompt = f"""Extract medical facts from this message if any are present.
Current known context: {current_context}
New message: "{message}"

Return a JSON object with only these keys (omit keys where no new info exists):
- allergies: list of strings
- medications: list of strings
- conditions: list of strings
- age: string

If no medical facts are present, return {{}}.
Return only valid JSON, nothing else."""

    try:
        result = await provider.complete(extraction_prompt)
        import json
        clean = result.strip().replace("```json", "").replace("```", "").strip()
        extracted = json.loads(clean)

        updated = dict(current_context)
        for key in PATIENT_CONTEXT_KEYS:
            if key in extracted and extracted[key]:
                if key == "age":
                    updated["age"] = extracted["age"]
                else:
                    existing = set(updated.get(key, []))
                    existing.update(extracted[key])
                    updated[key] = list(existing)

        return updated

    except Exception as e:
        logger.error(f"Context extraction failed: {str(e)}")
        return current_context
