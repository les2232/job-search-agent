"""Load local scoring configuration."""

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_CONFIG_PATH = PROJECT_ROOT / "config.local.json"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config.example.json"

BUILT_IN_SCORING_CONFIG = {
    "starting_score": 50,
    "positive_keyword_points": 5,
    "concern_keyword_penalty": 8,
    "apply_threshold": 75,
    "maybe_threshold": 60,
    "positive_keywords": [
        "python",
        "sql",
        "api",
        "apis",
        "automation",
        "dashboard",
        "dashboards",
        "data",
        "git",
        "linux",
        "documentation",
        "troubleshooting",
        "junior",
        "entry-level",
        "remote",
        "hybrid",
    ],
    "concern_keywords": [
        "senior",
        "principal",
        "lead engineer",
        "8+ years",
        "10+ years",
        "sales",
        "commission",
        "on-call",
    ],
}


def load_scoring_config(config_dir: Path | None = None) -> dict[str, Any]:
    """Load local scoring config, example config, or built-in defaults."""
    base_dir = PROJECT_ROOT if config_dir is None else config_dir
    config_path = _find_config_path(base_dir)

    config = dict(BUILT_IN_SCORING_CONFIG)
    if config_path is None:
        return config

    with config_path.open(encoding="utf-8") as config_file:
        file_config = json.load(config_file)

    if isinstance(file_config, dict):
        config.update(file_config)

    return config


def _find_config_path(config_dir: Path) -> Path | None:
    local_config_path = config_dir / "config.local.json"
    if local_config_path.exists():
        return local_config_path

    example_config_path = config_dir / "config.example.json"
    if example_config_path.exists():
        return example_config_path

    return None
