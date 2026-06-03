from typing import List, Dict

MAX_MESSAGES = 20
SUMMARIZE_AFTER = 16


async def maybe_summarize(history: List[Dict], provider) -> List[Dict]:
    """
    If conversation is getting long, summarize early messages.
    Calls provider.summarize() — works for any model.
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

    except Exception:
        return history[-MAX_MESSAGES:]
