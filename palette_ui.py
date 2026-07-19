# -*- coding: utf-8 -*-
"""환경설정 창 — 커스텀 팔레트(탭 + 블럭)와 기본 서식을 관리한다.

왼쪽: 탭 목록(추가/이름변경/삭제/순서). 오른쪽: 선택 탭의 블럭 목록
(문자/템플릿/서식 조합 추가, 순서 이동, 칸수(span) 변경, 삭제) + 기본 서식 설정.

블럭 추가:
  문자   한글에서 복사한 문자/문구를 붙여넣거나 직접 입력 (1칸)
  템플릿 라이브러리에 저장된 템플릿 선택 (기본 2칸)
  서식 조합  목록에서 여러 개 체크 → 한 블럭이 병렬 실행 (굵게+자간+글씨체…)
             (라이브러리의 "서식"은 문서에서 캡처한 것, 이쪽은 직접 고르는 것)
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, colorchooser

import palette
import library
import func_catalog
import hwp_engine
import engine_library
import library_ui                  # commit_ime (IME 조합 확정) 공용

BG = "#f5f5f7"
CARD = "#ffffff"
ACCENT = "#0071e3"
TEXT = "#1d1d1f"
MUTED = "#86868b"
BORDER = "#d2d2d7"
ROWBG = "#fafafa"
FONT = "맑은 고딕"

TYPE_LABEL = {"char": "문자", "template": "템플릿", "function": "서식 조합",
              "form": "양식"}

# 글자 수 상한 (개선안 23 — 흩어져 있던 매직넘버에 이름을 붙임)
TILE_LABEL_MAX = 12      # 격자 미리보기 타일에 넣을 수 있는 글자 수
AUTO_NAME_MAX = 16       # 이름을 안 지었을 때 기능 이름들을 이어 붙이는 길이

# 격자 한 칸 — 메인 창(main._BLOCK_CELL_PX)과 같은 크기여야 미리보기가 실물과 맞는다
CELL_PX = 26
CELL_GAP = 2
EMPTY_BG = "#fbfbfd"     # 빈칸 배경
RANGE_BG = "#d8e9ff"     # 끌어서 지정 중인 범위


def _rgb_int(r, g, b):
    return r + (g << 8) + (b << 16)


# ───────────────────────── 기능 블럭 편집 대화상자 ─────────────────────────
class FunctionDialog(tk.Toplevel):
    """조작 목록에서 여러 개를 체크해 '서식 조합' 블럭을 만든다.

    저장 형식의 type 은 "function" 그대로다 — 표기만 바꾸고 개인 config.json 을
    건드리지 않기 위함 (개선안 10).
    """

    def __init__(self, master, block=None):
        super().__init__(master)
        self.result = None
        self.title("서식 조합 블럭")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        existing = {a["func"]: a.get("value") for a in (block or {}).get("actions", [])}
        name0 = (block or {}).get("name", "")

        tk.Label(self, text="서식 조합 블럭 만들기", font=(FONT, 11, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(self, text="체크한 것들이 이 블럭 하나에 병렬로 담깁니다. 글자를 선택하고 누르세요.",
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
            # 저장된 색(HWP는 R + G<<8 + B<<16)을 견본에 복원
            cur_hex = "#000000"
            if cur is not None:
                try:
                    v = int(cur)
                    cur_hex = "#%02x%02x%02x" % (v & 0xFF, (v >> 8) & 0xFF,
                                                 (v >> 16) & 0xFF)
                except (TypeError, ValueError):
                    pass
            swatch = tk.Label(parent, text="  ", bg=cur_hex, relief="solid", bd=1)
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
        # 한글 IME 로 조합 중인 마지막 글자를 확정시킨다 (library_ui.commit_ime 설명 참고)
        library_ui.commit_ime(self)
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
                    val = (float(raw) if key in func_catalog.FLOAT_KEYS
                           else int(float(raw)))
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
            messagebox.showwarning("선택 없음", "하나 이상 체크해주세요.", parent=self)
            return
        if not name:
            name = " + ".join(a["func"] for a in actions)[:AUTO_NAME_MAX]
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
        self._drop_hint = None
        self._tile_map = {}
        self._empty_map = {}
        self._used_cells = set()
        self._new_from = None      # 빈칸을 끌어 새 블럭 자리를 잡는 중
        self._new_to = None
        self._extra_rows = 0       # ＋줄 추가로 늘린 빈 줄 수

        tk.Label(self, text="환경설정", font=(FONT, 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(self, text="탭을 만들고, 그 안에 문자·템플릿·서식 조합 블럭을 넣어 나만의 팔레트를 구성합니다.",
                 font=(FONT, 8), bg=BG, fg=MUTED).pack(anchor="w", padx=16, pady=(0, 8))

        main = tk.Frame(self, bg=BG, padx=16)
        main.pack(fill="both", expand=True)

        # 왼쪽: 탭 목록
        left = tk.Frame(main, bg=BG)
        left.pack(side="left", fill="y", padx=(0, 12))
        tk.Label(left, text="탭", font=(FONT, 9, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        # height 는 줄 수. 크면 이쪽이 창 높이를 정해 버려서, 격자에 줄을 더해도
        # 창이 안 커진다(실측 2026-07-19: 왼쪽 272px > 오른쪽 180px). 작게 잡는다.
        self.tab_list = tk.Listbox(left, width=16, height=6, font=(FONT, 10),
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
        tk.Button(addbar, text="+ 서식 조합", command=self._add_function, font=(FONT, 9),
                  bg="#e8e8ed", fg=TEXT, bd=0, padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=(0, 4))
        tk.Button(addbar, text="+ 양식", command=self._add_form, font=(FONT, 9),
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
        self.minsize(600, 380)   # 높이는 내용에 맞춰 줄었다 늘었다 한다
        # 크기는 지정하지 않는다 — _fit_window 가 내용에 맞춰 잡는다(줄이 늘면 커짐)
        self.geometry(f"+{max(20, master.winfo_rootx()-660)}+{master.winfo_rooty()}")

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
        self._tiles = {}
        tabs = palette.load_tabs()
        if not tabs:
            self.block_head.config(text="블럭")
            return
        tab = tabs[self.sel_tab]
        blocks = tab.get("blocks", [])
        cols = tab.get("cols", palette.DEFAULT_COLS)
        self.block_head.config(
            text=f"'{tab['name']}'  ·  블럭 {len(blocks)}개  ·  "
                 f"빈칸을 끌어 칸 수를 정하면 새 블럭, 타일을 끌면 자리 이동")

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
            # 빈 격자라도 그린다 — 거기를 끌어 첫 블럭을 만들어야 하므로
            tk.Label(self.block_area,
                     text="빈칸을 누르거나 끌어서 첫 블럭을 만들어보세요.",
                     font=(FONT, 9), bg=BG, fg=MUTED,
                     justify="left").pack(anchor="w", pady=(0, 4))

        # 격자는 스크롤 없이 그대로 편다 — 줄이 늘면 창 자체가 커진다(_fit_window).
        wrap = tk.Frame(self.block_area, bg=CARD, highlightbackground=BORDER,
                        highlightthickness=1)
        wrap.pack(anchor="w", pady=(2, 0))
        grid = tk.Frame(wrap, bg=CARD, padx=2, pady=2)
        grid.pack(anchor="w")

        for c in range(cols):
            grid.columnconfigure(c, minsize=CELL_PX + CELL_GAP, weight=0,
                                 uniform="cell")

        # ① 블럭이 어느 칸을 차지하는지 먼저 계산 (메인 창과 같은 흐름 배치)
        layout, used = [], set()
        r = c = 0
        for i, blk in enumerate(blocks):
            span = min(int(blk.get("span", 1)), cols)
            if c + span > cols:
                r += 1
                c = 0
            layout.append((r, c, span, i))
            used.update((r, c + k) for k in range(span))
            c += span
            if c >= cols:
                r += 1
                c = 0
        self._used_cells = used
        last_row = max((rr for rr, *_ in layout), default=-1)

        # ② 블럭 타일 (고정 크기 틀에 넣어 글자 길이가 칸을 늘리지 못하게)
        for rr, cc, span, i in layout:
            cell = tk.Frame(grid, bg=CARD, height=CELL_PX,
                            width=CELL_PX * span + CELL_GAP * (span - 1))
            cell.pack_propagate(False)
            cell.grid(row=rr, column=cc, columnspan=span,
                      padx=CELL_GAP // 2, pady=CELL_GAP // 2)
            self._make_tile(cell, i, blocks[i], span).pack(fill="both", expand=True)

        # ③ 빈칸 — 여기를 끌어 칸 수를 정하면 새 블럭을 만든다.
        #    마지막 줄의 남은 칸 + '줄 추가'로 늘린 줄만큼 채운다.
        self._empty_map = {}
        total_rows = last_row + 1 + self._extra_rows
        if total_rows == 0:
            total_rows = 1                  # 블럭이 없어도 놓을 자리는 있어야 한다
        for rr in range(total_rows):
            for cc in range(cols):
                if (rr, cc) not in used:
                    self._make_empty_cell(grid, rr, cc)

        # 줄 추가 / 빼기 — 누르면 격자가 늘고 창도 그만큼 커진다
        rowbar = tk.Frame(self.block_area, bg=BG)
        rowbar.pack(anchor="w", pady=(6, 0))
        tk.Button(rowbar, text="＋ 줄 추가", command=self._add_row,
                  font=(FONT, 8), bg=CARD, fg=TEXT, bd=1, padx=10, pady=3,
                  cursor="hand2").pack(side="left")
        if self._extra_rows > 0:
            tk.Button(rowbar, text="－ 줄 빼기", command=self._remove_row,
                      font=(FONT, 8), bg=CARD, fg=MUTED, bd=1, padx=10, pady=3,
                      cursor="hand2").pack(side="left", padx=(4, 0))
        tk.Label(rowbar, text="빈 줄을 늘려 놓을 자리를 만듭니다",
                 font=(FONT, 8), bg=BG, fg=MUTED).pack(side="left", padx=(8, 0))

        self.after_idle(self._fit_window)

    def _apply_cols(self):
        palette.set_tab_cols(self.sel_tab, self._cols_var.get())
        self._render_blocks()
        self._notify()

    # ── 줄 늘리기/줄이기 + 창 크기 맞추기 ──
    def _add_row(self):
        self._extra_rows += 1
        self._render_blocks()

    def _remove_row(self):
        if self._extra_rows > 0:
            self._extra_rows -= 1
            self._render_blocks()

    def _fit_window(self):
        """내용에 맞춰 창 높이를 다시 잡는다 — 줄이 늘면 창도 커진다.

        주의 (실측 2026-07-19): 격자에 줄을 더한 직후의 winfo_reqheight() 는 한
        박자 늦은 값을 준다(격자는 이미 커졌는데 창의 요청 크기는 그대로). 그래서
        레이아웃이 정리된 뒤에 부르도록 호출부에서 after_idle 로 미루고, 여기서도
        한 번 더 update_idletasks() 한다.

        폭은 사용자가 늘려 둘 수 있으므로 줄이지 않는다.
        """
        self.update_idletasks()
        # geometry("") = "내용에 맞춰라". 크기를 직접 계산해 넣으면 그 순간의
        # winfo_reqheight() 가 한 박자 늦어서 첫 '줄 추가'가 반영되지 않았다(실측).
        self.geometry("")
        self.update_idletasks()

    # ── 빈칸: 끌어서 새 블럭 자리 지정 ──
    def _make_empty_cell(self, grid, r, c):
        f = tk.Frame(grid, bg=EMPTY_BG, width=CELL_PX, height=CELL_PX,
                     highlightbackground=BORDER, highlightthickness=1)
        f.pack_propagate(False)
        f.grid(row=r, column=c, padx=CELL_GAP // 2, pady=CELL_GAP // 2)
        self._empty_map[str(f)] = (r, c)
        f.bind("<ButtonPress-1>", lambda e, rc=(r, c): self._empty_press(rc))
        f.bind("<B1-Motion>", self._empty_motion)
        f.bind("<ButtonRelease-1>", self._empty_release)
        f.config(cursor="plus")
        return f

    def _empty_press(self, rc):
        if self._drag_from is not None:
            return                      # 타일을 옮기는 중 — 새 블럭 만들기가 아니다
        self._new_from = self._new_to = rc
        self._paint_range()

    def _empty_motion(self, e):
        if self._new_from is None:
            return
        w = e.widget.winfo_containing(e.x_root, e.y_root)
        rc = self._empty_map.get(str(w))
        # 같은 줄에서만 늘린다 (블럭은 줄을 넘어갈 수 없다)
        if rc and rc[0] == self._new_from[0]:
            self._new_to = rc
            self._paint_range()

    def _empty_release(self, e):
        if self._drag_from is not None:
            return self._on_release(e)  # 타일 옮기기는 기존 처리로
        if self._new_from is None:
            return
        r = self._new_from[0]
        c0, c1 = sorted((self._new_from[1], self._new_to[1]))
        self._new_from = self._new_to = None
        # 사이에 블럭이 끼어 있으면 거기서 끊는다
        span = 1
        while c0 + span <= c1 and (r, c0 + span) not in self._used_cells:
            span += 1
        self._render_blocks()           # 범위 표시 지우기
        self._pick_tool(span)

    def _paint_range(self):
        """지금 끌고 있는 범위를 칠한다."""
        r = self._new_from[0]
        c0, c1 = sorted((self._new_from[1], self._new_to[1]))
        for key, (rr, cc) in self._empty_map.items():
            try:
                w = self.nametowidget(key)
            except Exception:
                continue
            inside = (rr == r and c0 <= cc <= c1)
            w.config(bg=RANGE_BG if inside else EMPTY_BG)

    def _pick_tool(self, span):
        """칸 수를 정한 뒤 '무엇을 넣을지' 고른다."""
        dlg = _ToolPickDialog(self, span)
        self.wait_window(dlg)
        if dlg.result == "char":
            self._add_char(span)
        elif dlg.result == "template":
            self._add_template(span)
        elif dlg.result == "function":
            self._add_function(span)
        elif dlg.result == "form":
            self._add_form(span)

    def _make_tile(self, parent, i, blk, span=1):
        selected = (self.sel_block == i)
        bg = {"char": CARD, "template": "#eef4ff", "function": "#fff4e6",
              "form": "#eafaf1"}.get(blk["type"], CARD)
        tile = tk.Frame(parent, bg=bg,
                        highlightbackground=ACCENT if selected else BORDER,
                        highlightthickness=2 if selected else 1)
        tile.pack_propagate(False)
        lab = tk.Label(tile, text=self._tile_text(blk, span), bg=bg, fg=TEXT,
                       font=(FONT, 10 if blk["type"] == "char" else 8))
        lab.pack(expand=True)
        self._tiles[i] = tile
        for w in (tile, lab):
            self._tile_map[str(w)] = i
            w.bind("<ButtonPress-1>", lambda e, idx=i: self._on_press(idx))
            w.bind("<B1-Motion>", self._on_drag)
            w.bind("<ButtonRelease-1>", self._on_release)
            w.bind("<Double-Button-1>", lambda e, idx=i: self._edit_block(idx))
            w.config(cursor="hand2")
        return tile

    def _tile_text(self, blk, span=1):
        """칸 수에 맞춰 자른다 — 메인 창(main._make_block_button)과 같은 규칙."""
        name = self._block_label(blk)
        if span <= 1 and blk["type"] != "char":
            # 1칸엔 기호를 버리고 이름을 살린다 (종류는 배경색으로 구분)
            s, limit = name, 2
        else:
            pre = {"template": "▦ ", "function": "ƒ ", "form": "📄 "}.get(
                blk["type"], "")
            s, limit = pre + name, 2 if span <= 1 else span * 2
        return s if len(s) <= limit else s[:limit] + "…"

    def _block_label(self, blk):
        if blk["type"] == "char":
            v = blk.get("value", "")
            return v if len(v) <= 20 else v[:20] + "…"
        if blk["type"] in ("template", "form"):
            # 라이브러리의 '현재' 이름을 보여준다 (이름을 바꿔도 따라가게)
            cat = "양식" if blk["type"] == "form" else "템플릿"
            key = "form" if blk["type"] == "form" else "template"
            it = library.get_item(cat, item_id=blk.get("ref"),
                                  name=blk.get(key))
            if it:
                return it["name"]
            return f"{blk.get(key, '?')} (삭제됨)"
        return blk.get("name", " + ".join(a["func"] for a in blk.get("actions", [])))

    # ── 드래그 이동 + 선택 ──
    def _set_selection(self, idx):
        """선택 표시를 '재렌더 없이' 그 자리에서 갱신.

        release마다 _render_blocks()로 다시 그리면 타일 위젯이 파괴돼,
        뒤이어 와야 할 <Double-Button-1>(수정)이 도달하지 못한다(실측 버그).
        그래서 선택은 위젯 config만 바꾼다.
        """
        self.sel_block = idx
        for i, tile in getattr(self, "_tiles", {}).items():
            sel = (i == idx)
            try:
                tile.config(highlightbackground=ACCENT if sel else BORDER,
                            highlightthickness=2 if sel else 1)
            except Exception:
                pass

    def _on_press(self, idx):
        self._drag_from = idx
        self._set_selection(idx)

    def _on_drag(self, e):
        """드래그 중 — 지금 놓으면 어디로 갈지 타일에 표시."""
        if self._drag_from is None:
            return
        under = self.winfo_containing(e.x_root, e.y_root)
        target = self._widget_to_index(under)
        if target is None and self._is_empty_cell(under):
            target = -1                      # 빈칸에 놓으면 맨 뒤로
        if target == self._drop_hint:
            return
        self._drop_hint = target
        # 후보 타일만 강조 (원본은 선택색 유지)
        for i, tile in getattr(self, "_tiles", {}).items():
            try:
                if i == target and i != self._drag_from:
                    tile.config(highlightbackground="#34c759", highlightthickness=3)
                elif i == self.sel_block:
                    tile.config(highlightbackground=ACCENT, highlightthickness=2)
                else:
                    tile.config(highlightbackground=BORDER, highlightthickness=1)
            except Exception:
                pass
        # 빈칸은 강조하지 않는다 — 어디에 놓든 "맨 뒤"라 표시가 오히려 헷갈린다

    def _on_release(self, e):
        src = self._drag_from
        self._drag_from = None
        self._drop_hint = None
        if src is None:
            return
        under = self.winfo_containing(e.x_root, e.y_root)
        target = self._widget_to_index(under)
        if target is None and self._is_empty_cell(under):
            # 빈칸에 놓으면 맨 뒤로 보낸다
            target = len(palette.load_tabs()[self.sel_tab]["blocks"]) - 1
        if target is not None and target != src:
            # 실제로 옮겼을 때만 재렌더 (더블클릭 경로를 막지 않기 위해)
            palette.move_block_to(self.sel_tab, src, target)
            self.sel_block = target
            self._render_blocks()
            self._notify()

    def _is_empty_cell(self, widget):
        """그 위젯이 빈칸인가 (타일을 여기 놓으면 맨 뒤로 보낸다)."""
        w = widget
        for _ in range(4):
            if w is None:
                return False
            if str(w) in getattr(self, "_empty_map", {}):
                return True
            w = getattr(w, "master", None)
        return False

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
                it = next(x for x in items if x["name"] == pick.result)
                blk["ref"] = it["id"]
                blk["template"] = it["name"]
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

    def _add_char(self, span=1):
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
            palette.add_block(self.sel_tab,
                              {"type": "char", "value": val, "span": span})
            self._render_blocks()
            self._notify()

    def _add_template(self, span=2):
        """템플릿 블럭 추가 — 지금 한글에서 바로 캡처하거나, 등록된 것에서 고른다."""
        if not self._need_tab():
            return
        items = library.list_items("템플릿")
        choice = _SourceDialog(self, has_registered=bool(items))
        self.wait_window(choice)
        if choice.result == "capture":
            self._capture_template_here(span)
        elif choice.result == "registered":
            pick = _ChoiceDialog(self, "템플릿 선택", [it["name"] for it in items])
            self.wait_window(pick)
            if pick.result:
                it = next(x for x in items if x["name"] == pick.result)
                self._add_template_block(it, span)

    def _capture_template_here(self, span=2):
        """한글의 현재 선택(또는 커서가 든 표)을 그 자리에서 템플릿으로 등록 + 배치."""
        try:
            hwp_engine.connect()
        except Exception as e:
            messagebox.showerror("연결 실패", f"한글을 먼저 실행해주세요.\n{e}", parent=self)
            return
        if not hwp_engine.has_selection():
            if not engine_library.auto_select_table_if_inside():
                messagebox.showwarning("선택 없음",
                    "한글에서 템플릿으로 저장할 영역을 드래그로 선택하거나,\n"
                    "표를 저장하려면 표 안을 클릭만 해둬도 됩니다.", parent=self)
                return
        captured = hwp_engine.read_selection_text(retries=6)
        slot_count = captured.count("\\")
        if slot_count:
            note = (f"빈칸(\\) {slot_count}개 발견 — 변환 시 아랫줄 {slot_count}줄이"
                    " 순서대로 채워집니다. (비울 칸엔 '-')")
        elif "/" in captured:
            note = ("⚠ 빈칸이 없습니다. 혹시 슬래시(/)를 쓰셨나요?\n"
                    "   빈칸은 역슬래시(\\) — 한글에서 ₩ 로 보이는 그 키입니다.")
        else:
            note = "빈칸(\\)이 없습니다. 글자 들어갈 자리에 \\ 를 넣어두면 채울 수 있습니다."

        meta = MetaDialog(self, title="템플릿 등록", extra_note=note)
        self.wait_window(meta)
        if not meta.result:
            return
        name, label, group = meta.result
        library.FRAGMENTS_DIR.mkdir(exist_ok=True)
        tmp = library.FRAGMENTS_DIR / f"_tmp_{int(time.time()*1000)}.hwp"
        try:
            engine_library.capture_fragment(tmp)
            item_id = library.add_template_from_capture(
                name, tmp, label=label, group=group, slot_count=slot_count)
        except Exception as e:
            messagebox.showerror("캡처 실패", str(e), parent=self)
            return
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        self._add_template_block(library.find_by_id("템플릿", item_id), span)

    def _add_template_block(self, item, span=2):
        if not item:
            return
        palette.add_block(self.sel_tab, {"type": "template", "ref": item["id"],
                                         "template": item["name"], "span": span})
        self._render_blocks()
        self._notify()

    def _add_function(self, span=1):
        if not self._need_tab():
            return
        dlg = FunctionDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            dlg.result["span"] = span
            palette.add_block(self.sel_tab, dlg.result)
            self._render_blocks()
            self._notify()

    def _add_form(self, span=2):
        """양식 블럭 추가 — 라이브러리에 등록된 양식에서 고른다."""
        if not self._need_tab():
            return
        items = library.list_items("양식")
        if not items:
            messagebox.showinfo(
                "양식 없음",
                "먼저 📚 라이브러리 → 양식 탭에서 hwp 파일을 등록해주세요.\n\n"
                "양식은 '새 문서로 열기'용입니다 (표지·통신문처럼\n"
                "용지·여백·머리말까지 그대로 시작할 때).", parent=self)
            return
        pick = _ChoiceDialog(self, "양식 선택", [it["name"] for it in items])
        self.wait_window(pick)
        if pick.result:
            it = next(x for x in items if x["name"] == pick.result)
            palette.add_block(self.sel_tab, {"type": "form", "ref": it["id"],
                                             "form": it["name"], "span": span})
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


class _SourceDialog(tk.Toplevel):
    """템플릿 블럭을 어디서 가져올지 — 지금 캡처 vs 이미 등록된 것."""

    def __init__(self, master, has_registered=True):
        super().__init__(master)
        self.result = None
        self.title("템플릿 추가")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        tk.Label(self, text="템플릿을 어디서 가져올까요?", font=(FONT, 11, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 8))

        body = tk.Frame(self, bg=BG, padx=16)
        body.pack(fill="x")
        tk.Button(body, text="📸  지금 한글에서 캡처해서 추가",
                  command=lambda: self._pick("capture"),
                  font=(FONT, 10, "bold"), bg=ACCENT, fg="white", bd=0,
                  pady=10, cursor="hand2").pack(fill="x")
        tk.Label(body, text="한글에서 표·영역을 선택해두고 누르세요. 등록과 배치가 한 번에.",
                 font=(FONT, 8), bg=BG, fg=MUTED).pack(anchor="w", pady=(3, 10))

        state = "normal" if has_registered else "disabled"
        tk.Button(body, text="📚  이미 등록된 템플릿에서 고르기",
                  command=lambda: self._pick("registered"),
                  font=(FONT, 10), bg=CARD, fg=TEXT, bd=1, pady=8,
                  cursor="hand2", state=state).pack(fill="x")
        if not has_registered:
            tk.Label(body, text="(아직 등록된 템플릿이 없습니다)",
                     font=(FONT, 8), bg=BG, fg=MUTED).pack(anchor="w", pady=(3, 0))

        tk.Button(self, text="취소", command=self.destroy, font=(FONT, 9),
                  bg=BG, fg=MUTED, bd=0, cursor="hand2").pack(pady=10)

        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()+50}+{master.winfo_rooty()+50}")
        self.grab_set()

    def _pick(self, what):
        self.result = what
        self.destroy()


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


class _ToolPickDialog(tk.Toplevel):
    """빈칸을 끌어 칸 수를 정한 뒤 '무엇을 넣을지' 고르는 창."""

    _TOOLS = [
        ("char", "문자", "특수문자·자주 쓰는 문구를 커서 자리에 삽입"),
        ("template", "템플릿", "표·결재란 등 문서 일부를 커서 자리에 꽂기"),
        ("function", "서식 조합", "선택한 글자에 굵게·크기·자간 등을 한 번에"),
        ("form", "양식", "hwp 파일 전체를 새 문서로 열기"),
    ]

    def __init__(self, master, span):
        super().__init__(master)
        self.result = None
        self.title("어떤 도구를 넣을까요?")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        tk.Label(self, text=f"{span}칸짜리 자리에 넣을 도구",
                 font=(FONT, 11, "bold"), bg=BG, fg=TEXT).pack(
            anchor="w", padx=16, pady=(12, 2))
        tk.Label(self, text="고르면 그 도구를 만드는 창이 이어서 열립니다.",
                 font=(FONT, 8), bg=BG, fg=MUTED).pack(anchor="w", padx=16,
                                                       pady=(0, 8))

        body = tk.Frame(self, bg=BG, padx=16)
        body.pack(fill="x")
        for key, name, desc in self._TOOLS:
            row = tk.Button(body, bg=CARD, bd=1, relief="solid", cursor="hand2",
                            anchor="w", justify="left", padx=10, pady=6,
                            text=f"{name}\n{desc}", font=(FONT, 9),
                            fg=TEXT, activebackground=BORDER,
                            command=lambda k=key: self._pick(k))
            row.pack(fill="x", pady=2)

        tk.Button(self, text="취소", command=self.destroy, font=(FONT, 9),
                  bg="#e8e8ed", fg=TEXT, bd=0, padx=14, pady=5,
                  cursor="hand2").pack(anchor="e", padx=16, pady=12)

        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()+60}+{master.winfo_rooty()+80}")
        self.grab_set()

    def _pick(self, key):
        self.result = key
        self.destroy()


def open_settings(master, on_saved=None):
    return SettingsWindow(master, on_saved=on_saved)
