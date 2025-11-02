"""
Check all config.yaml.* files are valid configs by loading them with config.py
"""

from pathlib import Path

import pytest

from app.core.config import _validate_config, load_config


def get_config_files():
    """Discover all config.yaml.* files in devops directory, excluding template."""
    devops_dir = Path(__file__).parent
    config_files = sorted(devops_dir.glob("config.yaml.*"))
    # Exclude template file as it's not a valid config
    config_files = [f for f in config_files if f.name != "config.yaml.template"]
    return [str(f) for f in config_files]


@pytest.mark.parametrize("config_path", get_config_files())
def test_load_config(config_path):
    """Test loading and validating configuration file."""
    config = load_config(config_path)
    _validate_config(config)
