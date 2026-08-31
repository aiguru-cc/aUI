import threading

import pytest

from aui.core.dispatcher import UIDispatcher


def test_dispatch_runs_immediately_on_owner_thread():
    dispatcher = UIDispatcher()
    values = []
    assert dispatcher.dispatch(lambda: values.append("now")) is True
    assert values == ["now"]


def test_worker_callbacks_wait_for_owner_and_preserve_fifo_order():
    dispatcher = UIDispatcher()
    values = []

    worker = threading.Thread(
        target=lambda: (
            dispatcher.dispatch(lambda: values.append(1)),
            dispatcher.dispatch(lambda: values.append(2)),
        )
    )
    worker.start()
    worker.join()
    assert values == []
    assert dispatcher.drain() == 2
    assert values == [1, 2]


def test_schedule_once_coalesces_until_callback_runs():
    dispatcher = UIDispatcher()
    values = []
    assert dispatcher.schedule_once("refresh", lambda: values.append(1)) is True
    assert dispatcher.schedule_once("refresh", lambda: values.append(2)) is False
    assert dispatcher.drain() == 1
    assert values == [1]
    assert dispatcher.schedule_once("refresh", lambda: values.append(3)) is True
    dispatcher.drain()
    assert values == [1, 3]


def test_close_discards_callbacks_and_rejects_new_work():
    dispatcher = UIDispatcher()
    dispatcher.schedule_once("refresh", lambda: pytest.fail("stale callback ran"))
    dispatcher.close()
    assert dispatcher.drain() == 0
    assert dispatcher.dispatch(lambda: None) is False


def test_drain_rejects_non_owner_thread():
    dispatcher = UIDispatcher()
    errors = []
    worker = threading.Thread(target=lambda: _capture_error(dispatcher, errors))
    worker.start()
    worker.join()
    assert isinstance(errors[0], RuntimeError)


def test_event_loop_can_adopt_its_starting_thread():
    dispatcher = UIDispatcher()
    owner_ids = []

    def run_loop():
        dispatcher.adopt_current_thread()
        owner_ids.append(dispatcher.is_ui_thread)

    worker = threading.Thread(target=run_loop)
    worker.start()
    worker.join()
    assert owner_ids == [True]
    assert dispatcher.is_ui_thread is False


def _capture_error(dispatcher, errors):
    try:
        dispatcher.drain()
    except Exception as error:
        errors.append(error)
