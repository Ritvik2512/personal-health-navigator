import os
import json
import anthropic
from typing import List, Dict, Tuple

from prompts import SYSTEM_PROMPT
from tools import TOOL_DEFINITIONS, execute_tool
from memory import maybe_summarize, history_to_claude_format


def init_claude():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in environment")
    return anthropic.Anthropic(api_key=api_key)


async def run_agent(
    user_message: str,
    raw_history: List[Dict],
) -> Tuple[str, List[Dict], bool, str, List[str]]:
    """
    Main agent loop.

    Returns:
        - reply (str): final text response
        - updated_history (list): new history to pass back to client
        - emergency (bool): whether emergency was flagged
        - emergency_reason (str): why
        - tool_calls_made (list): names of tools that were called
    """
    client = init_claude()

    # Run memory management (summarize if too long)
    history = await maybe_summarize(raw_history, client)
    messages = history_to_claude_format(history)

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    emergency = False
    emergency_reason = ""
    tool_calls_made = []
    final_reply = ""

    # --- Agentic loop: keep going until no more tool calls ---
    max_iterations = 5

    for iteration in range(max_iterations):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # Append assistant response to messages
        messages.append({"role": "assistant", "content": response.content})

        # If Claude is done (no tool calls), extract final text
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    final_reply = block.text
            break

        # If Claude wants to use tools
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_args = block.input
                    tool_calls_made.append(tool_name)

                    result = await execute_tool(tool_name, tool_args)

                    # Check for emergency
                    if tool_name == "flag_emergency" and result.get("emergency"):
                        emergency = True
                        emergency_reason = result.get("reason", "")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            # Send tool results back
            messages.append({"role": "user", "content": tool_results})

    # Build updated history (strip system internals, keep text only)
    updated_history = []
    for msg in messages:
        if isinstance(msg["content"], str):
            updated_history.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})
        elif isinstance(msg["content"], list):
            texts = [b.text for b in msg["content"] if hasattr(b, "text") and b.text]
            if texts:
                updated_history.append({"role": msg["role"], "parts": [{"text": t} for t in texts]})

    return final_reply, updated_history, emergency, emergency_reason, tool_calls_made
