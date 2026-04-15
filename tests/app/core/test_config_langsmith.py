import os
from types import SimpleNamespace

from app.core.config import Environment, set_langsmith_environment_variables


def _restore_env(original_values: dict[str, str | None]) -> None:
    for key, value in original_values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _make_config(environment: Environment) -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(name="inty-backend", environment=environment),
        agent=SimpleNamespace(langchain_api_key="langchain-key-for-test"),
    )


def test_set_langsmith_environment_variables_tracing_off_when_langsmith_tracing_v2_unset():
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        os.environ.pop("LANGSMITH_TRACING_V2", None)
        set_langsmith_environment_variables(_make_config(Environment.DEV))
        assert os.environ["LANGSMITH_TRACING_V2"] == "false"
        assert os.environ["LANGSMITH_PROJECT"] == "inty-backend-dev"
        assert os.environ["LANGCHAIN_API_KEY"] == "langchain-key-for-test"
    finally:
        _restore_env(original_values)


def test_set_langsmith_environment_variables_tracing_on_only_when_langsmith_tracing_v2_truthy():
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        os.environ["LANGSMITH_TRACING_V2"] = "true"
        set_langsmith_environment_variables(_make_config(Environment.DEV))
        assert os.environ["LANGSMITH_TRACING_V2"] == "true"
        assert os.environ["LANGSMITH_PROJECT"] == "inty-backend-dev"
        assert os.environ["LANGCHAIN_API_KEY"] == "langchain-key-for-test"
    finally:
        _restore_env(original_values)


def test_set_langsmith_environment_variables_tracing_off_for_explicit_false():
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        os.environ["LANGSMITH_TRACING_V2"] = "false"
        set_langsmith_environment_variables(_make_config(Environment.DEV))
        assert os.environ["LANGSMITH_TRACING_V2"] == "false"
        assert os.environ["LANGSMITH_PROJECT"] == "inty-backend-dev"
        assert os.environ["LANGCHAIN_API_KEY"] == "langchain-key-for-test"
    finally:
        _restore_env(original_values)


def test_set_langsmith_environment_variables_truthy_tokens_enable_tracing():
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        for token in ("1", "yes", "on", "TRUE"):
            os.environ["LANGSMITH_TRACING_V2"] = token
            set_langsmith_environment_variables(_make_config(Environment.TEST))
            assert os.environ["LANGSMITH_TRACING_V2"] == "true", token
        assert os.environ["LANGSMITH_PROJECT"] == "inty-backend-test"
    finally:
        _restore_env(original_values)


def test_set_langsmith_environment_variables_unrecognized_langsmith_tracing_v2_is_off():
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        os.environ["LANGSMITH_TRACING_V2"] = "maybe"
        set_langsmith_environment_variables(_make_config(Environment.DEV))
        assert os.environ["LANGSMITH_TRACING_V2"] == "false"
    finally:
        _restore_env(original_values)
