"""Tests for the promotion marker loader."""

import json
import logging
from pathlib import Path

import pytest

from pipeline.promotion import PromotedModel, load_promoted_model


def _make_artifact_layout(marker_dir: Path, run_id: str, config_name: str) -> Path:
    artifact_dir = marker_dir / "training-sweeps" / run_id / "configs" / config_name / "models"
    artifact_dir.mkdir(parents=True)
    return artifact_dir


def test_load_promoted_model_uses_marker_when_present(tmp_path) -> None:
    run_id = "20260507T010101Z_test-run"
    config_name = "full_c003_e100"
    artifact_dir = _make_artifact_layout(tmp_path, run_id, config_name)
    marker_path = tmp_path / "promoted_model.json"
    marker_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "config_name": config_name,
                "promoted_at": "2026-05-07T01:02:03+00:00",
                "schema_version": 1,
            }
        ),
        encoding="utf-8",
    )

    promoted = load_promoted_model(marker_path=marker_path)

    assert isinstance(promoted, PromotedModel)
    assert promoted.run_id == run_id
    assert promoted.config_name == config_name
    assert promoted.artifact_dir == artifact_dir
    assert promoted.promoted_at == "2026-05-07T01:02:03+00:00"
    assert promoted.source == "marker"


def test_load_promoted_model_falls_back_to_env_when_marker_missing(monkeypatch, tmp_path, caplog) -> None:
    env_artifact_dir = tmp_path / "env_models"
    env_artifact_dir.mkdir()
    monkeypatch.setattr("pipeline.promotion.config.MODEL_ARTIFACT_DIR", str(env_artifact_dir))
    monkeypatch.setattr("pipeline.promotion.config.MODEL_RUN_ID", "env-run-id")
    monkeypatch.setattr("pipeline.promotion.config.MODEL_CONFIG_NAME", "env-config")

    missing_marker_path = tmp_path / "does_not_exist.json"

    with caplog.at_level(logging.WARNING, logger="pipeline.promotion"):
        promoted = load_promoted_model(marker_path=missing_marker_path)

    assert promoted.source == "env"
    assert promoted.run_id == "env-run-id"
    assert promoted.config_name == "env-config"
    assert promoted.artifact_dir == env_artifact_dir
    assert any("No promotion marker" in record.message for record in caplog.records)


def test_load_promoted_model_falls_back_when_marker_malformed(monkeypatch, tmp_path, caplog) -> None:
    env_artifact_dir = tmp_path / "env_models"
    env_artifact_dir.mkdir()
    monkeypatch.setattr("pipeline.promotion.config.MODEL_ARTIFACT_DIR", str(env_artifact_dir))
    monkeypatch.setattr("pipeline.promotion.config.MODEL_RUN_ID", "env-run-id")
    monkeypatch.setattr("pipeline.promotion.config.MODEL_CONFIG_NAME", "env-config")

    marker_path = tmp_path / "promoted_model.json"
    marker_path.write_text("{not valid json", encoding="utf-8")

    with caplog.at_level(logging.ERROR, logger="pipeline.promotion"):
        promoted = load_promoted_model(marker_path=marker_path)

    assert promoted.source == "env"
    assert promoted.artifact_dir == env_artifact_dir
    assert any("malformed" in record.message for record in caplog.records)


def test_load_promoted_model_raises_when_artifact_dir_missing(tmp_path) -> None:
    run_id = "ghost-run"
    config_name = "ghost-config"
    marker_path = tmp_path / "promoted_model.json"
    marker_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "config_name": config_name,
                "promoted_at": "2026-05-07T01:02:03+00:00",
                "schema_version": 1,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError) as excinfo:
        load_promoted_model(marker_path=marker_path)

    message = str(excinfo.value)
    assert run_id in message
    assert "training-sweeps" in message
