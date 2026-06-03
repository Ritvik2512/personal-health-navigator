import json
from typing import List, Dict, Tuple

from prompts import SYSTEM_PROMPT
from tools import TOOL_DEFINITIONS, execute_tool
from memory import maybe_summarize
from llm_provider import get_provider


async def run_agent(
    user_message: str,
    raw_history: List[Dict],
) -> Tuple[str, List[Dict], bool, str, List[str]]:

    provider = get_provider()

    # Memory management
    history = await maybe_summarize(raw_history, provider)

    # Add current message
    messages = history + [{"role": "user", "content": user_message}]

    emergency = False
    emergency_reason = ""
    tool_calls_made = []
    final_reply = ""

    max_iterations = 5

    for _ in range(max_iterations):
        result = await provider.chat(
            messages=messages,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
        )

        if result["done"]:
            final_reply = result["text"] or "I'm not sure how to respond to that."
            break

        # Handle tool calls
        tool_calls = result["tool_calls"]
        if not tool_calls:
            final_reply = result["text"] or "I'm not sure how to respond to that."
            break

        # Append assistant response to messages (Claude needs raw content for tool loop)
        if "_raw_content" in result:
            messages.append({"role": "assistant", "content": result["_raw_content"]})
        else:
            messages.append({"role": "assistant", "content": result["text"] or ""})

        # Execute tools
        tool_results = []
        for tc in tool_calls:
            tool_calls_made.append(tc["name"])
            tool_result = await execute_tool(tc["name"], tc["args"])

            if tc["name"] == "flag_emergency" and tool_result.get("emergency"):
                emergency = True
                emergency_reason = tool_result.get("reason", "")

            # Claude format for tool results
            if "_raw_content" in result:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": json.dumps(tool_result),
                })
            else:
                # Gemini handles tool results differently — pass as text for now
                tool_results.append({
                    "role": "user",
                    "content": f"Tool result for {tc['name']}: {json.dumps(tool_result)}",
                })

        messages.append({"role": "user", "content": tool_results if "_raw_content" in result else tool_results[0]["content"]})

    # Build clean history
    updated_history = []
    for msg in messages:
        if isinstance(msg.get("content"), str) and msg["content"]:
            updated_history.append({"role": msg["role"], "content": msg["content"]})

    return final_reply, updated_history, emergency, emergency_reason, tool_calls_made
