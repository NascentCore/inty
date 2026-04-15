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


def test_set_langsmith_environment_variables_disables_tracing_in_test_env():
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        os.environ.pop("LANGSMITH_TRACING_V2", None)
        set_langsmith_environment_variables(_make_config(Environment.TEST))
        assert os.environ["LANGSMITH_TRACING_V2"] == "false"
        assert os.environ["LANGSMITH_PROJECT"] == "inty-backend-test"
        assert os.environ["LANGCHAIN_API_KEY"] == "langchain-key-for-test"
    finally:
        _restore_env(original_values)


def test_set_langsmith_environment_variables_enables_tracing_in_non_test_env():
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


def test_set_langsmith_environment_variables_respects_explicit_langsmith_tracing_v2_false():
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


def test_set_langsmith_environment_variables_respects_explicit_langsmith_tracing_v2_true_in_test():
    keys = ["LANGSMITH_TRACING_V2", "LANGSMITH_PROJECT", "LANGCHAIN_API_KEY"]
    original_values = {key: os.environ.get(key) for key in keys}
    try:
        os.environ["LANGSMITH_TRACING_V2"] = "true"
        set_langsmith_environment_variables(_make_config(Environment.TEST))
        assert os.environ["LANGSMITH_TRACING_V2"] == "true"
        assert os.environ["LANGSMITH_PROJECT"] == "inty-backend-test"
        assert os.environ["LANGCHAIN_API_KEY"] == "langchain-key-for-test"
    finally:
        _restore_env(original_values)
