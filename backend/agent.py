import json
import logging
from typing import List, Dict, Tuple

from prompts import SYSTEM_PROMPT
from tools import TOOL_DEFINITIONS, execute_tool
from memory import maybe_summarize, extract_context_from_message, format_patient_context
from llm_provider import get_provider

logger = logging.getLogger(__name__)


async def run_agent(
    user_message: str,
    raw_history: List[Dict],
    patient_context: Dict,
) -> Tuple[str, List[Dict], Dict, bool, str, List[str]]:
    """
    Main agent loop.

    Returns:
        - reply
        - updated_history
        - updated_patient_context
        - emergency
        - emergency_reason
        - tool_calls_made
    """
    provider = get_provider()

    # Layer 1: extract any new patient facts from this message
    patient_context = await extract_context_from_message(
        user_message, patient_context, provider
    )

    # Build system prompt with patient context injected
    context_block = format_patient_context(patient_context)
    system = SYSTEM_PROMPT
    if context_block:
        system = f"{SYSTEM_PROMPT}\n\n{context_block}"

    # Layer 2: sliding window summarization
    history = await maybe_summarize(raw_history, provider)
    messages = history + [{"role": "user", "content": user_message}]

    emergency = False
    emergency_reason = ""
    tool_calls_made = []
    final_reply = ""

    max_iterations = 5

    for _ in range(max_iterations):
        result = await provider.chat(
            messages=messages,
            system=system,
            tools=TOOL_DEFINITIONS,
        )

        if result["done"]:
            final_reply = result["text"] or "I'm not sure how to respond to that."
            messages.append({"role": "assistant", "content": final_reply})
            break

        tool_calls = result["tool_calls"]
        if not tool_calls:
            final_reply = result["text"] or "I'm not sure how to respond to that."
            break

        if "_raw_content" in result:
            messages.append({"role": "assistant", "content": result["_raw_content"]})
        else:
            messages.append({"role": "assistant", "content": result["text"] or ""})

        tool_results = []
        for tc in tool_calls:
            tool_calls_made.append(tc["name"])
            tool_result = await execute_tool(tc["name"], tc["args"])

            if tc["name"] == "flag_emergency" and tool_result.get("emergency"):
                emergency = True
                emergency_reason = tool_result.get("reason", "")

            if "_raw_content" in result:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": json.dumps(tool_result),
                })
            else:
                tool_results.append({
                    "role": "user",
                    "content": f"Tool result for {tc['name']}: {json.dumps(tool_result)}",
                })

        messages.append({
            "role": "user",
            "content": tool_results if "_raw_content" in result else tool_results[0]["content"]
        })

    # Clean history to return
    updated_history = []
    for msg in messages:
        if isinstance(msg.get("content"), str) and msg["content"]:
            updated_history.append({"role": msg["role"], "content": msg["content"]})

    return final_reply, updated_history, patient_context, emergency, emergency_reason, tool_calls_made
