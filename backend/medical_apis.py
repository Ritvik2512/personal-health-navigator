import httpx
import asyncio
from typing import Optional

OPENFDA_BASE = "https://api.fda.gov/drug"
MEDLINEPLUS_BASE = "https://connect.medlineplus.gov/service"


async def fetch_drug_info(drug_name: str) -> dict:
    """
    Fetch drug label information from OpenFDA.
    Returns side effects, warnings, interactions summary.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Search drug labels
            url = f"{OPENFDA_BASE}/label.json"
            params = {
                "search": f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
                "limit": 1,
            }
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            if not data.get("results"):
                # Try broader search
                params["search"] = drug_name
                resp = await client.get(url, params=params)
                data = resp.json()

            if not data.get("results"):
                return {"error": f"No FDA data found for '{drug_name}'"}

            result = data["results"][0]

            # Extract the most useful fields
            def first(field):
                val = result.get(field, [])
                return val[0] if val else None

            return {
                "drug_name": drug_name,
                "brand_name": result.get("openfda", {}).get("brand_name", [drug_name])[0] if result.get("openfda", {}).get("brand_name") else drug_name,
                "generic_name": result.get("openfda", {}).get("generic_name", ["Unknown"])[0] if result.get("openfda", {}).get("generic_name") else "Unknown",
                "purpose": first("purpose"),
                "indications_and_usage": first("indications_and_usage"),
                "warnings": first("warnings"),
                "adverse_reactions": first("adverse_reactions"),
                "drug_interactions": first("drug_interactions"),
                "dosage_and_administration": first("dosage_and_administration"),
                "contraindications": first("contraindications"),
            }

        except httpx.HTTPStatusError as e:
            return {"error": f"FDA API error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to fetch drug info: {str(e)}"}


async def fetch_condition_info(symptom_or_condition: str) -> dict:
    """
    Fetch health topic info from MedlinePlus Connect API.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            params = {
                "mainSearchCriteria.v.cs": "2.16.840.1.113883.6.90",  # ICD-10 code system
                "mainSearchCriteria.v.dn": symptom_or_condition,
                "informationRecipient.languageCode.c": "en",
                "knowledgeResponseType": "application/json",
            }
            resp = await client.get(MEDLINEPLUS_BASE, params=params)

            if resp.status_code != 200:
                # Fallback: search MedlinePlus health topics directly
                return await fetch_medlineplus_topic(symptom_or_condition, client)

            data = resp.json()
            entries = data.get("feed", {}).get("entry", [])

            if not entries:
                return await fetch_medlineplus_topic(symptom_or_condition, client)

            topics = []
            for entry in entries[:3]:
                topics.append({
                    "title": entry.get("title", {}).get("_value", ""),
                    "summary": entry.get("summary", {}).get("_value", ""),
                    "url": entry.get("link", [{}])[0].get("href", "") if entry.get("link") else "",
                })

            return {
                "query": symptom_or_condition,
                "topics": topics,
            }

        except Exception as e:
            return {"error": f"Failed to fetch condition info: {str(e)}"}


async def fetch_medlineplus_topic(query: str, client: httpx.AsyncClient) -> dict:
    """Fallback: search MedlinePlus health topics API."""
    try:
        url = "https://wsearch.nlm.nih.gov/ws/query"
        params = {
            "db": "healthTopics",
            "term": query,
            "retmax": 3,
        }
        resp = await client.get(url, params=params)
        # Return a simplified result even if we can't parse the XML
        return {
            "query": query,
            "topics": [
                {
                    "title": f"Search results for: {query}",
                    "summary": "Please visit MedlinePlus.gov for detailed, reliable health information on this topic.",
                    "url": f"https://medlineplus.gov/search.html?query={query.replace(' ', '+')}",
                }
            ],
        }
    except Exception as e:
        return {
            "query": query,
            "topics": [
                {
                    "title": query,
                    "summary": "Unable to fetch live data. Please consult MedlinePlus.gov or a healthcare professional.",
                    "url": "https://medlineplus.gov",
                }
            ],
        }
