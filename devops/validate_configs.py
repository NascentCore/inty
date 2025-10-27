"""
Check both config.yaml.{dev,prod} are valid configs by loading them with config.py
"""

from app.core.config import _validate_config, load_config


def test_load_test_config():
    """Test loading dev configuration file."""
    config = load_config("devops/config.yaml.test")
    _validate_config(config)


def test_load_dev_config():
    """Test loading dev configuration file."""
    config = load_config("devops/config.yaml.dev")
    _validate_config(config)


def test_load_prod_config():
    """Test loading dev configuration file."""
    config = load_config("devops/config.yaml.prod")
    _validate_config(config)
