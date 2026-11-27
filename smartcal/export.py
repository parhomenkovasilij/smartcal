"""Формування зведеного розкладу та експорт у файл (SCF_08)."""
import csv
from datetime import datetime

from .models import Block, FixedEvent, Task

STATUS_NAMES = {"planned": "Заплановано", "done": "Виконано", "skipped": "Пропущено"}


def schedule_rows(blocks: list[Block], events: list[FixedEvent], tasks: list[Task],
                  start: datetime, end: datetime) -> list[list[str]]:
    """Рядки таблиці розкладу за період: дата, початок, кінець, назва, статус."""
    names = {t.id: t.title for t in tasks}
    items = [(e.start, e.end, e.title, "Фіксована подія") for e in events]
    items += [(b.start, b.end, names.get(b.task_id, "?"), STATUS_NAMES[b.status]) for b in blocks]
    rows = []
    for s, e, title, status in sorted(items):
        if start <= s < end:
            rows.append([s.strftime("%d.%m.%Y"), s.strftime("%H:%M"), e.strftime("%H:%M"),
                         title, status])
    return rows


def export_csv(path: str, rows: list[list[str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Дата", "Початок", "Кінець", "Назва", "Статус"])
        writer.writerows(rows)


def export_txt(path: str, rows: list[list[str]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("Розклад SmartCal\n\n")
        for r in rows:
            f.write(f"{r[0]}  {r[1]}–{r[2]}  {r[3]}  [{r[4]}]\n")
