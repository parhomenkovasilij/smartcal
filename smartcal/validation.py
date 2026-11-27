"""Перевірка вхідних даних (SCF_02, SCF_03)."""
from datetime import datetime

from .models import FixedEvent, Task

DATE_FMT = "%d.%m.%Y %H:%M"


class ValidationError(ValueError):
    """Помилка введених даних; текст показується користувачу."""


def parse_dt(text: str) -> datetime:
    try:
        return datetime.strptime(text.strip(), DATE_FMT)
    except ValueError:
        raise ValidationError(f"Невірний формат дати «{text}». Очікується ДД.ММ.РРРР ГГ:ХХ")


def validate_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise ValidationError("Назва не може бути порожньою")
    if len(title) > 100:
        raise ValidationError("Назва не може бути довшою за 100 символів")
    return title


def validate_event(event: FixedEvent, existing: list[FixedEvent]) -> None:
    validate_title(event.title)
    if event.end <= event.start:
        raise ValidationError("Час завершення події має бути пізніше за час початку")
    for other in existing:
        if other.id != event.id and other.overlaps(event.start, event.end):
            raise ValidationError(f"Подія перетинається з «{other.title}»")


def validate_task(task: Task, now: datetime) -> None:
    validate_title(task.title)
    if task.deadline <= now:
        raise ValidationError("Дедлайн має бути пізніше поточного часу")
    if not 0.5 <= task.duration_h <= 500:
        raise ValidationError("Тривалість завдання має бути від 0,5 до 500 годин")
    if task.priority not in (1, 2, 3):
        raise ValidationError("Пріоритет має бути 1 (високий), 2 (середній) або 3 (низький)")
