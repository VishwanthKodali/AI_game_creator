from typing import Optional
from .properties import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL_FAST,
    GROQ_MODEL_POWER,
    BACKEND_URL,
    OUTPUT_DIR,
)


class _Settings:
    _groq_api_key: Optional[str] = GROQ_API_KEY
    _groq_base_url: Optional[str] = GROQ_BASE_URL
    _groq_model_fast: Optional[str] = GROQ_MODEL_FAST
    _groq_model_power: Optional[str] = GROQ_MODEL_POWER
    _backend_url: Optional[str] = BACKEND_URL
    _output_dir: str = OUTPUT_DIR
    
    def _require(self, value, value_name):
        if value is None:
            raise ValueError(f"{value_name} is not set. Please set it in config.yml or as an environment variable.")
        return value

    @property
    def groq_api_key(self) -> str:
        return self._require(self._groq_api_key, "GROQ_API_KEY")

    @property
    def groq_base_url(self) -> str:
        return self._require(self._groq_base_url, "GROQ_BASE_URL")

    @property
    def groq_model_fast(self) -> str:
        return self._require(self._groq_model_fast, "GROQ_MODEL_FAST")

    @property
    def groq_model_power(self) -> str:
        return self._require(self._groq_model_power, "GROQ_MODEL_POWER")

    @property
    def backend_url(self) -> str:
        return self._require(self._backend_url, "BACKEND_URL")

    @property
    def output_dir(self) -> str:
        return self._output_dir


Settings = _Settings()


def validate_settings() -> None:
    """Eagerly validate all required settings at startup."""
    _ = Settings.groq_api_key
    _ = Settings.groq_base_url
    _ = Settings.groq_model_fast
    _ = Settings.groq_model_power
    _ = Settings.backend_url
