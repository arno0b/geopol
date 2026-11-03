"""Sydney briefing slots: run ids and time-window checks.

Usage:
    python tools/slot.py current          # print the run id for now
    python tools/slot.py check fetch      # exit 0 inside the fetch window, else 3
    python tools/slot.py check briefing
"""
import sys
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

SYDNEY = ZoneInfo("Australia/Sydney")

# (start, end) local-time windows, end exclusive. Midnight-crossing windows are split.
WINDOWS = {
    "fetch": [(time(9, 0), time(9, 40)), (time(23, 0), time(23, 40))],
    "briefing": [(time(9, 30), time(10, 30)), (time(23, 30), time.max), (time(0, 0), time(0, 30))],
}


def _local(dt: datetime) -> datetime:
    return dt.astimezone(SYDNEY)


def run_id_for(dt: datetime) -> str:
    local = _local(dt)
    if 9 <= local.hour <= 21:
        return local.strftime("%Y-%m-%d") + "-1000"
    day = local.date() + timedelta(days=1) if local.hour >= 22 else local.date()
    return day.strftime("%Y-%m-%d") + "-0000"


def parse_run_id(run_id: str) -> datetime:
    return datetime.strptime(run_id, "%Y-%m-%d-%H%M").replace(tzinfo=SYDNEY)


def in_window(dt: datetime, stage: str) -> bool:
    t = _local(dt).time()
    return any(start <= t < end for start, end in WINDOWS[stage])


def main(argv: list[str]) -> int:
    now = datetime.now(SYDNEY)
    if argv[:1] == ["current"]:
        print(run_id_for(now))
        return 0
    if len(argv) == 2 and argv[0] == "check" and argv[1] in WINDOWS:
        inside = in_window(now, argv[1])
        print(f"{argv[1]} window: {'open' if inside else 'closed'} ({now:%Y-%m-%d %H:%M} Sydney)")
        return 0 if inside else 3
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
