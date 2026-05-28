import json
from pathlib import Path

from config_loader import BUILT_IN_SCORING_CONFIG, load_scoring_config


def test_load_scoring_config_uses_built_in_defaults_without_files(
    tmp_path: Path,
) -> None:
    assert load_scoring_config(tmp_path) == BUILT_IN_SCORING_CONFIG


def test_load_scoring_config_prefers_local_config(tmp_path: Path) -> None:
    example_config = {
        "starting_score": 10,
        "positive_keywords": ["example"],
    }
    local_config = {
        "starting_score": 70,
        "positive_keywords": ["local"],
    }

    (tmp_path / "config.example.json").write_text(
        json.dumps(example_config),
        encoding="utf-8",
    )
    (tmp_path / "config.local.json").write_text(
        json.dumps(local_config),
        encoding="utf-8",
    )

    config = load_scoring_config(tmp_path)

    assert config["starting_score"] == 70
    assert config["positive_keywords"] == ["local"]
