from datetime import datetime, timezone

from tools.slot import SYDNEY, in_window, parse_run_id, run_id_for


def d(y, m, day, h, mi):
    return datetime(y, m, day, h, mi, tzinfo=SYDNEY)


def test_morning_slot():
    assert run_id_for(d(2026, 11, 4, 9, 20)) == "2026-11-04-1000"


def test_late_evening_rolls_to_next_midnight():
    assert run_id_for(d(2026, 11, 4, 23, 30)) == "2026-11-05-0000"


def test_just_after_midnight():
    assert run_id_for(d(2026, 11, 5, 0, 10)) == "2026-11-05-0000"


def test_month_end_rolls_over():
    assert run_id_for(d(2026, 11, 30, 23, 30)) == "2026-12-01-0000"


def test_roundtrip():
    assert parse_run_id("2026-11-04-1000") == d(2026, 11, 4, 10, 0)


def test_fetch_window():
    assert in_window(d(2026, 11, 4, 9, 20), "fetch")
    assert not in_window(d(2026, 11, 4, 10, 20), "fetch")


def test_briefing_window_spans_midnight():
    assert in_window(d(2026, 11, 5, 0, 15), "briefing")
    assert in_window(d(2026, 11, 4, 23, 45), "briefing")
    assert not in_window(d(2026, 11, 4, 15, 0), "briefing")


def test_dst_utc_input():
    # 22:20 UTC on 3 Nov = 09:20 AEDT on 4 Nov
    assert run_id_for(datetime(2026, 11, 3, 22, 20, tzinfo=timezone.utc)) == "2026-11-04-1000"


def test_off_offset_cron_is_outside_fetch_window():
    # In AEDT, the AEST cron (23:20 UTC) lands at 10:20 local and must be skipped
    assert not in_window(datetime(2026, 11, 3, 23, 20, tzinfo=timezone.utc), "fetch")
