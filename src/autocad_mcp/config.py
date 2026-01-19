"""Configuration management for AutoCAD MCP Server."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

CADType = Literal["AUTOCAD", "GCAD", "ZWCAD"]


@dataclass
class ServerConfig:
    """MCP Server configuration."""

    name: str = "AutoCAD MCP Server"
    version: str = "1.0.0"


@dataclass
class CADConfig:
    """CAD application configuration."""

    type: CADType = "AUTOCAD"
    startup_wait_time: int = 20
    command_delay: float = 0.5


@dataclass
class OutputConfig:
    """Output file configuration."""

    directory: str = "./output"
    default_filename: str = "drawing.dwg"


@dataclass
class Config:
    """Main configuration container."""

    server: ServerConfig = field(default_factory=ServerConfig)
    cad: CADConfig = field(default_factory=CADConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create Config from dictionary."""
        server_data = data.get("server", {})
        cad_data = data.get("cad", {})
        output_data = data.get("output", {})

        return cls(
            server=ServerConfig(
                name=server_data.get("name", "AutoCAD MCP Server"),
                version=server_data.get("version", "1.0.0"),
            ),
            cad=CADConfig(
                type=cad_data.get("type", "AUTOCAD"),
                startup_wait_time=cad_data.get("startup_wait_time", 20),
                command_delay=cad_data.get("command_delay", 0.5),
            ),
            output=OutputConfig(
                directory=output_data.get("directory", "./output"),
                default_filename=output_data.get("default_filename", "drawing.dwg"),
            ),
        )


def load_config(config_path: Path | None = None) -> Config:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to config file. If None, uses default config.json location.

    Returns:
        Config object with loaded or default values.
    """
    if config_path is None:
        config_path = Path(__file__).parent / "config.json"

    if not config_path.exists():
        logger.info("Config file not found, using defaults: %s", config_path)
        return Config()

    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded configuration from %s", config_path)
        return Config.from_dict(data)
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON in config file: %s. Using defaults.", e)
        return Config()
    except Exception as e:
        logger.warning("Error loading config: %s. Using defaults.", e)
        return Config()
