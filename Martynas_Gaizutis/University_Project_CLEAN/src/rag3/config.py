from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional at runtime before deps are installed
    def load_dotenv() -> None:
        return None

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(slots=True)
class ElasticsearchConfig:
    host: str = "localhost"
    port: int = 9200
    index: str = "document"
    username: str = ""
    password: str = ""
    timeout: int = 120
    retry_on_timeout: bool = True
    max_retries: int = 5
    verify_certs: bool = False

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass(slots=True)
class GenerationConfig:
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_tokens: int = 350
    default_prompt: str = (
        "You are IO, Universal Retriever, a business-focused assistant for GravityX. "
        "Use only the provided internal context and never invent policies, metrics, dates, or commitments. "
        "If the context is insufficient, clearly state what is missing.\n\n"
        "Return your response in this structure:\n"
        "1) Executive Summary\n"
        "2) Evidence From Documents\n"
        "3) Recommended Next Steps\n"
        "4) Confidence (High/Medium/Low)\n\n"
        "Context:\n{context}\n\nQuestion:\n{question}"
    )


@dataclass(slots=True)
class ValidationConfig:
    enabled: bool = True
    max_tokens: int = 250


@dataclass(slots=True)
class RetrieverConfig:
    top_k: int = 5
    retries: int = 3
    delay_seconds: int = 3


@dataclass(slots=True)
class EmbedderConfig:
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    warm_up: bool = True


@dataclass(slots=True)
class IndexingConfig:
    txt_folder_path: str = "DATA/DATA_TXT"
    pdf_folder_path: str = "DATA/DATA_PDF"
    word_folder_path: str = "DATA/DATA_WORD"
    excel_folder_path: str = "DATA/DATA_EXCEL"


@dataclass(slots=True)
class AppConfig:
    api_key: str = ""
    elasticsearch: ElasticsearchConfig = field(default_factory=ElasticsearchConfig)
    generative_reader: GenerationConfig = field(default_factory=GenerationConfig)
    validation_agent: ValidationConfig = field(default_factory=ValidationConfig)
    retriever: RetrieverConfig = field(default_factory=RetrieverConfig)
    embedder: EmbedderConfig = field(default_factory=EmbedderConfig)
    index_documents: IndexingConfig = field(default_factory=IndexingConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            elasticsearch=ElasticsearchConfig(
                host=os.getenv("ELASTICSEARCH_HOST", "localhost"),
                port=_env_int("ELASTICSEARCH_PORT", 9200),
                index=os.getenv("ELASTICSEARCH_INDEX", "document"),
                username=os.getenv("ELASTICSEARCH_USERNAME", ""),
                password=os.getenv("ELASTICSEARCH_PASSWORD", ""),
                timeout=_env_int("ELASTICSEARCH_TIMEOUT", 120),
                retry_on_timeout=_env_bool("ELASTICSEARCH_RETRY_ON_TIMEOUT", True),
                max_retries=_env_int("ELASTICSEARCH_MAX_RETRIES", 5),
                verify_certs=_env_bool("ELASTICSEARCH_VERIFY_CERTS", False),
            ),
            generative_reader=GenerationConfig(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=_env_float("OPENAI_TEMPERATURE", 0.2),
                top_p=_env_float("OPENAI_TOP_P", 1.0),
                frequency_penalty=_env_float("OPENAI_FREQUENCY_PENALTY", 0.0),
                presence_penalty=_env_float("OPENAI_PRESENCE_PENALTY", 0.0),
                max_tokens=_env_int("OPENAI_MAX_TOKENS", 350),
            ),
            validation_agent=ValidationConfig(
                enabled=_env_bool("VALIDATION_ENABLED", True),
                max_tokens=_env_int("VALIDATION_MAX_TOKENS", 250),
            ),
            retriever=RetrieverConfig(
                top_k=_env_int("RETRIEVER_TOP_K", 5),
                retries=_env_int("RETRIEVER_RETRIES", 3),
                delay_seconds=_env_int("RETRIEVER_DELAY_SECONDS", 3),
            ),
            embedder=EmbedderConfig(
                model=os.getenv("EMBEDDER_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
                warm_up=_env_bool("EMBEDDER_WARM_UP", True),
            ),
            index_documents=IndexingConfig(
                txt_folder_path=os.getenv("TXT_FOLDER_PATH", "DATA/DATA_TXT"),
                pdf_folder_path=os.getenv("PDF_FOLDER_PATH", "DATA/DATA_PDF"),
                word_folder_path=os.getenv("WORD_FOLDER_PATH", "DATA/DATA_WORD"),
                excel_folder_path=os.getenv("EXCEL_FOLDER_PATH", "DATA/DATA_EXCEL"),
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_default_config() -> AppConfig:
    return AppConfig.from_env()
