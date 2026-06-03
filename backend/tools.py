from medical_apis import fetch_drug_info, fetch_condition_info

# --- Tool definitions for Claude function calling ---

TOOL_DEFINITIONS = [
    {
        "name": "lookup_drug",
        "description": (
            "Look up real FDA data for a drug or medication. "
            "Use this whenever the user mentions a drug, medication, supplement, or pill by name. "
            "Returns side effects, warnings, interactions, usage info."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_name": {
                    "type": "string",
                    "description": "The name of the drug or medication (brand or generic)",
                }
            },
            "required": ["drug_name"],
        },
    },
    {
        "name": "search_condition",
        "description": (
            "Search for health information about a symptom, condition, or disease. "
            "Use this when the user describes symptoms or asks about a medical condition. "
            "Returns reliable MedlinePlus health information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symptom_or_condition": {
                    "type": "string",
                    "description": "The symptom, condition, or disease to look up",
                }
            },
            "required": ["symptom_or_condition"],
        },
    },
    {
        "name": "flag_emergency",
        "description": (
            "IMMEDIATELY call this when the user describes potentially life-threatening symptoms. "
            "Triggers an emergency alert in the UI. "
            "Use for: chest pain, breathing difficulty, stroke symptoms, severe allergic reactions, "
            "uncontrolled bleeding, suicidal thoughts, or any other emergency."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Brief description of why this is an emergency",
                }
            },
            "required": ["reason"],
        },
    },
]


# --- Tool execution ---

async def execute_tool(tool_name: str, tool_args: dict) -> dict:
    """Execute a tool call and return the result."""
    if tool_name == "lookup_drug":
        return await fetch_drug_info(tool_args.get("drug_name", ""))

    elif tool_name == "search_condition":
        return await fetch_condition_info(tool_args.get("symptom_or_condition", ""))

    elif tool_name == "flag_emergency":
        return {
            "emergency": True,
            "reason": tool_args.get("reason", "Potentially life-threatening symptoms detected"),
            "message": "CALL 112 (India) or 911 (US) or go to your nearest emergency room immediately.",
        }

    return {"error": f"Unknown tool: {tool_name}"}
