"""Сервісний шар: поєднує валідацію, планувальник і сховище."""
from datetime import datetime

from . import scheduler
from .models import FixedEvent, PlanResult, Settings, Task
from .storage import Storage
from .validation import validate_event, validate_task


class SmartCalService:
    def __init__(self, storage: Storage, clock=datetime.now):
        self.storage = storage
        self.clock = clock
        self.last_result = PlanResult()

    def add_event(self, title: str, start: datetime, end: datetime) -> FixedEvent:
        ev = FixedEvent(title.strip(), start, end)
        validate_event(ev, self.storage.events())
        self.storage.save_event(ev)
        self.replan()
        return ev

    def delete_event(self, event_id: int) -> None:
        self.storage.delete_event(event_id)
        self.replan()

    def add_task(self, title: str, deadline: datetime, duration_h: float, priority: int) -> Task:
        task = Task(title.strip(), deadline, duration_h, priority)
        validate_task(task, self.clock())
        self.storage.save_task(task)
        self.replan()
        return task

    def delete_task(self, task_id: int) -> None:
        self.storage.delete_task(task_id)
        self.replan()

    def update_settings(self, settings: Settings) -> None:
        self.storage.save_settings(settings)
        self.replan()

    def mark_block(self, block_id: int, status: str) -> PlanResult:
        """Відмітка «Виконано»/«Пропущено». Пропуск запускає перерахунок (SCF_06)."""
        self.storage.set_block_status(block_id, status)
        return self.replan()

    def replan(self) -> PlanResult:
        now = self.clock()
        history = [b for b in self.storage.blocks() if b.status != "planned"]
        tasks = [t for t in self.storage.tasks() if t.deadline > now]
        result = scheduler.plan(tasks, self.storage.events(), now, self.storage.settings(), history)
        self.storage.replace_planned_blocks(result.blocks)
        self.last_result = result
        return result
