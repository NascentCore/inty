<<<<<<< HEAD
from app.utils.gcs import append_filename_suffix, get_bucket_and_path_from_gcs_url
=======
from app.utils.gcs import append_filename_suffix, get_path_from_gcs_url
>>>>>>> f8305cc1 (Add append_filename_suffix)
from app.core.config import global_config_loaded_from_config_yaml


def test_get_bucket_and_path_from_gcs_url():
    old_bucket = global_config_loaded_from_config_yaml.gcs.bucket
    global_config_loaded_from_config_yaml.gcs.bucket = "test-bucket"
<<<<<<< HEAD
    assert (
        get_bucket_and_path_from_gcs_url(
            "https://storage.googleapis.com/test-bucket/test-path"
        )
        == "test-path"
    )
    assert (
        get_bucket_and_path_from_gcs_url(
            "https://storage.googleapis.com/test-bucket/test-path"
        )
        == "test-path"
    )
    assert get_bucket_and_path_from_gcs_url("gs://test-bucket/test-path") == "test-path"
    assert (
        get_bucket_and_path_from_gcs_url(
            "https://storage.googleapis.com/test-bucket/test-path"
        )
        == "test-path"
    )
    assert (
        get_bucket_and_path_from_gcs_url(
            "https://storage.googleapis.com/test-bucket/test-path/test-path2"
        )
        == "test-path/test-path2"
    )
    assert (
        get_bucket_and_path_from_gcs_url("gs://test-bucket/test-path/test-path2")
        == "test-path/test-path2"
    )
    assert (
        get_bucket_and_path_from_gcs_url(
            "https://storage.googleapis.com/test-bucket/test-path/test-path2"
        )
        == "test-path/test-path2"
    )
=======
    assert get_path_from_gcs_url("https://storage.googleapis.com/test-bucket/test-path") == "test-path"
    assert get_path_from_gcs_url("https://storage.googleapis.com/test-bucket/test-path") == "test-path"
    assert get_path_from_gcs_url("gs://test-bucket/test-path") == "test-path"
    assert get_path_from_gcs_url("https://storage.googleapis.com/test-bucket/test-path") == "test-path"
    assert get_path_from_gcs_url("https://storage.googleapis.com/test-bucket/test-path/test-path2") == "test-path/test-path2"
    assert get_path_from_gcs_url("gs://test-bucket/test-path/test-path2") == "test-path/test-path2"
    assert get_path_from_gcs_url("https://storage.googleapis.com/test-bucket/test-path/test-path2") == "test-path/test-path2"
>>>>>>> f8305cc1 (Add append_filename_suffix)
    global_config_loaded_from_config_yaml.gcs.bucket = old_bucket


def test_append_filename_suffix():
    assert append_filename_suffix("a/b.c", "suffix") == "a/bsuffix.c"
    assert append_filename_suffix("a/b", "suffix") == "a/bsuffix"
    assert append_filename_suffix("b.c", "-suffix") == "b-suffix.c"
    assert append_filename_suffix("b", "-suffix") == "b-suffix"
