"""Promotion marker loader for the active scoring model.

The training/sweep service publishes a small JSON marker (``promoted_model.json``)
that names the currently promoted ``run_id`` / ``config_name``. This module
reads that marker and reconstructs the artifact directory layout shared with
``isolation-forest/``::

    <marker_dir>/training-sweeps/<run_id>/configs/<config_name>/models

If the marker is missing or malformed we fall back to the env-pinned
``MODEL_*`` values so local dev / CI keep working.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from config import config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromotedModel:
    """Resolved scoring-model pointer for one scoring run."""

    run_id: str
    config_name: str
    artifact_dir: Path
    promoted_at: str | None
    source: Literal["marker", "env"]


def load_promoted_model(marker_path: Path | str | None = None) -> PromotedModel:
    """Read the promotion marker, falling back to env vars if absent or unreadable.

    Behaviour:
      - Marker present and parseable -> use it; ``source == "marker"``.
      - Marker absent -> fall back to env-pinned config; ``source == "env"``;
        WARNING logged.
      - Marker present but malformed -> fall back to env-pinned config;
        ``source == "env"``; ERROR logged. (Scoring should not be broken by a
        bad marker.)
      - Reconstructed artifact directory does not exist on disk -> raise
        ``FileNotFoundError`` (no silent fallback to a different model).
    """
    resolved_marker_path = Path(marker_path or config.MODEL_PROMOTION_MARKER_PATH)

    promoted = _try_load_marker(resolved_marker_path)
    if promoted is None:
        promoted = _env_fallback()

    if not promoted.artifact_dir.exists():
        raise FileNotFoundError(
            "Reconstructed model artifact directory does not exist: "
            f"{promoted.artifact_dir} (run_id={promoted.run_id}, "
            f"config_name={promoted.config_name}, source={promoted.source})"
        )

    logger.info(
        "Resolved promoted model from %s: run_id=%s config_name=%s artifact_dir=%s",
        promoted.source,
        promoted.run_id,
        promoted.config_name,
        promoted.artifact_dir,
    )
    return promoted


def _try_load_marker(marker_path: Path) -> PromotedModel | None:
    if not marker_path.exists():
        logger.warning(
            "No promotion marker at %s; using env-pinned model",
            marker_path,
        )
        return None

    try:
        payload = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception(
            "Promotion marker at %s is malformed; falling back to env-pinned model",
            marker_path,
        )
        return None

    if not isinstance(payload, dict):
        logger.error(
            "Promotion marker at %s is not a JSON object; falling back to env-pinned model",
            marker_path,
        )
        return None

    run_id = payload.get("run_id")
    config_name = payload.get("config_name")
    if not isinstance(run_id, str) or not run_id or not isinstance(config_name, str) or not config_name:
        logger.error(
            "Promotion marker at %s missing run_id/config_name; falling back to env-pinned model",
            marker_path,
        )
        return None

    artifact_dir = _build_artifact_dir(marker_path.parent, run_id, config_name)
    promoted_at = payload.get("promoted_at") if isinstance(payload.get("promoted_at"), str) else None
    return PromotedModel(
        run_id=run_id,
        config_name=config_name,
        artifact_dir=artifact_dir,
        promoted_at=promoted_at,
        source="marker",
    )


def _env_fallback() -> PromotedModel:
    return PromotedModel(
        run_id=config.MODEL_RUN_ID,
        config_name=config.MODEL_CONFIG_NAME,
        artifact_dir=Path(config.MODEL_ARTIFACT_DIR),
        promoted_at=None,
        source="env",
    )


def _build_artifact_dir(marker_dir: Path, run_id: str, config_name: str) -> Path:
    """Reconstruct the per-config models dir from the marker directory."""
    return marker_dir / "training-sweeps" / run_id / "configs" / config_name / "models"
