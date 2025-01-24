import os
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    cadmium_cloud_ws_url: str = os.getenv("CADMIUM_CLOUD_WS_URL", "https://cadmium.softwarescompound.in/")
    cadmium_cloud_api_url: str = os.getenv("CADMIUM_CLOUD_API_URL", "https://cadmium-cloud.example.com/api")
    local_llm_endpoint: str = os.getenv("LOCAL_LLM_ENDPOINT", "http://localhost:8001/llm")
    local_llm_model: str = os.getenv("LOCAL_LLM_MODEL", "qwen2.5-coder:latest")
    local_embedding_model: str = os.getenv("LOCAL_EMBEDDING_MODEL", "nomic-embed-text:latest")
    openai_api_key: str = os.getenv("OPENAI_API_KEY","")
    openai_model_name: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
    preferred_environment: str = os.getenv("PREFERRED_ENVIRONMENT", "local")
    preferred_rag_approach: str = os.getenv("PREFERRED_RAG_APPROACH", "naive_rag")
    websocket_url: str = os.getenv("WEBSOCKET_URL", "wss://cadmium.softwarescompound.in/ws")
    cd_id: str = os.getenv("CD_ID", "")
    cd_secret: str = os.getenv("CD_SECRET", "")
    api_base_url: str = os.getenv("API_BASE_URL", "https://cadmium.softwarescompound.in")
    response_streaming: bool = os.getenv("RESPONSE_STREAMING", True)
    
    model_config = SettingsConfigDict(env_file=".env")
    
    
    

settings = Settings()

WEBSOCKET_HEADERS = {
    "CD-ID": settings.cd_id,
    "CD-Secret": settings.cd_secret
}

API_BASE_URL = settings.api_base_url

WEBSOCKET_URL = settings.websocket_url