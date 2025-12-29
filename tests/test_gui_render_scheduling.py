from woodcut_duotone.gui.state import RenderScheduler


def test_render_scheduler_single_flight_with_pending() -> None:
    scheduler = RenderScheduler()

    assert scheduler.request_render()
    for _ in range(10):
        assert not scheduler.request_render()

    assert scheduler.in_flight
    assert scheduler.pending

    assert scheduler.on_render_finished()
    assert not scheduler.in_flight
    assert not scheduler.pending

    assert scheduler.request_render()
    assert scheduler.in_flight


def test_render_scheduler_no_pending_finish() -> None:
    scheduler = RenderScheduler()

    assert scheduler.request_render()
    assert scheduler.on_render_finished() is False
    assert not scheduler.in_flight
    assert not scheduler.pending
