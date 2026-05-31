import os
import json
import google.generativeai as genai
from typing import List, Dict, Tuple

from prompts import SYSTEM_PROMPT
from tools import TOOL_DEFINITIONS, execute_tool
from memory import maybe_summarize, history_to_gemini_format


def init_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment")
    genai.configure(api_key=api_key)


def get_model() -> genai.GenerativeModel:
    return genai.GenerativeModel(
        model_name="gemini-3.1-flash-lite",
        system_instruction=SYSTEM_PROMPT,
        tools=TOOL_DEFINITIONS,
    )


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
    model = get_model()

    # memory management
    history = await maybe_summarize(raw_history, model)
    formatted_history = history_to_gemini_format(history)

    # start the chat after sharing histroy
    chat = model.start_chat(history=formatted_history)

    emergency = False
    emergency_reason = ""
    tool_calls_made = []
    final_reply = ""

    # agentic loop
    current_message = user_message
    max_iterations = 5  # prevents infinite loops

    for iteration in range(max_iterations):
        response = chat.send_message(current_message)
        candidate = response.candidates[0]

        # check finish reason
        finish_reason = candidate.finish_reason.name if candidate.finish_reason else "STOP"

        # collect tool calls from this response
        tool_calls_in_response = []
        text_parts = []

        for part in candidate.content.parts:
            if hasattr(part, "function_call") and part.function_call.name:
                tool_calls_in_response.append(part.function_call)
            elif hasattr(part, "text") and part.text:
                text_parts.append(part.text)

        # if no tool calls, we're done
        if not tool_calls_in_response:
            final_reply = "\n".join(text_parts) if text_parts else "I'm not sure how to respond to that."
            break

        # execute tool call
        tool_results = []
        for fc in tool_calls_in_response:
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}
            tool_calls_made.append(tool_name)

            result = await execute_tool(tool_name, tool_args)

            # check for emergency flag
            if tool_name == "flag_emergency" and result.get("emergency"):
                emergency = True
                emergency_reason = result.get("reason", "")

            tool_results.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=tool_name,
                        response={"result": json.dumps(result)},
                    )
                )
            )

        # send tool results back to the model
        current_message = tool_results

    # build updated history to return to the client
    # stored as dicts for JSON serialization
    updated_history = []
    for msg in chat.history:
        parts = []
        for part in msg.parts:
            if hasattr(part, "text") and part.text:
                parts.append({"text": part.text})
        if parts:
            updated_history.append({"role": msg.role, "parts": parts})

    return final_reply, updated_history, emergency, emergency_reason, tool_calls_made
