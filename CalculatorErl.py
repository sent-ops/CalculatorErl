import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import csv
import json
from datetime import datetime

ACCURACY = 1e-9

def first_erlang_formula(v: int, a: float) -> float:
    """Вычисление доли потерь по первой формуле Эрланга (B-формула)."""
    if a <= 0:
        return 0.0
    if v < 1000:
        p = 1.0
        for i in range(1, v + 1):
            p = a * p / (i + p * a)
        return p
    else:
        r = 1.0
        s_sum = 1.0
        for s in range(1, v + 1):
            r = r * (v - s + 1) / a
            s_sum += r
            rs = r * (v - s) / a
            if rs < ACCURACY:
                return 1.0 / s_sum
        return 1.0 / s_sum


def erlang_find_min_v(a: float, p_norm: float) -> int:
    """Нахождение минимального числа каналов v при известных a и норме потерь p."""
    v = 1
    while True:
        p0 = 1.0
        for i in range(1, v + 1):
            p0 = a * p0 / (i + p0 * a)
        if p0 <= p_norm:
            return v
        v += 1
        if v > 10_000:
            raise ValueError("Не удалось найти v (превышен лимит 10 000 каналов)")


def calc_m_from_a_p(a: float, p: float) -> float:
    """Среднее число занятых каналов: m = a*(1-p)."""
    return a * (1.0 - p)


def find_a_newton(v: int, m: float) -> tuple[float, float, float]:
    """
    Нахождение a методом Ньютона при известных v и m.
    Возвращает (a, p, m_real).
    """
    a0 = m
    for _ in range(10_000):
        p = first_erlang_formula(v, a0)
        denom = 1.0 - p * (v + 1 - a0 * (1.0 - p))
        if abs(denom) < 1e-15:
            break
        a = a0 + (m - a0 * (1.0 - p)) / denom
        f = m - a * (1.0 - p)
        if abs(f) <= ACCURACY:
            p_final = first_erlang_formula(v, a)
            return a, p_final, a * (1.0 - p_final)
        a0 = a
    raise ValueError("Метод Ньютона не сошёлся (v, m)")


def find_a_bisection(v: int, p_norm: float) -> tuple[float, float, float]:
    """
    Нахождение a методом деления пополам при известных v и норме потерь p.
    Возвращает (a, p_real, m).
    """
    lo, hi = 0.0, float(v) * 100
    for _ in range(200):
        mid = (lo + hi) / 2.0
        p_mid = first_erlang_formula(v, mid)
        if p_mid < p_norm:
            lo = mid
        else:
            hi = mid
        if (hi - lo) < ACCURACY:
            break
    a = (lo + hi) / 2.0
    p_real = first_erlang_formula(v, a)
    return a, p_real, calc_m_from_a_p(a, p_real)


def solve(known: dict) -> dict:
    keys = set(known.keys())
    if keys == {"v", "a"}:
        v, a = int(known["v"]), known["a"]
        p = first_erlang_formula(v, a)
        m = calc_m_from_a_p(a, p)
        return {"v": v, "a": a, "p": p, "m": m}
    elif keys == {"v", "p"}:
        v, p_norm = int(known["v"]), known["p"]
        a, p_real, m = find_a_bisection(v, p_norm)
        return {"v": v, "a": a, "p": p_real, "m": m}
    elif keys == {"v", "m"}:
        v, m = int(known["v"]), known["m"]
        a, p, m_real = find_a_newton(v, m)
        return {"v": v, "a": a, "p": p, "m": m_real}
    elif keys == {"a", "p"}:
        a, p_norm = known["a"], known["p"]
        v = erlang_find_min_v(a, p_norm)
        p_real = first_erlang_formula(v, a)
        m = calc_m_from_a_p(a, p_real)
        return {"v": v, "a": a, "p": p_real, "m": m}
    elif keys == {"a", "m"}:
        a, m = known["a"], known["m"]
        if m >= a:
            raise ValueError("Среднее число занятых каналов m должно быть меньше a")
        p_calc = 1.0 - m / a
        v = erlang_find_min_v(a, p_calc)
        p_real = first_erlang_formula(v, a)
        m_real = calc_m_from_a_p(a, p_real)
        return {"v": v, "a": a, "p": p_real, "m": m_real}
    elif keys == {"p", "m"}:
        p_norm, m = known["p"], known["m"]
        a = m / (1.0 - p_norm)
        v = erlang_find_min_v(a, p_norm)
        p_real = first_erlang_formula(v, a)
        m_real = calc_m_from_a_p(a, p_real)
        return {"v": v, "a": a, "p": p_real, "m": m_real}
    else:
        raise ValueError("Неподдерживаемая комбинация параметров")

MAX_VAL = 2_000_000_000

def validate_inputs(known: dict) -> str | None:
    """Возвращает строку с описанием ошибки или None если всё корректно."""
    if "v" in known:
        v = known["v"]
        if not isinstance(v, int) or v < 1:
            return "Число каналов v должно быть положительным целым числом (≥ 1)"
        if v > MAX_VAL:
            return f"Число каналов v не должно превышать {MAX_VAL:,}"

    if "a" in known:
        a = known["a"]
        if a <= 0:
            return "Интенсивность трафика a должна быть положительным числом"
        if a > MAX_VAL:
            return f"Интенсивность трафика a не должна превышать {MAX_VAL:,}"

    if "p" in known:
        p = known["p"]
        if not (0 < p < 1):
            return "Доля потерь p должна быть в интервале (0, 1)"

    if "m" in known:
        m = known["m"]
        if m <= 0:
            return "Среднее число занятых каналов m должно быть положительным"
        if m > MAX_VAL:
            return f"Среднее число занятых каналов m не должно превышать {MAX_VAL:,}"

    if "v" in known and "m" in known:
        if known["m"] >= known["v"]:
            return "Среднее число занятых каналов m должно быть меньше числа каналов v"

    if "a" in known and "m" in known:
        if known["m"] >= known["a"]:
            return "Среднее число занятых каналов m должно быть меньше интенсивности трафика a"

    return None


PARAMS = [
    ("v", "Число каналов (v)", "целое число ≥ 1"),
    ("a", "Интенсивность трафика (a), Эрл", "положительное число"),
    ("p", "Доля потерь (p)", "число в интервале (0, 1)"),
    ("m", "Среднее число зан. кан. (m)", "положительное число"),
]

BG         = "#1e1e2e"
BG2        = "#2a2a3e"
BG3        = "#313149"
ACCENT     = "#7c6af7"
ACCENT2    = "#a89cf7"
TEXT       = "#cdd6f4"
TEXT_DIM   = "#6c7086"
GREEN      = "#a6e3a1"
RED        = "#f38ba8"
YELLOW     = "#f9e2af"
BORDER     = "#45475a"


class ErlangApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Калькулятор Эрланга")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.history: list[dict] = []
        self.op_id = 0

        self._build_ui()
        self._update_state()

        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w)//2}+{(sh - h)//2}")


    def _build_ui(self):
        pad = dict(padx=18, pady=6)

        hdr = tk.Frame(self, bg=BG, pady=14)
        hdr.pack(fill="x")
        tk.Label(
            hdr, text="Калькулятор Эрланга",
            font=("Segoe UI", 22, "bold italic"),
            fg=ACCENT2, bg=BG
        ).pack()
        tk.Label(
            hdr, text="Моносервисная модель  •  Первая формула Эрланга",
            font=("Segoe UI", 9),
            fg=TEXT_DIM, bg=BG
        ).pack()

        sep = tk.Frame(self, height=1, bg=BORDER)
        sep.pack(fill="x", padx=12)

        param_frame = tk.LabelFrame(
            self, text=" Параметры модели ", bg=BG, fg=ACCENT2,
            font=("Segoe UI", 10, "bold"),
            bd=1, relief="flat", highlightbackground=BORDER,
            highlightthickness=1
        )
        param_frame.pack(fill="x", padx=14, pady=(12, 4))

        self.chk_vars: dict[str, tk.BooleanVar] = {}
        self.entries:  dict[str, tk.Entry]       = {}
        self.row_hints: dict[str, tk.Label]       = {}

        for key, label, hint in PARAMS:
            var = tk.BooleanVar()
            self.chk_vars[key] = var
            var.trace_add("write", lambda *_, k=key: self._on_check(k))

            row = tk.Frame(param_frame, bg=BG2, bd=0)
            row.pack(fill="x", padx=6, pady=3)
            row.columnconfigure(1, weight=1)

            chk = tk.Checkbutton(
                row, variable=var, bg=BG2, fg=TEXT,
                activebackground=BG2, activeforeground=ACCENT2,
                selectcolor=BG3,
                font=("Segoe UI", 10), text=label,
                width=28, anchor="w",
                cursor="hand2"
            )
            chk.grid(row=0, column=0, sticky="w", padx=(8, 4), pady=4)

            ent = tk.Entry(
                row, font=("Consolas", 10), width=18,
                bg=BG3, fg=TEXT, insertbackground=ACCENT2,
                relief="flat", bd=4,
                disabledbackground=BG, disabledforeground=TEXT_DIM,
            )
            ent.insert(0, "0")
            ent.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=4)
            self.entries[key] = ent

            hint_lbl = tk.Label(
                row, text=hint, font=("Segoe UI", 8),
                fg=TEXT_DIM, bg=BG2, anchor="w"
            )
            hint_lbl.grid(row=1, column=1, sticky="w", padx=(0, 8))
            self.row_hints[key] = hint_lbl

        self.error_lbl = tk.Label(
            self, text="", font=("Segoe UI", 9),
            fg=RED, bg=BG, wraplength=430, justify="left"
        )
        self.error_lbl.pack(fill="x", padx=18, pady=(2, 0))

        self.hint_lbl = tk.Label(
            self,
            text="Выберите два известных параметра, введите значения и нажмите «Вычислить»",
            font=("Segoe UI", 9, "italic"),
            fg=ACCENT2, bg=BG, wraplength=430, justify="left"
        )
        self.hint_lbl.pack(fill="x", padx=18, pady=(4, 8))

        sep2 = tk.Frame(self, height=1, bg=BORDER)
        sep2.pack(fill="x", padx=12)

        btn_frame = tk.Frame(self, bg=BG, pady=10)
        btn_frame.pack(fill="x", padx=14)

        self.calc_btn = self._btn(btn_frame, "▶  Вычислить", self._calculate, ACCENT)
        self.calc_btn.pack(side="left", padx=(0, 6))

        self._btn(btn_frame, "⟳  Очистить поля", self._clear_fields, BG3).pack(side="left", padx=6)
        self._btn(btn_frame, "✕  Очистить историю", self._clear_history, BG3).pack(side="left", padx=6)

        self._btn(btn_frame, "⬇  Экспорт CSV", self._export_csv, BG3).pack(side="right", padx=(6, 0))

        sep3 = tk.Frame(self, height=1, bg=BORDER)
        sep3.pack(fill="x", padx=12)

        hist_outer = tk.Frame(self, bg=BG)
        hist_outer.pack(fill="both", expand=True, padx=14, pady=(10, 14))

        tk.Label(
            hist_outer, text="История вычислений",
            font=("Segoe UI", 10, "bold"),
            fg=TEXT, bg=BG
        ).pack(anchor="w")

        tbl_frame = tk.Frame(hist_outer, bg=BG)
        tbl_frame.pack(fill="both", expand=True, pady=(4, 0))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Erlang.Treeview",
            background=BG2, foreground=TEXT, rowheight=24,
            fieldbackground=BG2, borderwidth=0,
            font=("Consolas", 9)
        )
        style.configure(
            "Erlang.Treeview.Heading",
            background=BG3, foreground=ACCENT2,
            font=("Segoe UI", 9, "bold"), relief="flat"
        )
        style.map("Erlang.Treeview", background=[("selected", ACCENT)])

        cols = ("id", "v", "a", "p", "m", "время")
        self.tree = ttk.Treeview(
            tbl_frame, columns=cols, show="headings",
            height=10, style="Erlang.Treeview"
        )

        col_widths = {"id": 40, "v": 70, "a": 90, "p": 110, "m": 100, "время": 90}
        col_anchors = {"id": "center", "v": "center", "a": "center",
                       "p": "center", "m": "center", "время": "center"}
        for c in cols:
            self.tree.heading(c, text=c, command=lambda _c=c: self._sort_tree(_c, False))
            self.tree.column(c, width=col_widths[c], anchor=col_anchors[c])

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.tag_configure("odd",  background=BG2)
        self.tree.tag_configure("even", background=BG3)

        self.status_lbl = tk.Label(
            self, text="Готово",
            font=("Segoe UI", 8), fg=TEXT_DIM, bg=BG, anchor="w"
        )
        self.status_lbl.pack(fill="x", padx=14, pady=(0, 6))

        self.bind("<Return>", lambda e: self._calculate())
        self.bind("<Escape>", lambda e: self._clear_fields())

    def _btn(self, parent, text, cmd, color):
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=color, fg=TEXT, activebackground=ACCENT2, activeforeground=BG,
            font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, padx=12, pady=6,
            cursor="hand2"
        )
        b.bind("<Enter>", lambda e, b=b, c=color: b.configure(bg=ACCENT2, fg=BG))
        b.bind("<Leave>", lambda e, b=b, c=color: b.configure(bg=c, fg=TEXT))
        return b

    def _on_check(self, key):
        self._update_state()

    def _update_state(self):
        checked = [k for k, v in self.chk_vars.items() if v.get()]
        count = len(checked)

        for key in ("v", "a", "p", "m"):
            ent = self.entries[key]
            if key in checked:
                ent.configure(state="normal", bg=BG3)
            elif count >= 2:
                ent.configure(state="disabled", bg=BG)
            else:
                ent.configure(state="disabled", bg=BG)

        can_calc = (count == 2)
        self.calc_btn.configure(
            state="normal" if can_calc else "disabled",
            bg=ACCENT if can_calc else BG3
        )

        if count < 2:
            self.hint_lbl.configure(
                text=f"Выберите {2 - count} параметр(а) из четырёх доступных",
                fg=YELLOW
            )
        else:
            knames = {"v": "v", "a": "a", "p": "p", "m": "m"}
            sel = " и ".join(knames[k] for k in checked)
            self.hint_lbl.configure(
                text=f"Известны: {sel} → нажмите «Вычислить»",
                fg=GREEN
            )
        self.error_lbl.configure(text="")

    def _parse_float(self, s: str) -> float | None:
        s = s.strip().replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    def _parse_int(self, s: str) -> int | None:
        s = s.strip()
        try:
            val = float(s)
            if val == int(val):
                return int(val)
            return None
        except ValueError:
            return None

    def _calculate(self):
        checked = [k for k, v in self.chk_vars.items() if v.get()]
        if len(checked) != 2:
            return

        known = {}
        for key in checked:
            raw = self.entries[key].get()
            if key == "v":
                val = self._parse_int(raw)
                if val is None:
                    self._set_error(f"Число каналов v должно быть целым числом (введено: «{raw}»)")
                    return
                known["v"] = val
            else:
                val = self._parse_float(raw)
                if val is None:
                    self._set_error(f"Параметр «{key}» имеет некорректный формат (введено: «{raw}»)")
                    return
                known[key] = val

        err = validate_inputs(known)
        if err:
            self._set_error(err)
            return

        self.error_lbl.configure(text="")
        self.status_lbl.configure(text="⏳ Выполняется расчёт...", fg=YELLOW)
        self.update_idletasks()

        try:
            result = solve(known)
        except Exception as ex:
            self._set_error(f"Ошибка расчёта: {ex}")
            self.status_lbl.configure(text="Ошибка", fg=RED)
            return

        for key in ("v", "a", "p", "m"):
            ent = self.entries[key]
            was_disabled = key not in checked
            if was_disabled:
                ent.configure(state="normal", bg=BG3)
            ent.delete(0, "end")
            val = result[key]
            if key == "v":
                ent.insert(0, str(int(val)))
            else:
                ent.insert(0, f"{val:.8g}")
            if was_disabled:
                ent.configure(state="disabled", bg=BG2)

        self.op_id += 1
        ts = datetime.now().strftime("%H:%M:%S")
        row = {
            "id": self.op_id,
            "v": int(result["v"]),
            "a": round(result["a"], 8),
            "p": round(result["p"], 8),
            "m": round(result["m"], 8),
            "время": ts,
        }
        self.history.append(row)
        tag = "odd" if self.op_id % 2 else "even"
        self.tree.insert(
            "", "end",
            values=(row["id"], row["v"], f'{row["a"]:.6g}',
                    f'{row["p"]:.8f}', f'{row["m"]:.6g}', ts),
            tags=(tag,)
        )
        self.tree.yview_moveto(1)

        self.status_lbl.configure(
            text=f"✓ Расчёт №{self.op_id} выполнен  |  v={int(result['v'])}  "
                 f"a={result['a']:.4g}  p={result['p']:.6f}  m={result['m']:.4g}",
            fg=GREEN
        )

    def _set_error(self, msg: str):
        self.error_lbl.configure(text=f"⚠  {msg}")
        self.status_lbl.configure(text="Ошибка ввода", fg=RED)

    def _clear_fields(self):
        for key in ("v", "a", "p", "m"):
            self.chk_vars[key].set(False)
            ent = self.entries[key]
            ent.configure(state="normal", bg=BG3)
            ent.delete(0, "end")
            ent.insert(0, "0")
        self.error_lbl.configure(text="")
        self.status_lbl.configure(text="Поля очищены", fg=TEXT_DIM)
        self._update_state()

    def _clear_history(self):
        if not self.history:
            return
        if messagebox.askyesno("Очистить историю", "Удалить все записи истории вычислений?"):
            self.history.clear()
            self.op_id = 0
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.status_lbl.configure(text="История очищена", fg=TEXT_DIM)

    def _export_csv(self):
        if not self.history:
            messagebox.showinfo("Экспорт", "История вычислений пуста.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")],
            title="Сохранить историю вычислений"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "v", "a", "p", "m", "время"])
            writer.writeheader()
            writer.writerows(self.history)
        messagebox.showinfo("Экспорт", f"История сохранена:\n{path}")
        self.status_lbl.configure(text=f"Экспортировано {len(self.history)} записей", fg=GREEN)

    def _sort_tree(self, col: str, reverse: bool):
        """Сортировка таблицы истории по столбцу."""
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            items.sort(key=lambda t: float(t[0]) if t[0] else 0, reverse=reverse)
        except ValueError:
            items.sort(key=lambda t: t[0], reverse=reverse)
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)
            tag = "odd" if idx % 2 else "even"
            self.tree.item(k, tags=(tag,))
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))



if __name__ == "__main__":
    app = ErlangApp()
    app.mainloop()