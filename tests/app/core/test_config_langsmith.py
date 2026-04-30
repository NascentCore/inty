import os
from types import SimpleNamespace

from app.core.config import Environment, set_langsmith_environment_variables


def _restore_env(original_values: dict[str, str | None]) -> None:
    for key, value in original_values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _make_config(
    environment: Environment, *, langsmith_tracing_enabled: bool = True
) -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(name="inty-backend", environment=environment),
        agent=SimpleNamespace(
            langchain_api_key="langchain-key-for-test",
            langsmith_tracing_enabled=langsmith_tracing_enabled,
        ),
    )


def test_set_langsmith_environment_variables_tracing_off_when_config_false():
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        os.environ.pop("LANGSMITH_TRACING_V2", None)
        set_langsmith_environment_variables(
            _make_config(Environment.DEV, langsmith_tracing_enabled=False)
        )
        assert os.environ["LANGSMITH_TRACING_V2"] == "false"
        assert os.environ["LANGSMITH_PROJECT"] == "inty-backend-dev"
        assert os.environ["LANGCHAIN_API_KEY"] == "langchain-key-for-test"
    finally:
        _restore_env(original_values)


def test_set_langsmith_environment_variables_tracing_on_when_config_true():
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        os.environ.pop("LANGSMITH_TRACING_V2", None)
        set_langsmith_environment_variables(_make_config(Environment.DEV))
        assert os.environ["LANGSMITH_TRACING_V2"] == "true"
        assert os.environ["LANGSMITH_PROJECT"] == "inty-backend-dev"
        assert os.environ["LANGCHAIN_API_KEY"] == "langchain-key-for-test"
    finally:
        _restore_env(original_values)


def test_set_langsmith_environment_variables_local_project_includes_username(monkeypatch):
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        monkeypatch.setenv("USER", "repl_tester")
        monkeypatch.delenv("USERNAME", raising=False)
        os.environ.pop("LANGSMITH_TRACING_V2", None)
        set_langsmith_environment_variables(_make_config(Environment.LOCAL))
        assert os.environ["LANGSMITH_PROJECT"] == "inty-backend-local-repl_tester"
        assert os.environ["LANGCHAIN_API_KEY"] == "langchain-key-for-test"
    finally:
        _restore_env(original_values)


def test_set_langsmith_environment_variables_prior_config_over_shell_langsmith_env():
    """YAML 开关生效；进程里残留的 LANGSMITH_TRACING_V2 由 set_langsmith 覆盖。"""
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        os.environ["LANGSMITH_TRACING_V2"] = "true"
        set_langsmith_environment_variables(
            _make_config(Environment.TEST, langsmith_tracing_enabled=False)
        )
        assert os.environ["LANGSMITH_TRACING_V2"] == "false"
        os.environ["LANGSMITH_TRACING_V2"] = "false"
        set_langsmith_environment_variables(_make_config(Environment.TEST))
        assert os.environ["LANGSMITH_TRACING_V2"] == "true"
    finally:
        _restore_env(original_values)
