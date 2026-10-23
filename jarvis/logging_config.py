"""Logging configuration that avoids logging prompts, credentials, or biometric data."""
import logging
from .config import Settings


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
