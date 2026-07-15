# -*- coding: utf-8 -*-
"""환경설정 창 — 커스텀 팔레트(탭 + 블럭)와 기본 서식을 관리한다.

왼쪽: 탭 목록(추가/이름변경/삭제/순서). 오른쪽: 선택 탭의 블럭 목록
(문자/템플릿/기능 추가, 순서 이동, 칸수(span) 변경, 삭제) + 기본 서식 설정.

블럭 추가:
  문자   한글에서 복사한 문자/문구를 붙여넣거나 직접 입력 (1칸)
  템플릿 라이브러리에 저장된 템플릿 선택 (기본 2칸)
  기능   기능 목록에서 여러 개 체크 → 한 블럭이 병렬 실행 (굵게+자간+글씨체…)
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, colorchooser

import palette
import library
import func_catalog
import hwp_engine

BG = "#f5f5f7"
CARD = "#ffffff"
ACCENT = "#0071e3"
TEXT = "#1d1d1f"
MUTED = "#86868b"
BORDER = "#d2d2d7"
ROWBG = "#fafafa"
FONT = "맑은 고딕"

TYPE_LABEL = {"char": "문자", "template": "템플릿", "function": "기능"}


def _rgb_int(r, g, b):
    return r + (g << 8) + (b << 16)


# ───────────────────────── 기능 블럭 편집 대화상자 ─────────────────────────
class FunctionDialog(tk.Toplevel):
    """기능 목록에서 여러 개를 체크해 병렬 기능 블럭을 만든다."""

    def __init__(self, master, block=None):
        super().__init__(master)
        self.result = None
        self.title("기능 블럭")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        existing = {a["func"]: a.get("value") for a in (block or {}).get("actions", [])}
        name0 = (block or {}).get("name", "")

        tk.Label(self, text="기능 블럭 만들기", font=(FONT, 11, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(self, text="체크한 기능들이 이 블럭 하나에 병렬로 담깁니다.",
                 font=(FONT, 8), bg=BG, fg=MUTED).pack(anchor="w", padx=16, pady=(0, 8))

        namef = tk.Frame(self, bg=BG, padx=16)
        namef.pack(fill="x")
        tk.Label(namef, text="블럭 이름", font=(FONT, 9), bg=BG, fg=TEXT).pack(side="left")
        self.name_var = tk.StringVar(value=name0)
        tk.Entry(namef, textvariable=self.name_var, width=20, font=(FONT, 10),
                 relief="solid", bd=1).pack(side="left", padx=(8, 0))

        body = tk.Frame(self, bg=BG, padx=16, pady=8)
        body.pack(fill="x")
        self.rows = {}
        for f in func_catalog.FUNCTIONS:
            key = f["key"]
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x", pady=1)
            chk = tk.BooleanVar(value=key in existing)
            tk.Checkbutton(row, variable=chk, bg=BG, activebackground=BG,
                           selectcolor=CARD).pack(side="left")
            tk.Label(row, text=key, font=(FONT, 10), bg=BG, fg=TEXT,
                     width=8, anchor="w").pack(side="left")
            val_widget, val_var = self._value_widget(row, f, existing.get(key))
            tk.Label(row, text=f.get("hint", ""), font=(FONT, 7), bg=BG,
                     fg=MUTED).pack(side="left", padx=(6, 0))
            self.rows[key] = (chk, f, val_var, val_widget)

        foot = tk.Frame(self, bg=BG, padx=16, pady=12)
        foot.pack(fill="x")
        tk.Button(foot, text="저장", command=self._ok, font=(FONT, 10, "bold"),
                  bg=ACCENT, fg="white", bd=0, padx=16, pady=6,
                  cursor="hand2").pack(side="right")
        tk.Button(foot, text="취소", command=self.destroy, font=(FONT, 10),
                  bg="#e8e8ed", fg=TEXT, bd=0, padx=16, pady=6,
                  cursor="hand2").pack(side="right", padx=(0, 6))

        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()+40}+{master.winfo_rooty()+30}")
        self.grab_set()

    def _value_widget(self, parent, f, cur):
        kind = f["kind"]
        if kind in ("toggle", "para"):
            return None, None
        if kind == "font":
            var = tk.StringVar(value=cur or func_catalog.COMMON_FONTS[0])
            w = ttk.Combobox(parent, textvariable=var, width=12,
                             values=func_catalog.COMMON_FONTS, font=(FONT, 9))
            w.pack(side="left")
            return w, var
        if kind == "number":
            var = tk.StringVar(value="" if cur is None else str(cur))
            w = tk.Entry(parent, textvariable=var, width=6, font=(FONT, 9),
                         relief="solid", bd=1)
            w.pack(side="left")
            tk.Label(parent, text=f.get("unit", ""), font=(FONT, 8),
                     bg=BG, fg=MUTED).pack(side="left")
            return w, var
        if kind == "color":
            var = tk.StringVar(value="" if cur is None else str(cur))
            swatch = tk.Label(parent, text="  ", bg="#000000", relief="solid", bd=1)
            swatch.pack(side="left")

            def pick():
                rgb, _hex = colorchooser.askcolor(parent=self)
                if rgb:
                    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
                    var.set(str(_rgb_int(r, g, b)))
                    swatch.config(bg=_hex)
            tk.Button(parent, text="색 선택", command=pick, font=(FONT, 8),
                      bg=CARD, bd=1, cursor="hand2").pack(side="left", padx=(4, 0))
            return swatch, var
        return None, None

    def _ok(self):
        name = self.name_var.get().strip()
        actions = []
        for key, (chk, f, var, _w) in self.rows.items():
            if not chk.get():
                continue
            kind = f["kind"]
            if kind in ("toggle", "para"):
                actions.append({"func": key})
            elif kind == "number":
                raw = (var.get() or "").strip()
                if raw == "":
                    messagebox.showwarning("값 없음", f"'{key}' 값을 입력해주세요.", parent=self)
                    return
                try:
                    val = float(raw) if key == "글씨크기" else int(float(raw))
                except ValueError:
                    messagebox.showwarning("값 오류", f"'{key}' 값이 숫자가 아닙니다.", parent=self)
                    return
                actions.append({"func": key, "value": val})
            elif kind == "font":
                actions.append({"func": key, "value": var.get().strip()})
            elif kind == "color":
                if not var.get():
                    messagebox.showwarning("색 없음", "글자색을 선택해주세요.", parent=self)
                    return
                actions.append({"func": key, "value": int(var.get())})
        if not actions:
            messagebox.showwarning("기능 없음", "하나 이상 체크해주세요.", parent=self)
            return
        if not name:
            name = " + ".join(a["func"] for a in actions)[:16]
        self.result = {"type": "function", "name": name, "actions": actions, "span": 1}
        self.destroy()


# ───────────────────────── 환경설정 메인 창 ─────────────────────────
class SettingsWindow(tk.Toplevel):
    def __init__(self, master, on_saved=None):
        super().__init__(master)
        self.on_saved = on_saved
        self.title("환경설정 — 팔레트")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.attributes("-topmost", True)
        self.sel_tab = 0
        self.sel_block = None
        self._drag_from = None
        self._tile_map = {}

        tk.Label(self, text="환경설정", font=(FONT, 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(self, text="탭을 만들고, 그 안에 문자·템플릿·기능 블럭을 넣어 나만의 팔레트를 구성합니다.",
                 font=(FONT, 8), bg=BG, fg=MUTED).pack(anchor="w", padx=16, pady=(0, 8))

        main = tk.Frame(self, bg=BG, padx=16)
        main.pack(fill="both", expand=True)

        # 왼쪽: 탭 목록
        left = tk.Frame(main, bg=BG)
        left.pack(side="left", fill="y", padx=(0, 12))
        tk.Label(left, text="탭", font=(FONT, 9, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        self.tab_list = tk.Listbox(left, width=16, height=12, font=(FONT, 10),
                                   relief="solid", bd=1, exportselection=False,
                                   selectbackground=ACCENT, selectforeground="white")
        self.tab_list.pack()
        self.tab_list.bind("<<ListboxSelect>>", self._on_tab_select)
        tb = tk.Frame(left, bg=BG)
        tb.pack(fill="x", pady=4)
        for txt, cmd in [("+", self._add_tab), ("이름", self._rename_tab),
                         ("삭제", self._del_tab), ("▲", lambda: self._move_tab(-1)),
                         ("▼", lambda: self._move_tab(1))]:
            tk.Button(tb, text=txt, command=cmd, font=(FONT, 8), bg=CARD, fg=TEXT,
                      bd=1, padx=6, pady=2, cursor="hand2").pack(side="left", padx=1)

        # 오른쪽: 블럭 목록 + 추가
        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self.block_head = tk.Label(right, text="블럭", font=(FONT, 9, "bold"),
                                   bg=BG, fg=TEXT)
        self.block_head.pack(anchor="w")

        addbar = tk.Frame(right, bg=BG)
        addbar.pack(fill="x", pady=(2, 6))
        tk.Button(addbar, text="+ 문자", command=self._add_char, font=(FONT, 9),
                  bg="#e8e8ed", fg=TEXT, bd=0, padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=(0, 4))
        tk.Button(addbar, text="+ 템플릿", command=self._add_template, font=(FONT, 9),
                  bg="#e8e8ed", fg=TEXT, bd=0, padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=(0, 4))
        tk.Button(addbar, text="+ 기능", command=self._add_function, font=(FONT, 9),
                  bg="#e8e8ed", fg=TEXT, bd=0, padx=10, pady=5,
                  cursor="hand2").pack(side="left")

        self.block_area = tk.Frame(right, bg=BG)
        self.block_area.pack(fill="both", expand=True)

        # 기본 서식 버튼
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(8, 0))
        foot = tk.Frame(self, bg=BG, padx=16, pady=10)
        foot.pack(fill="x")
        tk.Button(foot, text="⚙ 기본 서식 설정", command=self._edit_default_format,
                  font=(FONT, 9), bg=CARD, fg=TEXT, bd=1, padx=10, pady=5,
                  cursor="hand2").pack(side="left")
        tk.Button(foot, text="닫기", command=self._close, font=(FONT, 10, "bold"),
                  bg=ACCENT, fg="white", bd=0, padx=16, pady=6,
                  cursor="hand2").pack(side="right")

        self._reload_tabs()
        self.update_idletasks()
        self.minsize(600, 520)
        self.geometry(f"640x560+{max(20, master.winfo_rootx()-660)}+{master.winfo_rooty()}")

    # ── 탭 목록 ──
    def _reload_tabs(self):
        self.tab_list.delete(0, tk.END)
        for t in palette.load_tabs():
            self.tab_list.insert(tk.END, t["name"])
        tabs = palette.load_tabs()
        if tabs:
            self.sel_tab = min(self.sel_tab, len(tabs) - 1)
            self.tab_list.selection_set(self.sel_tab)
        self._render_blocks()

    def _on_tab_select(self, e=None):
        sel = self.tab_list.curselection()
        if sel:
            self.sel_tab = sel[0]
            self._render_blocks()

    def _add_tab(self):
        name = simpledialog.askstring("탭 추가", "새 탭 이름:", parent=self)
        if name:
            palette.add_tab(name)
            self.sel_tab = len(palette.load_tabs()) - 1
            self._reload_tabs()
            self._notify()

    def _rename_tab(self):
        tabs = palette.load_tabs()
        if not tabs:
            return
        cur = tabs[self.sel_tab]["name"]
        name = simpledialog.askstring("이름 변경", "새 이름:", initialvalue=cur, parent=self)
        if name:
            try:
                palette.rename_tab(self.sel_tab, name)
            except ValueError as e:
                messagebox.showwarning("이름 충돌", str(e), parent=self)
                return
            self._reload_tabs()
            self._notify()

    def _del_tab(self):
        tabs = palette.load_tabs()
        if not tabs:
            return
        if messagebox.askyesno("삭제", f"'{tabs[self.sel_tab]['name']}' 탭을 삭제할까요?",
                               parent=self):
            palette.delete_tab(self.sel_tab)
            self.sel_tab = max(0, self.sel_tab - 1)
            self._reload_tabs()
            self._notify()

    def _move_tab(self, delta):
        palette.move_tab(self.sel_tab, delta)
        self.sel_tab = max(0, min(self.sel_tab + delta, len(palette.load_tabs()) - 1))
        self._reload_tabs()
        self._notify()

    # ── 블럭 그리드 (문자표처럼 격자 + 드래그로 자유 이동) ──
    def _render_blocks(self):
        for w in self.block_area.winfo_children():
            w.destroy()
        self._tile_map = {}
        tabs = palette.load_tabs()
        if not tabs:
            self.block_head.config(text="블럭")
            return
        tab = tabs[self.sel_tab]
        blocks = tab.get("blocks", [])
        cols = tab.get("cols", palette.DEFAULT_COLS)
        self.block_head.config(
            text=f"'{tab['name']}'  ·  블럭 {len(blocks)}개  ·  타일을 끌어 옮기고, 눌러 선택")

        # 상단 바: 칸 수 + 선택 블럭 동작
        bar = tk.Frame(self.block_area, bg=BG)
        bar.pack(fill="x", pady=(0, 6))
        tk.Label(bar, text="칸 수", font=(FONT, 8), bg=BG, fg=MUTED).pack(side="left")
        self._cols_var = tk.IntVar(value=cols)
        tk.Spinbox(bar, from_=1, to=10, width=3, textvariable=self._cols_var,
                   command=self._apply_cols, font=(FONT, 9)).pack(side="left", padx=(4, 14))
        tk.Button(bar, text="✎ 편집", font=(FONT, 8), bg=CARD, bd=1, padx=8, pady=2,
                  cursor="hand2", command=self._edit_selected).pack(side="left", padx=2)
        tk.Button(bar, text="◧ 1↔2칸", font=(FONT, 8), bg=CARD, bd=1, padx=8, pady=2,
                  cursor="hand2", command=self._span_selected).pack(side="left", padx=2)
        tk.Button(bar, text="삭제", font=(FONT, 8), bg="#e8e8ed", bd=0, padx=8, pady=2,
                  cursor="hand2", command=self._del_selected).pack(side="left", padx=2)

        if not blocks:
            tk.Label(self.block_area,
                     text="블럭이 없습니다. 위 ‘+ 문자 / + 템플릿 / + 기능’으로 추가한 뒤\n"
                          "타일을 끌어 원하는 자리에 놓으세요.",
                     font=(FONT, 9), bg=BG, fg=MUTED, justify="left").pack(anchor="w", pady=8)
            return

        grid = tk.Frame(self.block_area, bg=CARD, highlightbackground=BORDER,
                        highlightthickness=1)
        grid.pack(fill="both", expand=True, pady=(2, 0))
        for c in range(cols):
            grid.columnconfigure(c, weight=1, uniform="cell")
        r = c = 0
        for i, blk in enumerate(blocks):
            span = min(int(blk.get("span", 1)), cols)
            if c + span > cols:
                r += 1
                c = 0
            self._make_tile(grid, i, blk).grid(
                row=r, column=c, columnspan=span, sticky="nsew", padx=1, pady=1)
            c += span
            if c >= cols:
                r += 1
                c = 0

    def _apply_cols(self):
        palette.set_tab_cols(self.sel_tab, self._cols_var.get())
        self._render_blocks()
        self._notify()

    def _make_tile(self, parent, i, blk):
        selected = (self.sel_block == i)
        bg = {"char": CARD, "template": "#eef4ff", "function": "#fff4e6"}.get(
            blk["type"], CARD)
        tile = tk.Frame(parent, bg=bg, height=42,
                        highlightbackground=ACCENT if selected else BORDER,
                        highlightthickness=2 if selected else 1)
        tile.pack_propagate(False)
        lab = tk.Label(tile, text=self._tile_text(blk), bg=bg, fg=TEXT,
                       font=(FONT, 12 if blk["type"] == "char" else 9))
        lab.pack(expand=True)
        for w in (tile, lab):
            self._tile_map[str(w)] = i
            w.bind("<ButtonPress-1>", lambda e, idx=i: self._on_press(idx))
            w.bind("<ButtonRelease-1>", self._on_release)
            w.bind("<Double-Button-1>", lambda e, idx=i: self._edit_block(idx))
            w.config(cursor="hand2")
        return tile

    def _tile_text(self, blk):
        pre = {"template": "▦ ", "function": "ƒ "}.get(blk["type"], "")
        s = pre + self._block_label(blk)
        return s if len(s) <= 12 else s[:12] + "…"

    def _block_label(self, blk):
        if blk["type"] == "char":
            v = blk.get("value", "")
            return v if len(v) <= 20 else v[:20] + "…"
        if blk["type"] == "template":
            return blk.get("template", "?")
        return blk.get("name", " + ".join(a["func"] for a in blk.get("actions", [])))

    # ── 드래그 이동 + 선택 ──
    def _on_press(self, idx):
        self._drag_from = idx
        self.sel_block = idx           # 재렌더는 release에서 (드래그 중 위젯 파괴 방지)

    def _on_release(self, e):
        src = self._drag_from
        self._drag_from = None
        moved = False
        if src is not None:
            target = self._widget_to_index(self.winfo_containing(e.x_root, e.y_root))
            if target is not None and target != src:
                palette.move_block_to(self.sel_tab, src, target)
                self.sel_block = target
                moved = True
        self._render_blocks()          # 선택 표시 갱신
        if moved:
            self._notify()

    def _widget_to_index(self, w):
        seen = 0
        while w is not None and seen < 6:
            key = str(w)
            if key in self._tile_map:
                return self._tile_map[key]
            parent = w.winfo_parent()
            if not parent:
                break
            try:
                w = w.nametowidget(parent)
            except Exception:
                break
            seen += 1
        return None

    # ── 선택 블럭 동작 ──
    def _need_sel(self):
        if self.sel_block is None:
            messagebox.showinfo("선택 없음", "먼저 블럭을 눌러 선택하세요.", parent=self)
            return False
        blocks = palette.load_tabs()[self.sel_tab]["blocks"]
        if not (0 <= self.sel_block < len(blocks)):
            self.sel_block = None
            return False
        return True

    def _span_selected(self):
        if not self._need_sel():
            return
        blocks = palette.load_tabs()[self.sel_tab]["blocks"]
        blk = dict(blocks[self.sel_block])
        blk["span"] = 1 if blk.get("span", 1) == 2 else 2
        palette.update_block(self.sel_tab, self.sel_block, blk)
        self._render_blocks()
        self._notify()

    def _del_selected(self):
        if not self._need_sel():
            return
        palette.delete_block(self.sel_tab, self.sel_block)
        self.sel_block = None
        self._render_blocks()
        self._notify()

    def _edit_selected(self):
        if not self._need_sel():
            return
        self._edit_block(self.sel_block)

    def _edit_block(self, idx):
        self.sel_block = idx
        blocks = palette.load_tabs()[self.sel_tab]["blocks"]
        if not (0 <= idx < len(blocks)):
            return
        blk = dict(blocks[idx])
        if blk["type"] == "char":
            val = simpledialog.askstring("문자/문구 편집", "내용:",
                                         initialvalue=blk.get("value", ""), parent=self)
            if val is not None and val != "":
                blk["value"] = val
                palette.update_block(self.sel_tab, idx, blk)
        elif blk["type"] == "template":
            items = library.list_items("템플릿")
            if not items:
                return
            pick = _ChoiceDialog(self, "템플릿 변경", [it["name"] for it in items])
            self.wait_window(pick)
            if pick.result:
                blk["template"] = pick.result
                palette.update_block(self.sel_tab, idx, blk)
        else:  # function
            dlg = FunctionDialog(self, block=blk)
            self.wait_window(dlg)
            if dlg.result:
                dlg.result["span"] = blk.get("span", 1)
                palette.update_block(self.sel_tab, idx, dlg.result)
        self._render_blocks()
        self._notify()

    # ── 블럭 추가 ──
    def _need_tab(self):
        if not palette.load_tabs():
            messagebox.showwarning("탭 없음", "먼저 탭을 만들어주세요.", parent=self)
            return False
        return True

    def _add_char(self):
        if not self._need_tab():
            return
        prefill = ""
        try:
            hwp_engine.connect()
            if hwp_engine.has_selection():
                prefill = hwp_engine.read_selection_text(retries=6)
        except Exception:
            pass
        val = simpledialog.askstring(
            "문자/문구 블럭", "삽입할 문자나 문구 (한글에서 선택했다면 자동으로 채워집니다):",
            initialvalue=prefill, parent=self)
        if val:
            palette.add_block(self.sel_tab, {"type": "char", "value": val, "span": 1})
            self._render_blocks()
            self._notify()

    def _add_template(self):
        if not self._need_tab():
            return
        items = library.list_items("템플릿")
        if not items:
            messagebox.showinfo("템플릿 없음",
                "먼저 📚 라이브러리에서 템플릿을 등록해주세요.", parent=self)
            return
        names = [it["name"] for it in items]
        pick = _ChoiceDialog(self, "템플릿 선택", names)
        self.wait_window(pick)
        if pick.result:
            palette.add_block(self.sel_tab,
                              {"type": "template", "template": pick.result, "span": 2})
            self._render_blocks()
            self._notify()

    def _add_function(self):
        if not self._need_tab():
            return
        dlg = FunctionDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            palette.add_block(self.sel_tab, dlg.result)
            self._render_blocks()
            self._notify()

    # ── 기본 서식 ──
    def _edit_default_format(self):
        dlg = _DefaultFormatDialog(self)
        self.wait_window(dlg)
        self._notify()

    def _close(self):
        self._notify()
        self.destroy()

    def _notify(self):
        if self.on_saved:
            self.on_saved()


class _ChoiceDialog(tk.Toplevel):
    def __init__(self, master, title, options):
        super().__init__(master)
        self.result = None
        self.title(title)
        self.configure(bg=BG)
        self.attributes("-topmost", True)
        self.resizable(False, False)
        tk.Label(self, text=title, font=(FONT, 10, "bold"), bg=BG, fg=TEXT).pack(
            anchor="w", padx=16, pady=(12, 6))
        self.var = tk.StringVar(value=options[0])
        ttk.Combobox(self, textvariable=self.var, values=options, width=24,
                     state="readonly", font=(FONT, 10)).pack(padx=16)
        foot = tk.Frame(self, bg=BG, padx=16, pady=12)
        foot.pack(fill="x")
        tk.Button(foot, text="확인", command=self._ok, font=(FONT, 10, "bold"),
                  bg=ACCENT, fg="white", bd=0, padx=16, pady=6,
                  cursor="hand2").pack(side="right")
        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()+60}+{master.winfo_rooty()+60}")
        self.grab_set()

    def _ok(self):
        self.result = self.var.get()
        self.destroy()


class _DefaultFormatDialog(tk.Toplevel):
    """‘기본 서식으로 변환’이 적용할 기본 서식."""

    def __init__(self, master):
        super().__init__(master)
        self.title("기본 서식 설정")
        self.configure(bg=BG)
        self.attributes("-topmost", True)
        self.resizable(False, False)
        fmt = palette.get_default_format()

        tk.Label(self, text="기본 서식으로 변환 시 적용할 서식",
                 font=(FONT, 10, "bold"), bg=BG, fg=TEXT).pack(
                 anchor="w", padx=16, pady=(12, 8))
        body = tk.Frame(self, bg=BG, padx=16)
        body.pack(fill="x")

        self.font_var = tk.StringVar(value=fmt["font"])
        self.size_var = tk.StringVar(value=str(fmt["size_pt"]))
        self.ls_var = tk.StringVar(value=str(fmt["line_spacing"]))
        self.sp_var = tk.StringVar(value=str(fmt["spacing"]))

        rows = [("글꼴", ttk.Combobox(body, textvariable=self.font_var, width=16,
                                     values=func_catalog.COMMON_FONTS, font=(FONT, 9))),
                ("크기(pt)", tk.Entry(body, textvariable=self.size_var, width=8,
                                     font=(FONT, 9), relief="solid", bd=1)),
                ("줄간격(%)", tk.Entry(body, textvariable=self.ls_var, width=8,
                                     font=(FONT, 9), relief="solid", bd=1)),
                ("자간", tk.Entry(body, textvariable=self.sp_var, width=8,
                                font=(FONT, 9), relief="solid", bd=1))]
        for i, (lbl, w) in enumerate(rows):
            tk.Label(body, text=lbl, font=(FONT, 9), bg=BG, fg=TEXT).grid(
                row=i, column=0, sticky="w", pady=3)
            w.grid(row=i, column=1, sticky="w", padx=(8, 0), pady=3)

        foot = tk.Frame(self, bg=BG, padx=16, pady=12)
        foot.pack(fill="x")
        tk.Button(foot, text="저장", command=self._ok, font=(FONT, 10, "bold"),
                  bg=ACCENT, fg="white", bd=0, padx=16, pady=6,
                  cursor="hand2").pack(side="right")
        tk.Button(foot, text="취소", command=self.destroy, font=(FONT, 10),
                  bg="#e8e8ed", fg=TEXT, bd=0, padx=16, pady=6,
                  cursor="hand2").pack(side="right", padx=(0, 6))
        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()+50}+{master.winfo_rooty()+50}")
        self.grab_set()

    def _ok(self):
        try:
            fmt = {
                "font": self.font_var.get().strip() or "함초롬바탕",
                "size_pt": float(self.size_var.get()),
                "line_spacing": int(float(self.ls_var.get())),
                "spacing": int(float(self.sp_var.get())),
                "align": palette.get_default_format().get("align", 0),
            }
        except ValueError:
            messagebox.showwarning("값 오류", "크기·줄간격·자간은 숫자여야 합니다.", parent=self)
            return
        palette.save_default_format(fmt)
        self.destroy()


def open_settings(master, on_saved=None):
    return SettingsWindow(master, on_saved=on_saved)
