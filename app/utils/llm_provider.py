from langchain_core.language_models import BaseLLM
from app.config import settings

def get_llm(use_summary_model: bool = False) -> BaseLLM:
    """
    Returns the correct LangChain LLM based on ENV.

    Args:
        use_summary_model: True  → Llama 3.2 (summarization)
                           False → Mistral (extraction + prioritization)
    """

    model_name = settings.summary_model() if use_summary_model else settings.llm_model()

    if settings.is_local():
        from langchain_ollama import OllamaLLM
        return OllamaLLM(
            model=model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1
        )
    else:
        from langchain_huggingface import HuggingFaceEndpoint
        return HuggingFaceEndpoint(
            repo_id=model_name,
            huggingfacehub_api_token=settings.HF_TOKEN,
            temperature=0.1,
            max_new_tokens=1024
        )