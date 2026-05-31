import google.generativeai as genai
from medical_apis import fetch_drug_info, fetch_condition_info

# tool definitions for Gemini

TOOL_DEFINITIONS = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="lookup_drug",
                description=(
                    "Look up real FDA data for a drug or medication. "
                    "Use this whenever the user mentions a drug, medication, supplement, or pill by name. "
                    "Returns side effects, warnings, interactions, usage info."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "drug_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The name of the drug or medication (brand or generic)",
                        )
                    },
                    required=["drug_name"],
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="search_condition",
                description=(
                    "Search for health information about a symptom, condition, or disease. "
                    "Use this when the user describes symptoms or asks about a medical condition. "
                    "Returns reliable MedlinePlus health information."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "symptom_or_condition": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The symptom, condition, or disease to look up",
                        )
                    },
                    required=["symptom_or_condition"],
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="flag_emergency",
                description=(
                    "IMMEDIATELY call this when the user describes potentially life-threatening symptoms. "
                    "Triggers an emergency alert in the UI. "
                    "Use for: chest pain, breathing difficulty, stroke symptoms, severe allergic reactions, "
                    "uncontrolled bleeding, suicidal thoughts, or any other emergency."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "reason": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Brief description of why this is an emergency",
                        )
                    },
                    required=["reason"],
                ),
            ),
        ]
    )
]


# tool execution

async def execute_tool(tool_name: str, tool_args: dict) -> dict:
    """Execute a tool call and return the result."""
    if tool_name == "lookup_drug":
        return await fetch_drug_info(tool_args.get("drug_name", ""))

    elif tool_name == "search_condition":
        return await fetch_condition_info(tool_args.get("symptom_or_condition", ""))

    elif tool_name == "flag_emergency":
        # handled in the response, just returning signal
        return {
            "emergency": True,
            "reason": tool_args.get("reason", "Potentially life-threatening symptoms detected"),
            "message": "CALL 112 (India) or 911 (US) or go to your nearest emergency room immediately.",
        }

    return {"error": f"Unknown tool: {tool_name}"}
