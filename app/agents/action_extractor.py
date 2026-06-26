"""
Agent 3+4: Action Extractor + Task Prioritizer
------------------------------------------------
Transcript + Summary → Mistral → structured JSON → saved via Filesystem MCP

Why combined into one agent?
  - Fewer LLM calls = faster response on free tier
  - Prioritization needs context from the full transcript anyway
  - Cleaner output: extract AND prioritize in one shot

Output per action item:
{
  "task": "Send proposal to client",
  "owner": "Joy",
  "priority": "High",
  "deadline": "Friday"
}
"""

import json
import re
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.llm_provider import get_llm
from app.mcp.filesystem_mcp import save_json


# ── Prompt ────────────────────────────────────────────────────
# Key design decisions:
# 1. Provide the summary AND transcript — summary gives context,
#    transcript gives specific names, dates, details
# 2. Explicit JSON format with an example — LLMs follow examples
#    better than abstract descriptions
# 3. "ONLY a valid JSON array" — firm instruction reduces preamble
# 4. Priority guidelines with concrete rules — removes ambiguity
EXTRACTION_PROMPT = PromptTemplate(
    input_variables=["transcript", "summary"],
    template="""You are an expert at extracting action items from meeting notes.

Extract ALL action items from the transcript below.
For each action item determine:
- task     : what needs to be done (specific and actionable)
- owner    : who is responsible (person name, or null if unassigned)
- priority : High, Medium, or Low
- deadline : when it is due (exact date or relative like "Friday", or null)

Priority rules:
  High   → urgent, blocking others, or has a near deadline
  Medium → important but not blocking, has a soft deadline
  Low    → nice to have, no clear deadline, informational follow-up

IMPORTANT:
- Respond with ONLY a valid JSON array. No explanation, no markdown.
- If no action items exist return an empty array: []

Example output:
[
  {{"task": "Send proposal to client", "owner": "Alice", "priority": "High", "deadline": "Thursday"}},
  {{"task": "Review Q3 budget", "owner": "Bob", "priority": "Medium", "deadline": "next week"}},
  {{"task": "Share meeting notes", "owner": null, "priority": "Low", "deadline": null}}
]

Meeting Summary:
{summary}

Full Transcript:
{transcript}

JSON Output:"""
)


# ── Parser ────────────────────────────────────────────────────

def _parse_action_items(raw: str) -> list[dict]:
    """
    Safely parses LLM output into a list of action item dicts.

    LLMs sometimes add markdown fences (```json) or preamble text
    before the JSON. This function handles all those cases.
    """

    # Remove markdown code fences if present
    # e.g. ```json [...] ``` → [...]
    clean = re.sub(r"```(?:json)?", "", raw).strip()

    # Find the JSON array anywhere in the output
    # re.DOTALL makes . match newlines too
    match = re.search(r"\[.*\]", clean, re.DOTALL)
    if not match:
        print(f"[ActionExtractor] No JSON array found in: {raw[:200]}")
        return []

    try:
        items = json.loads(match.group())
    except json.JSONDecodeError as e:
        print(f"[ActionExtractor] JSON parse error: {e}")
        return []

    # Normalize each item — validate priority, fill missing fields
    normalized = []
    for item in items:
        priority = item.get("priority", "Medium")
        if priority not in ["High", "Medium", "Low"]:
            priority = "Medium"

        normalized.append({
            "task": str(item.get("task", "")).strip(),
            "owner": item.get("owner"),        # keep null if unassigned
            "priority": priority,
            "deadline": item.get("deadline"),  # keep null if no deadline
        })

    return normalized


# ── Main function ─────────────────────────────────────────────

async def extract_and_prioritize(
    transcript: str,
    summary: str,
    meeting_id: int,
) -> list[dict]:
    """
    Extracts and prioritizes action items from meeting content.

    Args:
        transcript : full meeting text
        summary    : output from Agent 2 (gives better context)
        meeting_id : used to name the saved output file

    Returns:
        list of action item dicts with task, owner, priority, deadline
    """
    print(f"[ActionExtractor] Extracting actions for meeting {meeting_id}...")

    # Step 1: Build and run chain
    llm = get_llm(use_summary_model=False)  # Mistral
    chain = EXTRACTION_PROMPT | llm | StrOutputParser()

    raw_output = await chain.ainvoke({
        "transcript": transcript,
        "summary": summary,
    })

    # Step 2: Parse LLM output into clean list of dicts
    action_items = _parse_action_items(raw_output)
    print(f"[ActionExtractor] Found {len(action_items)} action items")

    # Step 3: Save JSON output via Filesystem MCP
    await save_json(
        relative_path=f"outputs/actions_{meeting_id}.json",
        data={
            "meeting_id": meeting_id,
            "action_items": action_items,
            "total": len(action_items),
        }
    )

    return action_items