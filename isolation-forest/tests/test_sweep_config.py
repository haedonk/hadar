import pytest

from pipeline.sweep_config import load_sweep_config


def test_load_yaml_sweep_config_applies_defaults(tmp_path) -> None:
    config_path = tmp_path / "sweep.yaml"
    config_path.write_text(
        """
name: contamination-sweep
defaults:
  random_state: 42
  test_size: 0.2
  min_training_rows: 10
  n_estimators: 100
configs:
  - name: contamination_0_01
    contamination: 0.01
    feature_columns:
      - temperature
      - temperature_zscore
  - name: contamination_0_05
    contamination: 0.05
    random_state: 7
""",
        encoding="utf-8",
    )

    config = load_sweep_config(config_path)

    assert config.name == "contamination-sweep"
    assert config.configs[0].random_state == 42
    assert config.configs[0].contamination == 0.01
    assert config.configs[0].n_estimators == 100
    assert config.configs[0].feature_columns == ["temperature", "temperature_zscore"]
    assert config.configs[1].random_state == 7


def test_load_csv_sweep_config(tmp_path) -> None:
    config_path = tmp_path / "grid.csv"
    config_path.write_text(
        "name,contamination,random_state,test_size,min_training_rows,n_estimators,feature_columns\n"
        "contamination_0_01,0.01,42,0.2,10,200,temperature|temperature_zscore\n",
        encoding="utf-8",
    )

    config = load_sweep_config(config_path)

    assert config.name == "grid"
    assert config.configs[0].name == "contamination_0_01"
    assert config.configs[0].min_training_rows == 10
    assert config.configs[0].n_estimators == 200
    assert config.configs[0].feature_columns == ["temperature", "temperature_zscore"]


def test_load_sweep_config_rejects_duplicate_names(tmp_path) -> None:
    config_path = tmp_path / "sweep.csv"
    config_path.write_text(
        "name,contamination,random_state,test_size,min_training_rows,n_estimators\n"
        "same,0.01,42,0.2,10,100\n"
        "same,0.05,42,0.2,10,100\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate"):
        load_sweep_config(config_path)


def test_load_sweep_config_rejects_invalid_contamination(tmp_path) -> None:
    config_path = tmp_path / "sweep.csv"
    config_path.write_text(
        "name,contamination,random_state,test_size,min_training_rows,n_estimators\n"
        "bad,0.9,42,0.2,10,100\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid contamination"):
        load_sweep_config(config_path)
