from datetime import date, datetime, time as time_type
from typing import Any, Optional


def normalize_langsmith_metadata_value(value: Any) -> Any:
    """Convert metadata values into LangSmith-friendly readable structures."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (datetime, date, time_type)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            str(key): normalize_langsmith_metadata_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [normalize_langsmith_metadata_value(item) for item in value]

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return normalize_langsmith_metadata_value(model_dump())

    table = getattr(value, "__table__", None)
    if table is not None and hasattr(table, "columns"):
        serialized: dict[str, Any] = {}
        for column in table.columns:
            serialized[column.name] = normalize_langsmith_metadata_value(
                getattr(value, column.name, None)
            )
        return serialized

    return str(value)


def normalize_langsmith_metadata(
    metadata: Optional[dict[str, Any]],
) -> dict[str, Any]:
    if not metadata:
        return {}
    return {
        str(key): normalize_langsmith_metadata_value(value)
        for key, value in metadata.items()
    }
