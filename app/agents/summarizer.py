"""
Agent 2: Summarization Agent
------------------------------
Transcript text → LangChain prompt → LLM → summary → saved via Filesystem MCP

Uses Llama 3.2 locally (Ollama) or Qwen on HF Spaces (production).
This is the first agent that actually uses an LLM.
"""

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.llm_provider import get_llm
from app.mcp.filesystem_mcp import save_file


# ── Prompt ────────────────────────────────────────────────────
# Be very specific in prompts — vague prompts = vague output
# "under 200 words" prevents the LLM from rambling
SUMMARY_PROMPT = PromptTemplate(
    input_variables=["transcript"],
    template="""You are an expert meeting analyst.
    Read the meeting transcript below and write a concise summary.

    Your summary must include:
    - Main topics discussed
    - Key decisions made
    - Any important context or blockers mentioned

    Rules:
    - Maximum 200 words
    - Use clear, professional English
    - Do NOT include action items (those are extracted separately)
    - Write in paragraph form, not bullet points

    Meeting Transcript:
    {transcript}

    Summary:
    """
)


async def summarize(transcript: str, meeting_id: int) -> str:
    """
    Summarizes a meeting transcript using LLM.

    Args:
        transcript : full meeting text
        meeting_id : used to name the saved summary file

    Returns:
        summary : clean summary string
    """
    print(f"[SummarizationAgent] Summarizing meeting {meeting_id}...")

    # Step 1: Build LangChain chain
    # This is the LCEL (LangChain Expression Language) syntax
    # prompt | llm | parser means: format prompt → send to LLM → parse output
    llm = get_llm(use_summary_model=True)   # Llama 3.2 / Qwen
    chain = SUMMARY_PROMPT | llm | StrOutputParser()

    # Step 2: Run the chain
    # ainvoke = async invoke (non-blocking, FastAPI friendly)
    summary = await chain.ainvoke({"transcript": transcript})
    summary = summary.strip()

    print(f"[SummarizationAgent] Summary generated ({len(summary)} chars)")

    # Step 3: Save via Filesystem MCP
    saved_path = await save_file(
        relative_path=f"outputs/summary_{meeting_id}.txt",
        content=summary,
    )
    print(f"[SummarizationAgent] Saved → {saved_path}")

    return summary