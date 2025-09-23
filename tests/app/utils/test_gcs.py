from google.cloud.storage import bucket

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.gcs import (
    append_filename_suffix,
    get_bucket_and_path_from_gcs_url,
)


def test_get_bucket_and_path_from_gcs_url():
    assert get_bucket_and_path_from_gcs_url("gs://test-bucket/test-path") == [
        "test-bucket",
        "test-path",
    ]
    assert get_bucket_and_path_from_gcs_url(
        "https://storage.googleapis.com/test-bucket/test-path/test-path2"
    ) == [
        "test-bucket",
        "test-path/test-path2",
    ]
    assert get_bucket_and_path_from_gcs_url(
        "https://storage.cloud.google.com/test-bucket/test-path/test-path2"
    ) == [
        "test-bucket",
        "test-path/test-path2",
    ]


def test_append_filename_suffix():
    assert append_filename_suffix("a/b.c", "suffix") == "a/bsuffix.c"
    assert append_filename_suffix("a/b", "suffix") == "a/bsuffix"
    assert append_filename_suffix("b.c", "-suffix") == "b-suffix.c"
    assert append_filename_suffix("b", "-suffix") == "b-suffix"
