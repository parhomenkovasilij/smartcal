"""Аналітичне ядро SmartCal: пошук вільних вікон і розбиття завдань на блоки (SCF_04–SCF_06)."""
from datetime import datetime, timedelta

from .models import Block, FixedEvent, PlanResult, Settings, Task

STEP = timedelta(minutes=15)  # дискретність розкладу


def round_up(dt: datetime) -> datetime:
    """Округлює час вгору до найближчих 15 хвилин."""
    base = dt.replace(second=0, microsecond=0)
    extra = base.minute % 15
    if extra or dt != base:
        base += timedelta(minutes=15 - extra) if extra else STEP
    return base


def find_free_windows(busy: list[tuple[datetime, datetime]], start: datetime,
                      end: datetime, settings: Settings) -> list[tuple[datetime, datetime]]:
    """Повертає вільні проміжки в межах робочого часу доби між start і end."""
    windows = []
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    busy = sorted(busy)
    while day < end:
        w_start = max(day + timedelta(hours=settings.day_start_h), start)
        w_end = min(day + timedelta(hours=settings.day_end_h), end)
        cursor = w_start
        for b_start, b_end in busy:
            if b_end <= cursor or b_start >= w_end:
                continue
            if b_start > cursor:
                windows.append((cursor, b_start))
            cursor = max(cursor, b_end)
        if cursor < w_end:
            windows.append((cursor, w_end))
        day += timedelta(days=1)
    return [(s, e) for s, e in windows if e - s >= STEP]


def split_task(task: Task, hours_needed: float, windows: list[tuple[datetime, datetime]],
               settings: Settings) -> tuple[list[Block], float]:
    """Розбиває потрібну кількість годин на блоки у вільних вікнах.

    Повертає список блоків і кількість годин, які не вдалося розмістити.
    """
    remaining = timedelta(hours=hours_needed)
    min_len = timedelta(hours=settings.min_block_h)
    max_len = timedelta(hours=settings.max_block_h)
    pause = timedelta(minutes=settings.break_min)
    blocks: list[Block] = []
    for w_start, w_end in windows:
        cursor = w_start
        while remaining > timedelta(0):
            available = w_end - cursor
            length = min(max_len, remaining, available)
            # блок коротший за мінімальний дозволений лише як «хвіст» завдання
            if length < min_len and length < remaining:
                break
            if length <= timedelta(0):
                break
            blocks.append(Block(task_id=task.id, start=cursor, end=cursor + length))
            remaining -= length
            cursor += length + pause
        if remaining <= timedelta(0):
            break
    return blocks, remaining / timedelta(hours=1)


def plan(tasks: list[Task], events: list[FixedEvent], now: datetime,
         settings: Settings, done_blocks: list[Block] | None = None) -> PlanResult:
    """Формує розклад для всіх завдань.

    Завдання обробляються за зростанням дедлайну, а за однакового дедлайну —
    за пріоритетом. Вже виконані блоки зменшують потрібний обсяг годин.
    """
    done_blocks = done_blocks or []
    start = round_up(now)
    busy = [(e.start, e.end) for e in events]
    result = PlanResult()
    for task in sorted(tasks, key=lambda t: (t.deadline, t.priority)):
        done_h = sum(b.hours for b in done_blocks if b.task_id == task.id and b.status == "done")
        need = task.duration_h - done_h
        if need <= 0:
            continue
        windows = find_free_windows(busy, start, task.deadline, settings)
        blocks, deficit = split_task(task, need, windows, settings)
        result.blocks.extend(blocks)
        busy.extend((b.start, b.end + timedelta(minutes=settings.break_min)) for b in blocks)
        if deficit > 1e-9:
            result.deficits[task.id] = round(deficit, 2)
    result.blocks.sort(key=lambda b: b.start)
    return result


def free_hours(events: list[FixedEvent], now: datetime, deadline: datetime,
               settings: Settings) -> float:
    """Сумарна кількість вільних годин до дедлайну (для контролю перевантаження, SCF_05)."""
    windows = find_free_windows([(e.start, e.end) for e in events], round_up(now), deadline, settings)
    return sum((e - s) / timedelta(hours=1) for s, e in windows)
