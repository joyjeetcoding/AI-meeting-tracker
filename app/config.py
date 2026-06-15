from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    ENV: str = "local"

    # Ollama
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_LLM_MODEL: str = "mistral"
    OLLAMA_SUMMARY_MODEL: str = "llama3.2"

    # HuggingFace
    HF_TOKEN: str = ""
    HF_LLM_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.3"
    HF_SUMMARY_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"

    # Storage
    DATA_DIR: str = "./data"
    MEETINGS_DIR: str = "./data/meetings"
    TRANSCRIPTS_DIR: str = "./data/transcripts"
    OUTPUTS_DIR: str = "./data/outputs"
    SQLITE_DB_PATH: str = "./data/meetings.db"

    # MCP
    MCP_FILESYSTEM_ROOT: str = "./data"
    MCP_SQLITE_DB_PATH: str = "./data/meetings.db"

    class Config:
        env_file = ".env"
        extra = "ignore"
    
    def is_local(self) -> bool:
        return self.ENV == "local"
    
    def llm_model(self) -> str:
        """Returns the right model name based on environment."""
        return self.OLLAMA_LLM_MODEL if self.is_local() else self.HF_LLM_MODEL
    
    def summary_model(self) -> str:
        """Returns the right summary model name based on environment."""
        return self.OLLAMA_SUMMARY_MODEL if self.is_local() else self.HF_SUMMARY_MODEL
    
    def ensure_dirs(self):
        """Creates all data directories if they don't exist."""
        for d in [self.MEETINGS_DIR, self.TRANSCRIPTS_DIR, self.OUTPUTS_DIR]:
            Path(d).mkdir(parents=True, exist_ok=True)

settings = Settings()