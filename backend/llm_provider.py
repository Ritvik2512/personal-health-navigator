import os
import json
import anthropic
import google.generativeai as genai
from typing import List, Dict, Any


class GeminiProvider:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    def format_tools(self, neutral_tools: List[Dict]) -> list:
        declarations = []
        for t in neutral_tools:
            props = {}
            for name, meta in t["parameters"].items():
                props[name] = genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description=meta["description"],
                )
            declarations.append(
                genai.protos.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties=props,
                        required=t.get("required", []),
                    ),
                )
            )
        return [genai.protos.Tool(function_declarations=declarations)]

    def format_history(self, history: List[Dict]) -> List[Dict]:
        formatted = []
        for msg in history:
            role = "model" if msg["role"] == "assistant" else msg["role"]
            text = msg.get("content", "")
            if text:
                formatted.append({"role": role, "parts": [text]})
        return formatted

    async def complete(self, prompt: str) -> str:
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(prompt)
        return resp.text

    async def summarize(self, convo_text: str) -> str:
        return await self.complete(
            "Summarize this health conversation concisely. "
            "Capture: symptoms, medications, key info, current state.\n\n"
            + convo_text
        )

    async def chat(self, messages: List[Dict], system: str, tools: List[Dict]) -> Dict:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=system,
            tools=self.format_tools(tools),
        )
        history = self.format_history(messages[:-1])
        chat = model.start_chat(history=history)
        response = chat.send_message(messages[-1]["content"])
        candidate = response.candidates[0]

        tool_calls = []
        text = None
        for part in candidate.content.parts:
            if hasattr(part, "function_call") and part.function_call.name:
                tool_calls.append({
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args),
                    "id": part.function_call.name,
                })
            elif hasattr(part, "text") and part.text:
                text = part.text

        return {
            "text": text,
            "tool_calls": tool_calls,
            "done": len(tool_calls) == 0,
        }


class ClaudeProvider:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def format_tools(self, neutral_tools: List[Dict]) -> list:
        formatted = []
        for t in neutral_tools:
            props = {}
            for name, meta in t["parameters"].items():
                props[name] = {"type": "string", "description": meta["description"]}
            formatted.append({
                "name": t["name"],
                "description": t["description"],
                "input_schema": {
                    "type": "object",
                    "properties": props,
                    "required": t.get("required", []),
                },
            })
        return formatted

    def format_history(self, history: List[Dict]) -> List[Dict]:
        formatted = []
        for msg in history:
            role = "assistant" if msg["role"] == "model" else msg["role"]
            text = msg.get("content", "")
            if text:
                formatted.append({"role": role, "content": text})
        return formatted

    async def complete(self, prompt: str) -> str:
        resp = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    async def summarize(self, convo_text: str) -> str:
        return await self.complete(
            "Summarize this health conversation concisely. "
            "Capture: symptoms, medications, key info, current state.\n\n"
            + convo_text
        )

    async def chat(self, messages: List[Dict], system: str, tools: List[Dict]) -> Dict:
        formatted = self.format_history(messages)
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            tools=self.format_tools(tools),
            messages=formatted,
        )

        tool_calls = []
        text = None
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append({
                    "name": block.name,
                    "args": block.input,
                    "id": block.id,
                })
            elif hasattr(block, "text"):
                text = block.text

        return {
            "text": text,
            "tool_calls": tool_calls,
            "done": response.stop_reason == "end_turn",
            "_raw_content": response.content,
            "_usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }      


def get_provider():
    """Switch provider here. Only this function needs to change."""
    return ClaudeProvider()
    # return GeminiProvider()
