import os
import yaml


def test_config_file_exists():
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "config.yaml",
    )
    assert os.path.exists(config_path), f"Config file not found at {config_path}"


def test_env_file_exists():
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        ".env",
    )
    assert os.path.exists(env_path), f"Env file not found at {env_path}"


def test_config_has_required_keys():
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "config.yaml",
    )
    with open(config_path) as f:
        config = yaml.safe_load(f)

    assert "database" in config
    assert "storage" in config
    assert "file_format" in config
    assert "business_rules" in config
    assert "logging" in config
    assert "auth" in config
    assert config["business_rules"]["grace_period_minutes"] == 5
    assert config["file_format"]["delimiter"] == "|"


def test_requirements_txt():
    req_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "requirements.txt",
    )
    assert os.path.exists(req_path)

    with open(req_path) as f:
        pkgs = f.read()

    for pkg in ["fastapi", "sqlalchemy", "pandas", "psycopg2", "uvicorn", "minio"]:
        assert pkg in pkgs, f"Missing required package: {pkg}"
