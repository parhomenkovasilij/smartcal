"""Моделі предметної області SmartCal."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

PRIORITY_NAMES = {1: "Високий", 2: "Середній", 3: "Низький"}


@dataclass
class FixedEvent:
    """Подія «жорсткого розкладу», яку не можна пересунути."""
    title: str
    start: datetime
    end: datetime
    id: int | None = None

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return self.start < end and start < self.end


@dataclass
class Task:
    """Гнучке завдання з дедлайном та оцінкою тривалості."""
    title: str
    deadline: datetime
    duration_h: float
    priority: int = 2
    id: int | None = None


@dataclass
class Block:
    """Робочий блок, згенерований планувальником для завдання."""
    task_id: int
    start: datetime
    end: datetime
    status: str = "planned"  # planned | done | skipped
    id: int | None = None

    @property
    def hours(self) -> float:
        return (self.end - self.start) / timedelta(hours=1)


@dataclass
class Settings:
    """Обмеження планування."""
    min_block_h: float = 1.0
    max_block_h: float = 2.0
    break_min: int = 15
    day_start_h: int = 8
    day_end_h: int = 22


@dataclass
class PlanResult:
    """Результат роботи планувальника."""
    blocks: list[Block] = field(default_factory=list)
    deficits: dict[int, float] = field(default_factory=dict)  # task_id -> годин бракує

    @property
    def ok(self) -> bool:
        return not self.deficits
