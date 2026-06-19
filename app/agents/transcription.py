"""
Agent 1: Transcription Agent
------------------------------
Audio file → Whisper → transcript text → saved via Filesystem MCP

No LLM used here. Whisper is a separate ML model specifically
trained for speech-to-text. Much better than using a general LLM for audio.
"""
import whisper
from app.mcp.filesystem_mcp import save_file

# Load Whisper model once at module level
# It stays in memory — avoids reloading on every request
# "base" = fast, decent accuracy, ~140MB
# Upgrade to "small" or "medium" for better accuracy if needed
_model = None

def _get_model():
    global _model
    if _model is None:
        print("[TranscriptionAgent] Loading Whisper base model...")
        _model = whisper.load_model("base")
        print("[TranscriptionAgent] Model loaded")
    return _model

async def transcribe(audio_path: str, meeting_id: int) -> str:
    """
    Transcribes an audio file and saves the result via Filesystem MCP.

    Args:
        audio_path  : absolute path to the uploaded audio file
        meeting_id  : used to name the saved transcript file

    Returns:
        transcript  : the full transcript as a plain string
    """
    print(f"[TranscriptionAgent] Transcribing: {audio_path}")

    # Step 1: Run Whisper
    # fp16=False because most CPUs don't support float16
    # On a GPU you can set fp16=True for faster inference
    model = _get_model()
    result = model.transcribe(audio_path, fp16=False)
    transcript = result["text"].strip()

    print(f"[TranscriptionAgent] Transcribed {len(transcript)} characters")

    # Step 2: Save transcript via Filesystem MCP
    # This is where MCP comes in — instead of open() we use MCP
    saved_path = await save_file(
        relative_path=f"transcripts/meeting_{meeting_id}.txt",
        content=transcript
    )

    print(f"[TranscriptionAgent] Saved → {saved_path}")

    return transcript