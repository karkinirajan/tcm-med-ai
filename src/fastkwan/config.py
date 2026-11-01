"""Settings from environment variables (or a local ``.env``). Nothing is required to *import* the
package or to start the server: an endpoint whose services are not configured answers 503 and
names the missing variables (the old module raised at import unless four API keys were set)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class NotConfigured(Exception):
    def __init__(self, names):
        self.names = [name.upper() for name in names]
        super().__init__("Missing configuration: " + ", ".join(self.names))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI: symptom extraction (NER) and the embeddings used for the vector search
    openai_api_key: str = ""
    openai_model: str = ""  # no default: set a chat model your account can use
    embedding_model: str = ""  # empty: LangChain's default, which is what the index was built with
    openai_timeout: float = 60.0

    # Pinecone: where the syndromes and prescriptions are indexed
    pinecone_api_key: str = ""
    pinecone_index_name: str = "evidgpt"
    syndromes_namespace: str = "syndromes"
    prescriptions_namespace: str = "fangji"
    syndrome_candidates: int = 30
    prescription_candidates: int = 50

    # Cohere: reranking of the candidates
    cohere_api_key: str = ""
    cohere_rerank_model: str = ""  # no default: set a rerank model your account can use
    rerank_top_n: int = 5

    # MongoDB Atlas: disease names and their lifestyle advice (needs an Atlas Search index)
    mongodb_uri: str = ""
    mongodb_database: str = "cmedai"
    mongodb_collection: str = "教科书"
    mongodb_search_index: str = "diseaseName"

    # The service
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = ""  # comma-separated; no CORS headers at all when empty
    api_key: str = ""  # when set, every endpoint except / and /health needs it in X-API-Key

    @property
    def cors_origin_list(self):
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def require(self, *names):
        missing = [name for name in names if not getattr(self, name)]
        if missing:
            raise NotConfigured(missing)
