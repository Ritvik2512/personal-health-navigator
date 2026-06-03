import anthropic
from typing import List, Dict


MAX_MESSAGES = 20
SUMMARIZE_AFTER = 16


async def maybe_summarize(history: List[Dict], client: anthropic.Anthropic) -> List[Dict]:
    """
    If conversation is getting long, summarize early messages.
    Keeps the last 8 messages verbatim for recency.
    """
    if len(history) <= SUMMARIZE_AFTER:
        return history

    to_summarize = history[:-8]
    recent = history[-8:]

    convo_text = "\n".join(
        f"{msg['role'].upper()}: {_extract_text(msg)}"
        for msg in to_summarize
    )

    summary_prompt = (
        f"Summarize this health conversation concisely. "
        f"Capture: the user's main symptoms/concerns, any medications mentioned, "
        f"key information provided, and the current state of the conversation.\n\n{convo_text}"
    )

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": summary_prompt}],
        )
        summary_text = resp.content[0].text

        summary_message = {
            "role": "user",
            "parts": [{"text": f"[CONVERSATION SUMMARY — earlier context]\n{summary_text}"}],
        }
        model_ack = {
            "role": "assistant",
            "parts": [{"text": "Understood. I have the context from our earlier conversation."}],
        }

        return [summary_message, model_ack] + recent

    except Exception:
        return history[-MAX_MESSAGES:]


def _extract_text(msg: Dict) -> str:
    parts = msg.get("parts", [])
    texts = []
    for part in parts:
        if isinstance(part, dict) and "text" in part:
            texts.append(part["text"])
        elif hasattr(part, "text"):
            texts.append(part.text)
    return " ".join(texts)[:500]


def history_to_claude_format(raw_history: List[Dict]) -> List[Dict]:
    """
    Convert stored history to Claude's expected format:
    [{"role": "user"|"assistant", "content": "..."}]
    """
    formatted = []
    for msg in raw_history:
        role = msg.get("role", "user")
        # map "model" (Gemini legacy) to "assistant"
        if role == "model":
            role = "assistant"
        parts = msg.get("parts", [])
        text = " ".join(
            p["text"] for p in parts if isinstance(p, dict) and "text" in p
        )
        if text:
            formatted.append({"role": role, "content": text})
    return formatted
