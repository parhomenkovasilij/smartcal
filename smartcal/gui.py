"""Графічний інтерфейс SmartCal на Tkinter (SCN_01)."""
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk

from .export import export_csv, export_txt, schedule_rows
from .models import PRIORITY_NAMES, Settings
from .service import SmartCalService
from .validation import DATE_FMT, ValidationError, parse_dt

PRIORITY_COLORS = {1: "#e57373", 2: "#ffd54f", 3: "#81c784"}
EVENT_COLOR = "#90a4ae"
HOUR_PX = 28
DAY_PX = 120


class MainWindow(tk.Tk):
    def __init__(self, service: SmartCalService):
        super().__init__()
        self.service = service
        self.title("SmartCal — розумний календар-планувальник")
        self.geometry("1000x680")
        self.week_start = self._monday(datetime.now())
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.calendar_tab = ttk.Frame(nb)
        self.events_tab = ttk.Frame(nb)
        self.tasks_tab = ttk.Frame(nb)
        self.schedule_tab = ttk.Frame(nb)
        self.settings_tab = ttk.Frame(nb)
        nb.add(self.calendar_tab, text="Календар")
        nb.add(self.events_tab, text="Фіксовані події")
        nb.add(self.tasks_tab, text="Завдання")
        nb.add(self.schedule_tab, text="Розклад")
        nb.add(self.settings_tab, text="Налаштування")

        self._build_calendar()
        self._build_events()
        self._build_tasks()
        self._build_schedule()
        self._build_settings()
        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=6, pady=2)
        self.service.replan()
        self.refresh()  # під час запуску лише рядок стану, без спливаючого вікна

    @staticmethod
    def _monday(dt: datetime) -> datetime:
        d = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return d - timedelta(days=d.weekday())

    # ---------- Календар ----------
    def _build_calendar(self):
        bar = ttk.Frame(self.calendar_tab)
        bar.pack(fill="x")
        ttk.Button(bar, text="◀ Попередній тиждень", command=lambda: self._shift(-7)).pack(side="left")
        ttk.Button(bar, text="Сьогодні", command=self._today).pack(side="left")
        ttk.Button(bar, text="Наступний тиждень ▶", command=lambda: self._shift(7)).pack(side="left")
        self.week_label = ttk.Label(bar)
        self.week_label.pack(side="left", padx=10)
        self.canvas = tk.Canvas(self.calendar_tab, bg="white", height=24 * HOUR_PX + 30)
        self.canvas.pack(fill="both", expand=True)

    def _shift(self, days):
        self.week_start += timedelta(days=days)
        self.refresh()

    def _today(self):
        self.week_start = self._monday(datetime.now())
        self.refresh()

    def _draw_calendar(self):
        c = self.canvas
        c.delete("all")
        s = self.service.storage.settings()
        top, left = 24, 50
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
        for i in range(7):
            d = self.week_start + timedelta(days=i)
            c.create_text(left + i * DAY_PX + DAY_PX / 2, 12, text=f"{days[i]} {d:%d.%m}")
        for h in range(s.day_start_h, s.day_end_h + 1):
            y = top + (h - s.day_start_h) * HOUR_PX
            c.create_line(left, y, left + 7 * DAY_PX, y, fill="#eee")
            c.create_text(left - 20, y, text=f"{h:02d}:00", font=("Arial", 8))
        week_end = self.week_start + timedelta(days=7)

        def place(start, end, color, text):
            if not (self.week_start <= start < week_end):
                return
            col = (start - self.week_start).days
            y1 = top + (start.hour + start.minute / 60 - s.day_start_h) * HOUR_PX
            y2 = top + (end.hour + end.minute / 60 - s.day_start_h) * HOUR_PX
            x = left + col * DAY_PX
            c.create_rectangle(x + 2, y1, x + DAY_PX - 2, y2, fill=color, outline="#555")
            c.create_text(x + 6, y1 + 2, text=text, anchor="nw", width=DAY_PX - 10, font=("Arial", 8))

        for e in self.service.storage.events():
            place(e.start, e.end, EVENT_COLOR, e.title)
        tasks = {t.id: t for t in self.service.storage.tasks()}
        for b in self.service.storage.blocks():
            t = tasks.get(b.task_id)
            if t:
                color = "#cfd8dc" if b.status == "skipped" else PRIORITY_COLORS[t.priority]
                mark = {"done": " ✔", "skipped": " ✖"}.get(b.status, "")
                place(b.start, b.end, color, t.title + mark)
        self.week_label.config(text=f"{self.week_start:%d.%m.%Y} – {week_end - timedelta(days=1):%d.%m.%Y}")

    # ---------- Фіксовані події ----------
    def _build_events(self):
        form = ttk.LabelFrame(self.events_tab, text="Нова подія жорсткого розкладу")
        form.pack(fill="x", padx=6, pady=6)
        self.ev_title, self.ev_start, self.ev_end = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for i, (label, var) in enumerate([("Назва", self.ev_title), (f"Початок ({DATE_FMT})", self.ev_start),
                                          ("Кінець", self.ev_end)]):
            ttk.Label(form, text=label).grid(row=0, column=2 * i, padx=4)
            ttk.Entry(form, textvariable=var, width=22).grid(row=0, column=2 * i + 1, padx=4)
        ttk.Button(form, text="Додати", command=self.add_event).grid(row=0, column=6, padx=4)
        self.events_list = ttk.Treeview(self.events_tab, columns=("start", "end", "title"), show="headings")
        for col, name in zip(("start", "end", "title"), ("Початок", "Кінець", "Назва")):
            self.events_list.heading(col, text=name)
        self.events_list.pack(fill="both", expand=True, padx=6)
        ttk.Button(self.events_tab, text="Видалити обрану", command=self.delete_event).pack(pady=4)

    def add_event(self):
        try:
            self.service.add_event(self.ev_title.get(), parse_dt(self.ev_start.get()), parse_dt(self.ev_end.get()))
        except ValidationError as e:
            messagebox.showerror("Помилка введення", str(e))
            return
        self.ev_title.set("")
        self.refresh(self.service.last_result)

    def delete_event(self):
        for item in self.events_list.selection():
            self.service.delete_event(int(item))
        self.refresh(self.service.last_result)

    # ---------- Завдання ----------
    def _build_tasks(self):
        form = ttk.LabelFrame(self.tasks_tab, text="Нове гнучке завдання")
        form.pack(fill="x", padx=6, pady=6)
        self.t_title, self.t_deadline = tk.StringVar(), tk.StringVar()
        self.t_hours, self.t_prio = tk.StringVar(value="2"), tk.StringVar(value=PRIORITY_NAMES[2])
        ttk.Label(form, text="Назва").grid(row=0, column=0)
        ttk.Entry(form, textvariable=self.t_title, width=28).grid(row=0, column=1, padx=4)
        ttk.Label(form, text=f"Дедлайн ({DATE_FMT})").grid(row=0, column=2)
        ttk.Entry(form, textvariable=self.t_deadline, width=18).grid(row=0, column=3, padx=4)
        ttk.Label(form, text="Години").grid(row=0, column=4)
        ttk.Entry(form, textvariable=self.t_hours, width=6).grid(row=0, column=5, padx=4)
        ttk.Label(form, text="Пріоритет").grid(row=0, column=6)
        ttk.Combobox(form, textvariable=self.t_prio, values=list(PRIORITY_NAMES.values()),
                     state="readonly", width=10).grid(row=0, column=7, padx=4)
        ttk.Button(form, text="Додати й розпланувати", command=self.add_task).grid(row=0, column=8, padx=4)
        self.tasks_list = ttk.Treeview(self.tasks_tab, columns=("title", "deadline", "hours", "prio", "deficit"),
                                       show="headings")
        for col, name in zip(("title", "deadline", "hours", "prio", "deficit"),
                             ("Назва", "Дедлайн", "Години", "Пріоритет", "Дефіцит, год")):
            self.tasks_list.heading(col, text=name)
        self.tasks_list.pack(fill="both", expand=True, padx=6)
        ttk.Button(self.tasks_tab, text="Видалити обране", command=self.delete_task).pack(pady=4)

    def add_task(self):
        try:
            hours = float(self.t_hours.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Помилка введення", "Тривалість має бути числом")
            return
        prio = {v: k for k, v in PRIORITY_NAMES.items()}[self.t_prio.get()]
        try:
            self.service.add_task(self.t_title.get(), parse_dt(self.t_deadline.get()), hours, prio)
        except ValidationError as e:
            messagebox.showerror("Помилка введення", str(e))
            return
        self.t_title.set("")
        self.refresh(self.service.last_result)

    def delete_task(self):
        for item in self.tasks_list.selection():
            self.service.delete_task(int(item))
        self.refresh(self.service.last_result)

    # ---------- Розклад ----------
    def _build_schedule(self):
        bar = ttk.Frame(self.schedule_tab)
        bar.pack(fill="x", padx=6, pady=4)
        ttk.Button(bar, text="Виконано", command=lambda: self.mark("done")).pack(side="left")
        ttk.Button(bar, text="Пропущено", command=lambda: self.mark("skipped")).pack(side="left", padx=4)
        ttk.Button(bar, text="Експорт CSV", command=lambda: self.export("csv")).pack(side="right")
        ttk.Button(bar, text="Експорт TXT", command=lambda: self.export("txt")).pack(side="right", padx=4)
        self.blocks_list = ttk.Treeview(self.schedule_tab, columns=("date", "start", "end", "title", "status"),
                                        show="headings")
        for col, name in zip(("date", "start", "end", "title", "status"),
                             ("Дата", "Початок", "Кінець", "Завдання", "Статус")):
            self.blocks_list.heading(col, text=name)
        self.blocks_list.pack(fill="both", expand=True, padx=6)

    def mark(self, status):
        sel = self.blocks_list.selection()
        if not sel:
            messagebox.showinfo("SmartCal", "Оберіть робочий блок у таблиці")
            return
        for item in sel:
            result = self.service.mark_block(int(item), status)
        self.refresh(result)

    def export(self, kind):
        path = filedialog.asksaveasfilename(defaultextension=f".{kind}", filetypes=[(kind.upper(), f"*.{kind}")])
        if not path:
            return
        st = self.service.storage
        rows = schedule_rows(st.blocks(), st.events(), st.tasks(), self.week_start, self.week_start + timedelta(days=7))
        (export_csv if kind == "csv" else export_txt)(path, rows)
        self.status.set(f"Розклад збережено у файл {path}")

    # ---------- Налаштування ----------
    def _build_settings(self):
        s = self.service.storage.settings()
        self.set_vars = {k: tk.StringVar(value=str(v)) for k, v in vars(s).items()}
        labels = {"min_block_h": "Мінімальна тривалість блоку, год", "max_block_h": "Максимальна тривалість блоку, год",
                  "break_min": "Перерва між блоками, хв", "day_start_h": "Початок робочого дня, год",
                  "day_end_h": "Кінець робочого дня, год"}
        for i, (key, text) in enumerate(labels.items()):
            ttk.Label(self.settings_tab, text=text).grid(row=i, column=0, sticky="w", padx=8, pady=4)
            ttk.Entry(self.settings_tab, textvariable=self.set_vars[key], width=8).grid(row=i, column=1)
        ttk.Button(self.settings_tab, text="Зберегти й перерахувати", command=self.save_settings).grid(
            row=len(labels), column=0, columnspan=2, pady=8)

    def save_settings(self):
        try:
            s = Settings(**{k: type(getattr(Settings(), k))(float(v.get())) for k, v in self.set_vars.items()})
            if not 0.25 <= s.min_block_h <= s.max_block_h or not 0 <= s.day_start_h < s.day_end_h <= 24:
                raise ValueError
        except ValueError:
            messagebox.showerror("Помилка введення", "Перевірте значення налаштувань")
            return
        self.service.update_settings(s)
        self.refresh(self.service.last_result)

    # ---------- Оновлення ----------
    def refresh(self, result=None):
        st = self.service.storage
        tasks = st.tasks()
        names = {t.id: t.title for t in tasks}
        deficits = result.deficits if result else self.service.last_result.deficits
        self.events_list.delete(*self.events_list.get_children())
        for e in st.events():
            self.events_list.insert("", "end", iid=str(e.id), values=(e.start.strftime(DATE_FMT),
                                                                     e.end.strftime(DATE_FMT), e.title))
        self.tasks_list.delete(*self.tasks_list.get_children())
        for t in tasks:
            self.tasks_list.insert("", "end", iid=str(t.id), values=(
                t.title, t.deadline.strftime(DATE_FMT), t.duration_h, PRIORITY_NAMES[t.priority],
                deficits.get(t.id, "—")))
        self.blocks_list.delete(*self.blocks_list.get_children())
        status_names = {"planned": "Заплановано", "done": "Виконано", "skipped": "Пропущено"}
        for b in st.blocks():
            self.blocks_list.insert("", "end", iid=str(b.id), values=(
                b.start.strftime("%d.%m.%Y"), b.start.strftime("%H:%M"), b.end.strftime("%H:%M"),
                names.get(b.task_id, "?"), status_names[b.status]))
        self._draw_calendar()
        if deficits:
            lines = [f"«{names.get(tid, tid)}»: бракує {h} год" for tid, h in deficits.items()]
            self.status.set("Увага! Перевантаження: " + "; ".join(lines))
            if result is not None:
                messagebox.showwarning("Дефіцит часу", "Вільного часу до дедлайну недостатньо:\n" + "\n".join(lines))
        else:
            self.status.set("Розклад актуальний")

    def on_close(self):
        self.service.storage.close()
        self.destroy()
