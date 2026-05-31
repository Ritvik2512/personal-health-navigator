import google.generativeai as genai
from typing import List, Dict

MAX_MESSAGES = 20          # max no. of msgs to keep in full
SUMMARIZE_AFTER = 16       # no. of msgs to start summarizing after


def get_message_count(history: List[Dict]) -> int:
    return len(history)


async def maybe_summarize(history: List[Dict], model: genai.GenerativeModel) -> List[Dict]:
    """
    If conversation is getting long, summarize early messages into a compact context block.
    Keeps the last 8 messages verbatim for recency.
    Returns a (possibly trimmed) history.
    """
    if len(history) <= SUMMARIZE_AFTER:
        return history

    # keep last 8 msgs as is, summarize everything else
    to_summarize = history[:-8]
    recent = history[-8:]

    # text block for summarizer
    convo_text = "\n".join(
        f"{msg['role'].upper()}: {_extract_text(msg)}"
        for msg in to_summarize
    )

    summary_prompt = (
        f"Summarize this health conversation concisely. "
        f"Capture: the user's main symptoms/concerns, any medications mentioned, "
        f"key information provided, and the current state of the conversation. "
        f"Be factual and brief.\n\n{convo_text}"
    )

    try:
        resp = model.generate_content(summary_prompt)
        summary_text = resp.text

        summary_message = {
            "role": "user",
            "parts": [{"text": f"[CONVERSATION SUMMARY — earlier context]\n{summary_text}"}],
        }
        model_ack = {
            "role": "model",
            "parts": [{"text": "Understood. I have the context from our earlier conversation."}],
        }

        return [summary_message, model_ack] + recent

    except Exception:
        # in case summarization doesn't work, trim to last MAX_MESSAGES
        return history[-MAX_MESSAGES:]


def _extract_text(msg: Dict) -> str:
    """Pull plain text out of a Gemini history message."""
    parts = msg.get("parts", [])
    texts = []
    for part in parts:
        if isinstance(part, dict) and "text" in part:
            texts.append(part["text"])
        elif hasattr(part, "text"):
            texts.append(part.text)
    return " ".join(texts)[:500]  # cap per message for summarization input


def history_to_gemini_format(raw_history: List[Dict]) -> List[Dict]:
    """
    Ensure history is in the format Gemini's start_chat() expects:
    [{"role": "user"|"model", "parts": [{"text": "..."}]}]
    """
    formatted = []
    for msg in raw_history:
        role = msg.get("role", "user")
        parts = msg.get("parts", [])

        # convert parts to dicts
        normalized_parts = []
        for p in parts:
            if isinstance(p, str):
                normalized_parts.append({"text": p})
            elif isinstance(p, dict):
                normalized_parts.append(p)
            else:
                normalized_parts.append({"text": str(p)})

        if normalized_parts:
            formatted.append({"role": role, "parts": normalized_parts})

    return formatted
