from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from doomsdaybot.routines import effective_task_group, task_setting_specs


CATEGORY_TITLES = {
    "startup": "Запуск",
    "daily": "Ежедневные действия",
    "development": "Развитие",
    "army": "Лечение",
    "training": "Производство войск",
    "marches": "Боевые задачи",
    "resources": "Сбор ресурсов",
    "custom": "Другие задачи",
}

CATEGORY_ORDER = ("startup", "daily", "development", "army", "training", "marches", "resources", "custom")


def _center(window, width, height):
    window.update_idletasks()
    x = max(0, (window.winfo_screenwidth() - width) // 2)
    y = max(0, (window.winfo_screenheight() - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


class TaskSettingsDialog:
    def __init__(self, parent, bot, task, refresh):
        self.parent = parent
        self.bot = bot
        self.task = task
        self.refresh = refresh
        self.vars = {}
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(task.get("name", "Настройки"))
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        _center(self.dialog, 470, 430)
        self._build()

    def _build(self):
        body = ttk.Frame(self.dialog, padding=16)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(body, text=self.task.get("name", ""), style="CompactTitle.TLabel").pack(anchor="w")

        form = ttk.Frame(body)
        form.pack(fill=tk.X, pady=(14, 8))
        settings = self.task.setdefault("settings", {})
        row = 0
        for spec in task_setting_specs(self.task["id"]):
            ttk.Label(form, text=spec["label"]).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
            value = settings.get(spec["key"])
            kind = spec["kind"]
            if kind == "bool":
                variable = tk.BooleanVar(value=bool(value))
                widget = ttk.Checkbutton(form, variable=variable)
            elif kind == "choice":
                labels = {stored: label for stored, label in spec["choices"]}
                reverse = {label: stored for stored, label in spec["choices"]}
                variable = tk.StringVar(value=labels.get(value, next(iter(labels.values()))))
                widget = ttk.Combobox(form, textvariable=variable, values=list(reverse), state="readonly", width=23)
                spec = dict(spec, reverse=reverse)
            else:
                variable = tk.IntVar(value=int(value or spec.get("min", 0)))
                widget = ttk.Spinbox(
                    form,
                    from_=spec.get("min", 0),
                    to=spec.get("max", 1000000),
                    textvariable=variable,
                    width=12,
                )
            widget.grid(row=row, column=1, sticky="w", pady=5)
            self.vars[spec["key"]] = (variable, spec)
            row += 1

        ttk.Label(form, text="Повтор, минут").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        self.interval_var = tk.DoubleVar(value=float(self.task.get("interval_minutes", 1.0)))
        ttk.Spinbox(form, from_=0.1, to=1440, increment=0.5, textvariable=self.interval_var, width=12).grid(
            row=row, column=1, sticky="w", pady=5
        )

        group = effective_task_group(self.task)
        templates = [image for image in self.bot.search_images if image.get("group") == group]
        ttk.Label(body, text=f"Шаблонов: {len(templates)}", foreground="#6b7280").pack(anchor="w", pady=(8, 2))

        completion_map = {
            f"{image.get('description', '')} [{str(image.get('uid', ''))[:8]}]": image.get("uid", "")
            for image in templates
        }
        self.completion_map = completion_map
        selected_label = next(
            (label for label, uid in completion_map.items() if uid == self.task.get("completion_uid")),
            "Авто по таймауту",
        )
        self.completion_var = tk.StringVar(value=selected_label)
        ttk.Label(body, text="Финальный шаг").pack(anchor="w", pady=(8, 2))
        ttk.Combobox(
            body,
            textvariable=self.completion_var,
            values=["Авто по таймауту", *completion_map],
            state="readonly",
            width=48,
        ).pack(fill=tk.X)

        buttons = ttk.Frame(body)
        buttons.pack(fill=tk.X, side=tk.BOTTOM, pady=(16, 0))
        ttk.Button(buttons, text="Снять шаблон", command=self.capture_template).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Сохранить", style="Primary.TButton", command=self.save).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="Отмена", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=8)
        self.dialog.bind("<Escape>", lambda _event: self.dialog.destroy())

    def _apply(self):
        settings = self.task.setdefault("settings", {})
        for key, (variable, spec) in self.vars.items():
            value = variable.get()
            if spec["kind"] == "choice":
                value = spec["reverse"].get(value, "off")
            settings[key] = value
        self.task["interval_minutes"] = max(0.1, float(self.interval_var.get()))
        self.task["group"] = effective_task_group(self.task)
        self.task["completion_uid"] = self.completion_map.get(self.completion_var.get(), "")
        if self.task["id"] == "gathering_boost":
            self.task["interval_minutes"] = max(
                self.task["interval_minutes"],
                float(settings.get("boost_hours", 8)) * 60.0,
            )
        self.bot.groups[self.task["group"]] = bool(self.task.get("enabled", False))
        self.bot.save_config()
        self.refresh()

    def save(self):
        try:
            self._apply()
        except (tk.TclError, TypeError, ValueError) as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self.dialog)
            return
        self.dialog.destroy()

    def capture_template(self):
        try:
            self._apply()
        except (tk.TclError, TypeError, ValueError) as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self.dialog)
            return
        group = effective_task_group(self.task)
        count = len([image for image in self.bot.search_images if image.get("group") == group]) + 1
        self.dialog.destroy()
        self.bot.select_area(
            self.parent,
            default_group=group,
            default_description=f"{self.task.get('name')} {count}",
        )


class AccountsDialog:
    def __init__(self, parent, bot, refresh):
        self.parent = parent
        self.bot = bot
        self.refresh = refresh
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Аккаунты LDPlayer")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        _center(self.dialog, 530, 400)
        self._build()

    def _build(self):
        body = ttk.Frame(self.dialog, padding=14)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            body,
            text="Один LDPlayer, несколько сохранённых аккаунтов",
            style="CompactTitle.TLabel",
        ).pack(anchor="w")
        self.listbox = tk.Listbox(body, height=10, font=("Segoe UI", 10), activestyle="none")
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=12)
        self._reload()

        buttons = ttk.Frame(body)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Добавить", command=self.add).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Удалить", command=self.delete).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="Снять шаг входа", command=self.capture_switch).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="Сменить в игре", style="Primary.TButton", command=self.switch_in_game).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="Профиль", command=self.select).pack(side=tk.RIGHT, padx=6)
        self.dialog.bind("<Escape>", lambda _event: self.dialog.destroy())

    def _reload(self):
        self.listbox.delete(0, tk.END)
        for profile in self.bot.account_profiles:
            mark = "●" if profile.get("id") == self.bot.current_account_id else " "
            self.listbox.insert(
                tk.END,
                f"{mark} {profile.get('name')} | LD {profile.get('ldplayer_index')} | {profile.get('adb_serial')}",
            )
        if self.bot.account_profiles:
            current = next(
                (i for i, profile in enumerate(self.bot.account_profiles) if profile.get("id") == self.bot.current_account_id),
                0,
            )
            self.listbox.selection_set(current)

    def _selected(self):
        selection = self.listbox.curselection()
        if not selection:
            return None
        return self.bot.account_profiles[selection[0]]

    def add(self):
        name = simpledialog.askstring("Новый аккаунт", "Название аккаунта:", parent=self.dialog)
        if not name or not name.strip():
            return
        chooser_index = simpledialog.askinteger(
            "Новый аккаунт",
            "Номер строки аккаунта Google (сверху):",
            parent=self.dialog,
            minvalue=1,
            maxvalue=20,
            initialvalue=len(self.bot.account_profiles) + 1,
        )
        if chooser_index is None:
            return
        profile = self.bot.add_account_profile(
            name.strip(), 5, self.bot.adb_serial, 30.0, chooser_index=chooser_index
        )
        self.bot.select_account_profile(profile["id"])
        self._reload()
        self.refresh()

    def delete(self):
        profile = self._selected()
        if not profile:
            return
        if not messagebox.askyesno("Аккаунты", f"Удалить профиль «{profile.get('name')}»?", parent=self.dialog):
            return
        if not self.bot.remove_account_profile(profile["id"]):
            messagebox.showwarning("Аккаунты", "Нельзя удалить единственный профиль.", parent=self.dialog)
            return
        self._reload()
        self.refresh()

    def select(self):
        profile = self._selected()
        if not profile:
            return
        self.bot.select_account_profile(profile["id"])
        self.dialog.destroy()
        self.refresh()

    def switch_in_game(self):
        profile = self._selected()
        if not profile:
            return
        if not self.bot.start_account_switch(profile["id"]):
            messagebox.showwarning(
                "Аккаунты",
                "Сначала снимите последовательность входа для этого аккаунта.",
                parent=self.dialog,
            )
            return
        self.dialog.destroy()
        self.refresh()

    def capture_switch(self):
        profile = self._selected()
        if not profile:
            return
        group = "Переключение аккаунта"
        count = len([image for image in self.bot.search_images if image.get("group") == group]) + 1
        self.dialog.destroy()
        self.bot.select_area(
            self.parent,
            default_group=group,
            default_description=f"Вход {profile.get('name')} {count}",
        )


def build_compact_ui(root, bot):
    for after_name in ("status_after_id", "active_after_id", "monitor_after_id", "compact_after_id"):
        after_id = getattr(root, after_name, None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except tk.TclError:
                pass
            setattr(root, after_name, None)
    for widget in root.winfo_children():
        widget.destroy()

    root.title("Doomsday Routine")
    root.geometry("760x820")
    root.minsize(680, 650)
    root.configure(bg="#f3f1eb")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background="#f3f1eb")
    style.configure("TLabel", background="#f3f1eb", foreground="#20231f", font=("Segoe UI", 10))
    style.configure("TLabelframe", background="#f3f1eb", bordercolor="#cbc7bc")
    style.configure("TLabelframe.Label", background="#f3f1eb", foreground="#20231f", font=("Segoe UI Semibold", 10))
    style.configure("TCheckbutton", background="#f3f1eb", font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI Semibold", 9), padding=(10, 7))
    style.configure("Primary.TButton", foreground="white", background="#1f6b52")
    style.map("Primary.TButton", background=[("active", "#18533f"), ("disabled", "#9ca3af")])
    style.configure("Danger.TButton", foreground="white", background="#a63d32")
    style.map("Danger.TButton", background=[("active", "#832f27")])
    style.configure("CompactTitle.TLabel", font=("Segoe UI Semibold", 15), foreground="#173f35")

    outer = ttk.Frame(root, padding=14)
    outer.pack(fill=tk.BOTH, expand=True)

    header = ttk.Frame(outer)
    header.pack(fill=tk.X)
    ttk.Label(header, text="DOOMSDAY ROUTINE", style="CompactTitle.TLabel").pack(side=tk.LEFT)
    ttk.Label(header, text=f"v{getattr(bot, 'app_version', '3.0.0')} · LDPlayer").pack(side=tk.RIGHT)

    account_frame = ttk.LabelFrame(outer, text="Аккаунт", padding=9)
    account_frame.pack(fill=tk.X, pady=(12, 8))
    account_var = tk.StringVar()
    account_combo = ttk.Combobox(account_frame, textvariable=account_var, state="readonly", width=24)
    account_combo.pack(side=tk.LEFT)
    rotation_var = tk.BooleanVar(value=bot.account_rotation_enabled)
    ttk.Checkbutton(account_frame, text="Автосмена", variable=rotation_var).pack(side=tk.LEFT, padx=12)

    def save_rotation():
        bot.account_rotation_enabled = bool(rotation_var.get())
        bot.save_config()

    rotation_var.trace_add("write", lambda *_args: save_rotation())
    ttk.Button(account_frame, text="Управление", command=lambda: AccountsDialog(root, bot, refresh_all)).pack(side=tk.RIGHT)

    task_vars = {}
    task_rows = {}
    canvas_frame = ttk.Frame(outer)
    canvas_frame.pack(fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(canvas_frame, bg="#f3f1eb", highlightthickness=0)
    scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
    content = ttk.Frame(canvas)
    window_id = canvas.create_window((0, 0), window=content, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
    canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"))

    def toggle_task(task):
        value = bool(task_vars[task["id"]].get())
        bot.set_routine_enabled(task["id"], value)
        refresh_all()

    def build_task_rows():
        for widget in content.winfo_children():
            widget.destroy()
        task_vars.clear()
        task_rows.clear()
        grouped = {}
        for task in bot.routine_tasks:
            grouped.setdefault(task.get("category", "custom"), []).append(task)
        for category in CATEGORY_ORDER:
            tasks = grouped.get(category, [])
            if not tasks:
                continue
            frame = ttk.LabelFrame(content, text=CATEGORY_TITLES.get(category, category), padding=8)
            frame.pack(fill=tk.X, pady=4)
            frame.columnconfigure(0, weight=1)
            frame.columnconfigure(1, weight=1)
            for index, task in enumerate(tasks):
                cell = ttk.Frame(frame)
                cell.grid(row=index // 2, column=index % 2, sticky="ew", padx=4, pady=3)
                variable = tk.BooleanVar(value=bool(task.get("enabled", False)))
                task_vars[task["id"]] = variable
                ttk.Checkbutton(
                    cell,
                    text=task.get("name", task["id"]),
                    variable=variable,
                    command=lambda current=task: toggle_task(current),
                ).pack(side=tk.LEFT)
                group = effective_task_group(task)
                template_count = len([image for image in bot.search_images if image.get("group") == group])
                if task_setting_specs(task["id"]):
                    ttk.Button(
                        cell,
                        text="⋯",
                        width=3,
                        command=lambda current=task: TaskSettingsDialog(root, bot, current, refresh_all),
                    ).pack(side=tk.RIGHT)
                status = "готово" if template_count else "не обучено"
                label = ttk.Label(cell, text=status, foreground="#1f6b52" if template_count else "#9a3412")
                label.pack(side=tk.RIGHT, padx=6)
                task_rows[task["id"]] = label

    control = ttk.Frame(outer)
    control.pack(fill=tk.X, pady=(10, 6))
    start_button = ttk.Button(control, text="Запустить выбранное", style="Primary.TButton", command=bot.start_routines)
    start_button.pack(side=tk.LEFT)
    pause_button = ttk.Button(control, text="Пауза", command=bot.toggle_pause)
    pause_button.pack(side=tk.LEFT, padx=6)
    stop_button = ttk.Button(control, text="Стоп", style="Danger.TButton", command=bot.stop)
    stop_button.pack(side=tk.LEFT)

    marches = ttk.Frame(control)
    marches.pack(side=tk.RIGHT)
    ttk.Label(marches, text="Походы").pack(side=tk.LEFT, padx=4)
    marches_var = tk.IntVar(value=bot.routine_max_marches)

    def save_marches():
        try:
            bot.routine_max_marches = min(5, max(1, int(marches_var.get())))
        except (tk.TclError, ValueError):
            return
        bot.routine_march_deadlines = bot.routine_march_deadlines[:bot.routine_max_marches]
        bot.save_config()

    ttk.Spinbox(marches, from_=1, to=5, width=3, textvariable=marches_var, command=save_marches).pack(side=tk.LEFT)

    adb_frame = ttk.LabelFrame(outer, text="ADB и экран", padding=7)
    adb_frame.pack(fill=tk.X, pady=4)
    adb_state = tk.StringVar(value="ADB и экран: проверка...")
    ttk.Label(adb_frame, textvariable=adb_state, wraplength=700).pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
    adb_controls = ttk.Frame(adb_frame)
    adb_controls.pack(fill=tk.X, side=tk.TOP)
    check_busy = {"value": False}

    def check_environment():
        if check_busy["value"]:
            return
        check_busy["value"] = True
        adb_state.set("ADB и экран: проверка...")
        check_button.configure(state=tk.DISABLED)

        def worker():
            ok = bot.check_runtime_environment(notify=False, wait_seconds=45.0)
            summary = bot.get_environment_summary()

            def finish():
                check_busy["value"] = False
                check_button.configure(state=tk.NORMAL)
                adb_state.set(summary)
                if not ok:
                    bot.sync_status_message()

            root.after(0, finish)

        threading.Thread(target=worker, name="EnvironmentCheck", daemon=True).start()

    repair_button = ttk.Button(adb_controls, text="Восстановить ADB")

    def repair_adb():
        target = bot.get_adb_repair_target()
        if not target:
            bot.check_adb_connection(notify=True)
            return
        if not messagebox.askyesno(
            "Восстановление ADB",
            f"Будет включён ADB и перезапущен только LDPlayer {target.index} «{target.name}». Продолжить?",
            parent=root,
        ):
            return
        repair_button.configure(state=tk.DISABLED)
        bot.set_status_message(
            f"Перезапуск LDPlayer {target.index}. Ожидание подключения до 90 секунд...",
            force=True,
        )

        def worker():
            ok = bot.repair_adb_connection(target.index)

            def finish():
                repair_button.configure(state=tk.NORMAL)
                check_environment()
                title = "Связь восстановлена" if ok else "ADB не подключён"
                message = (
                    f"Подключено устройство {bot.adb_serial}."
                    if ok else "Не удалось подключиться. Нажмите «Создать отчёт»."
                )
                (messagebox.showinfo if ok else messagebox.showerror)(title, message, parent=root)

            root.after(0, finish)

        threading.Thread(target=worker, name="AdbRepair", daemon=True).start()

    repair_button.configure(command=repair_adb)
    repair_button.pack(side=tk.RIGHT)
    check_button = ttk.Button(
        adb_controls,
        text="Проверить ADB и экран",
        command=check_environment,
    )
    check_button.pack(side=tk.RIGHT, padx=5)

    def create_report():
        try:
            report_path = bot.create_diagnostic_report()
        except Exception as exc:
            messagebox.showerror("Отчёт", f"Не удалось создать отчёт:\n{exc}", parent=root)
            return
        messagebox.showinfo("Отчёт создан", f"Файл сохранён:\n{report_path}", parent=root)

    ttk.Button(adb_controls, text="Создать отчёт", command=create_report).pack(side=tk.RIGHT, padx=5)

    status_var = tk.StringVar(value=bot.status_message or "Готов к запуску")
    bot.attach_status_var(status_var)
    status_frame = ttk.LabelFrame(outer, text="Состояние", padding=9)
    status_frame.pack(fill=tk.X, pady=(4, 0))
    ttk.Label(status_frame, textvariable=status_var, wraplength=690, justify=tk.LEFT).pack(anchor="w")

    def select_account(_event=None):
        name = account_var.get()
        profile = next((item for item in bot.account_profiles if item.get("name") == name), None)
        if profile:
            bot.select_account_profile(profile["id"])
            refresh_all()

    account_combo.bind("<<ComboboxSelected>>", select_account)

    def refresh_all():
        names = [profile.get("name") for profile in bot.account_profiles]
        account_combo["values"] = names
        current = bot.get_current_account()
        account_var.set(current.get("name") if current else (names[0] if names else ""))
        build_task_rows()

    def update_state():
        if bot.is_running:
            start_button.configure(state=tk.DISABLED)
            pause_button.configure(state=tk.NORMAL, text="Продолжить" if bot.is_paused else "Пауза")
            stop_button.configure(state=tk.NORMAL)
        else:
            ready_state = tk.DISABLED if check_busy["value"] else tk.NORMAL
            start_button.configure(state=ready_state)
            pause_button.configure(state=tk.DISABLED, text="Пауза")
            stop_button.configure(state=tk.DISABLED)
        root.compact_after_id = root.after(500, update_state)

    root.bind("<<AccountChanged>>", lambda _event: refresh_all())
    refresh_all()
    root.after(250, check_environment)
    update_state()
