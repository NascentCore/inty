from datetime import date

from app.services import festival_memory_task_state_service as task_state_service


def setup_function() -> None:
    task_state_service.clear_run_states()


def test_get_run_state_returns_none_when_not_exists() -> None:
    assert task_state_service.get_run_state(1001) is None


def test_mark_running_and_completed_updates_state() -> None:
    config_id = 2001
    festival_name = "Thanksgiving"
    festival_date = date(2026, 11, 26)

    task_state_service.mark_running(config_id, festival_name, festival_date)
    running_state = task_state_service.get_run_state(config_id)

    assert running_state is not None
    assert running_state.run_status == task_state_service.RUN_STATUS_RUNNING
    assert running_state.run_started_at is not None
    assert running_state.run_finished_at is None
    assert running_state.run_total_pairs is None

    task_state_service.mark_completed(
        config_id,
        festival_name,
        festival_date,
        total_pairs=12,
        success_count=10,
        failed_count=2,
    )
    completed_state = task_state_service.get_run_state(config_id)

    assert completed_state is not None
    assert completed_state.run_status == task_state_service.RUN_STATUS_COMPLETED
    assert completed_state.run_started_at == running_state.run_started_at
    assert completed_state.run_finished_at is not None
    assert completed_state.run_total_pairs == 12
    assert completed_state.run_success_count == 10
    assert completed_state.run_failed_count == 2
    assert completed_state.run_error_message is None


def test_mark_failed_records_error_message() -> None:
    config_id = 3001
    festival_name = "Christmas"
    festival_date = date(2026, 12, 25)

    task_state_service.mark_running(config_id, festival_name, festival_date)
    task_state_service.mark_failed(
        config_id,
        festival_name,
        festival_date,
        total_pairs=5,
        success_count=2,
        failed_count=3,
        error_message="db timeout",
    )
    failed_state = task_state_service.get_run_state(config_id)

    assert failed_state is not None
    assert failed_state.run_status == task_state_service.RUN_STATUS_FAILED
    assert failed_state.run_total_pairs == 5
    assert failed_state.run_success_count == 2
    assert failed_state.run_failed_count == 3
    assert failed_state.run_error_message == "db timeout"
