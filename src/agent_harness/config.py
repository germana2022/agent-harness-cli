"""Typed Phase 1 configuration using Pydantic Settings."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import ConfigurationError

OutputFormat = Literal["text", "json"]

_SUPPORTED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Settings(BaseSettings):
    """Phase 1 configuration read from ``AGENT_HARNESS_*`` environment variables.

    ``read_only`` defaults to ``True`` and cannot be disabled in Phase 1.
    """

    model_config = SettingsConfigDict(
        env_prefix="AGENT_HARNESS_",
        env_file=None,
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"
    output_format: OutputFormat = "text"
    read_only: bool = True

    @model_validator(mode="after")
    def _validate_phase_1_constraints(self) -> "Settings":
        normalized = self.log_level.upper()
        if normalized not in _SUPPORTED_LOG_LEVELS:
            raise ConfigurationError(
                "invalid log_level: must be one of "
                f"{sorted(_SUPPORTED_LOG_LEVELS)}"
            )
        if not self.read_only:
            raise ConfigurationError("read_only cannot be disabled in Phase 1")
        return self
