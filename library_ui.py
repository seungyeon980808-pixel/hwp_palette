# -*- coding: utf-8 -*-
"""개인 라이브러리 관리 창 (Toplevel) — 서식 / 문자 / 템플릿 3탭.

각 탭은 독립적으로 "+추가"가 가능하다.
- 서식: 한글에서 원하는 모양으로 글자를 선택해두고 [+ 캡처해서 추가] →
  체크한 항목만 델타로 저장. 이후 [적용]은 선택 영역에 그 항목만 입힌다.
- 문자: 문구를 직접 입력(또는 한글 선택 영역에서 자동 채움)해 이름 붙여 저장.
  [삽입]으로 커서 위치에 그대로 삽입.
- 템플릿: 한글에서 표·결재란 등 영역을 선택해두고 [+ 선택 영역을 템플릿으로
  저장] → 통째로 조각 .hwp 파일로 보관. [삽입]으로 커서 위치에 그대로 삽입.
"""

import pathlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import applog
import hwp_engine
import engine_library
import library
import builtin_chars

BG = "#f5f5f7"
CARD = "#ffffff"
ACCENT = "#0071e3"
TEXT = "#1d1d1f"
MUTED = "#86868b"
BORDER = "#d2d2d7"
ROWBG = "#fafafa"
FONT = "맑은 고딕"

TAB_DESC = {
    "서식": "문서에서 캡처한 글자 모양(굵기·색상·자간 등) 일부만 저장해 "
            "아무 글자에나 입히는 기능 "
            "— 팔레트의 '서식 조합'은 캡처 대신 목록에서 직접 고르는 쪽",
    "문자": "특수문자나 자주 쓰는 문구를 저장해 바로 삽입하는 기능",
    "템플릿": "표·결재란처럼 문서 '일부'를 저장해 커서 자리에 꽂아 넣는 기능",
    "양식": "hwp 파일 '전체'를 저장해 새 문서로 여는 기능 "
            "(용지·여백·머리말까지 그대로 — 표지·통신문용)",
    "내장": "등록 없이 바로 쓰는 기본 기호. 문서에 \\원1\\ \\로마3\\ \\홑낫표\\ 로 호출",
}

TABS = ("서식", "문자", "템플릿", "양식", "내장")

# 글자 수 상한 (개선안 23 — 흩어져 있던 매직넘버에 이름을 붙임)
ROW_PREVIEW_MAX = 16     # 목록 행에 보여줄 내용 미리보기 길이
AUTO_NAME_MAX = 10       # 문자 등록 시 내용에서 이름을 자동으로 뽑는 길이


def commit_ime(window):
    r"""한글 IME 로 조합 중인 글자를 확정시킨다. 값을 읽기 **직전에** 부른다.

    '기본문'을 치는 도중 마지막 '문'은 IME 가 화면에만 그리고 있을 뿐, 위젯에는
    아직 안 들어와 있다(실측 2026-07-19 — 위젯에 실제로 들어간 글자는 즉시
    변수에 반영되는 것을 확인했으므로, 코드 순서 문제가 아니라 IME 조합 때문).
    그 상태에서 값을 읽으면 '기본'만 저장된다.

    포커스를 옮기면 조합이 확정되므로 한 번 옮겨 주고, 반영될 때까지 기다린다.
    """
    try:
        window.focus_set()              # 입력칸 → 창 자체로 포커스 이동
        window.update_idletasks()       # 확정 결과가 변수에 반영될 때까지
    except Exception as e:
        applog.exc("IME 조합 확정 실패 — 마지막 글자가 빠질 수 있음", e)


def _ensure_hwp(parent):
    try:
        hwp_engine.connect()
        return True
    except Exception as e:
        messagebox.showerror("연결 실패", f"한글을 먼저 실행해주세요.\n{e}", parent=parent)
        return False


class StyleFieldDialog(tk.Toplevel):
    """서식 캡처 시 '체크한 항목만' 담기 위한 체크리스트."""

    def __init__(self, master):
        super().__init__(master)
        self.result = None
        self.title("캡처할 항목 선택")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        tk.Label(self, text="선택 영역에서 어떤 항목을 저장할까요?",
                 font=(FONT, 10, "bold"), bg=BG, fg=TEXT).pack(
                 anchor="w", padx=16, pady=(14, 2))
        tk.Label(self, text="체크한 항목만 저장돼, 나중에 그 항목만 다른 글자에 입혀집니다.",
                 font=(FONT, 8), bg=BG, fg=MUTED).pack(anchor="w", padx=16, pady=(0, 10))

        self.vars = {}
        body = tk.Frame(self, bg=BG, padx=16)
        body.pack(fill="x")
        for label in engine_library.CHARSHAPE_FIELD_LABELS:
            v = tk.BooleanVar(value=False)
            self.vars[label] = v
            tk.Checkbutton(body, text=label, variable=v, font=(FONT, 10),
                           bg=BG, fg=TEXT, activebackground=BG,
                           selectcolor=CARD, cursor="hand2").pack(anchor="w", pady=2)

        foot = tk.Frame(self, bg=BG, padx=16, pady=14)
        foot.pack(fill="x")
        tk.Button(foot, text="다음", command=self._ok,
                  font=(FONT, 10, "bold"), bg=ACCENT, fg="white", bd=0,
                  padx=16, pady=6, cursor="hand2").pack(side="right")
        tk.Button(foot, text="취소", command=self.destroy,
                  font=(FONT, 10), bg="#e8e8ed", fg=TEXT, bd=0,
                  padx=16, pady=6, cursor="hand2").pack(side="right", padx=(0, 6))

        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()+40}+{master.winfo_rooty()+40}")
        self.grab_set()

    def _ok(self):
        checked = [k for k, v in self.vars.items() if v.get()]
        if not checked:
            messagebox.showwarning("선택 없음", "하나 이상 체크해주세요.", parent=self)
            return
        self.result = checked
        self.destroy()


class MetaDialog(tk.Toplevel):
    """이름 / 마크다운 라벨 / 분류를 한 창에서 입력."""

    def __init__(self, master, title="등록 정보", name="", label="", extra_note="",
                 exclude_id=None):
        super().__init__(master)
        self.result = None
        self.exclude_id = exclude_id        # 수정 중인 자기 자신은 충돌에서 제외
        self.title(title)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        body = tk.Frame(self, bg=BG, padx=16, pady=12)
        body.pack(fill="x")

        # ── 이름만 물어본다. 라벨·분류는 대부분 기본값이면 충분하므로 접어둠 ──
        tk.Label(body, text="이름", font=(FONT, 9), bg=BG, fg=TEXT).grid(
            row=0, column=0, sticky="w", pady=3)
        self.name_var = tk.StringVar(value=name)
        name_entry = tk.Entry(body, textvariable=self.name_var, width=26,
                              font=(FONT, 10), relief="solid", bd=1)
        name_entry.grid(row=0, column=1, pady=3, padx=(8, 0))
        name_entry.focus_set()
        name_entry.bind("<Return>", lambda e: self._ok())
        self.name_entry = name_entry
        # 한글 IME 로 조합 중인 글자는 아직 위젯에 안 들어와 있어서 미리보기가
        # 한 글자 뒤처져 보인다(실측). 조합이 끝나는 순간을 잡으려고 키를 뗄 때와
        # 포커스가 빠질 때도 다시 그린다.
        name_entry.bind("<KeyRelease>", lambda e: self._update_preview())
        name_entry.bind("<FocusOut>", lambda e: self._update_preview())

        self.label_var = tk.StringVar(value=label)
        self.group_var = tk.StringVar(value=library.DEFAULT_GROUP)
        self._preview = tk.Label(body, text="", font=(FONT, 8), bg=BG, fg=ACCENT)
        self._preview.grid(row=1, column=1, sticky="w", padx=(8, 0))
        self.name_var.trace_add("write", lambda *a: self._update_preview())
        self.label_var.trace_add("write", lambda *a: self._update_preview())

        if extra_note:
            tk.Label(body, text=extra_note, font=(FONT, 8), bg=BG, fg=MUTED,
                     wraplength=320, justify="left").grid(
                row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # ── 자세히 (라벨·분류) — 필요할 때만 펼침 ──
        self._adv_open = False
        self._adv = tk.Frame(self, bg=BG, padx=16)
        tk.Label(self._adv, text="마크다운 라벨", font=(FONT, 9), bg=BG,
                 fg=TEXT).grid(row=0, column=0, sticky="w", pady=3)
        tk.Entry(self._adv, textvariable=self.label_var, width=24,
                 font=(FONT, 10), relief="solid", bd=1).grid(
            row=0, column=1, pady=3, padx=(8, 0))
        tk.Label(self._adv, text="비우면 이름을 그대로 씁니다.",
                 font=(FONT, 7), bg=BG, fg=MUTED).grid(
            row=1, column=1, sticky="w", padx=(8, 0))
        tk.Label(self._adv, text="분류", font=(FONT, 9), bg=BG, fg=TEXT).grid(
            row=2, column=0, sticky="w", pady=3)
        ttk.Combobox(self._adv, textvariable=self.group_var, width=21,
                     values=library.list_groups(), font=(FONT, 10)).grid(
            row=2, column=1, pady=3, padx=(8, 0))

        self._adv_btn = tk.Button(self, text="▸ 자세히 (라벨·분류)",
                                  command=self._toggle_adv, font=(FONT, 8),
                                  fg=MUTED, bg=BG, activebackground=BG,
                                  bd=0, cursor="hand2", anchor="w")
        self._adv_btn.pack(fill="x", padx=16)

        foot = tk.Frame(self, bg=BG, padx=16, pady=12)
        foot.pack(fill="x")
        tk.Button(foot, text="저장", command=self._ok,
                  font=(FONT, 10, "bold"), bg=ACCENT, fg="white", bd=0,
                  padx=16, pady=6, cursor="hand2").pack(side="right")
        tk.Button(foot, text="취소", command=self.destroy,
                  font=(FONT, 10), bg="#e8e8ed", fg=TEXT, bd=0,
                  padx=16, pady=6, cursor="hand2").pack(side="right", padx=(0, 6))

        self._update_preview()
        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()+40}+{master.winfo_rooty()+60}")
        self.grab_set()

    def _toggle_adv(self):
        if self._adv_open:
            self._adv.pack_forget()
            self._adv_btn.config(text="▸ 자세히 (라벨·분류)")
        else:
            self._adv.pack(fill="x", before=self._adv_btn)
            self._adv_btn.config(text="▾ 자세히 (라벨·분류)")
        self._adv_open = not self._adv_open

    def _update_preview(self):
        """문서에 어떻게 쓰는지 실물로 보여준다 (\\ 헷갈림 방지)."""
        lab = library.normalize_label(self.label_var.get()) \
            or library.normalize_label(self.name_var.get())
        self._preview.config(text=f"문서에 이렇게 쓰세요:  \\{lab}\\" if lab else "")

    def _ok(self):
        commit_ime(self)
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("이름 없음", "이름을 입력해주세요.", parent=self)
            return
        label = self.label_var.get().strip() or name
        if not self._confirm_label(label):
            return
        self.result = (name, label,
                       self.group_var.get().strip() or library.DEFAULT_GROUP)
        self.destroy()

    def _confirm_label(self, label):
        r"""라벨이 이미 쓰이고 있으면 물어본다. 계속할지 여부를 반환.

        막지는 않는다 — 팔레트 버튼으로만 쓸 거라면 라벨이 겹쳐도 상관없다.
        다만 \라벨\ 로는 호출되지 않는다는 사실을 알고 넘어가야 한다.
        """
        owner = library.find_label_owner(label, exclude_id=self.exclude_id)
        if owner is None:
            return True
        cat, item = owner
        return messagebox.askyesno(
            "라벨이 겹칩니다",
            f"\\{library.normalize_label(label)}\\ 은(는) 이미 "
            f"[{cat}] '{item.get('name')}' 이(가) 쓰고 있습니다.\n\n"
            "이대로 저장하면 이 항목은 팔레트 버튼으로는 동작하지만,\n"
            "마크다운 변환에서는 호출되지 않습니다.\n\n"
            "그래도 저장할까요?  (아니오 = 라벨을 고치러 돌아가기)",
            parent=self)


class TextInputDialog(tk.Toplevel):
    """문자/문구 등록 입력창."""

    def __init__(self, master, prefill=""):
        super().__init__(master)
        self.result = None
        self.title("문자/문구 내용")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        tk.Label(self, text="저장할 내용을 입력하세요 (한글에서 선택했다면 자동으로 채워집니다)",
                 font=(FONT, 9), bg=BG, fg=MUTED, justify="left").pack(
                 anchor="w", padx=16, pady=(14, 6))

        self.text = tk.Text(self, width=44, height=5, font=(FONT, 10),
                             wrap="word", relief="solid", bd=1)
        self.text.pack(padx=16)
        self.text.insert("1.0", prefill)

        foot = tk.Frame(self, bg=BG, padx=16, pady=14)
        foot.pack(fill="x")
        tk.Button(foot, text="다음", command=self._ok,
                  font=(FONT, 10, "bold"), bg=ACCENT, fg="white", bd=0,
                  padx=16, pady=6, cursor="hand2").pack(side="right")
        tk.Button(foot, text="취소", command=self.destroy,
                  font=(FONT, 10), bg="#e8e8ed", fg=TEXT, bd=0,
                  padx=16, pady=6, cursor="hand2").pack(side="right", padx=(0, 6))

        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()+40}+{master.winfo_rooty()+40}")
        self.grab_set()

    def _ok(self):
        commit_ime(self)                # 조합 중인 마지막 글자가 빠지지 않게
        self.result = self.text.get("1.0", "end-1c")
        self.destroy()


class LibraryManager(tk.Toplevel):
    def __init__(self, master, on_saved=None):
        super().__init__(master)
        self.on_saved = on_saved
        self.title("내 라이브러리")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.current_cat = "서식"

        tk.Label(self, text="내 라이브러리", font=(FONT, 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 2))

        # 탭 버튼
        tab_row = tk.Frame(self, bg=BG, padx=16)
        tab_row.pack(fill="x", pady=(4, 0))
        self.tab_btns = {}
        for cat in TABS:
            b = tk.Button(tab_row, text=cat, font=(FONT, 10, "bold"),
                          bd=0, padx=14, pady=8, cursor="hand2",
                          command=lambda c=cat: self._switch_tab(c))
            b.pack(side="left", padx=(0, 4))
            self.tab_btns[cat] = b

        self.desc_label = tk.Label(self, font=(FONT, 8), bg=BG, fg=MUTED,
                                    justify="left", wraplength=420)
        self.desc_label.pack(anchor="w", padx=16, pady=(6, 8))

        # 검색 + 분류 필터
        filter_row = tk.Frame(self, bg=BG, padx=16)
        filter_row.pack(fill="x")
        tk.Label(filter_row, text="검색", font=(FONT, 8), fg=MUTED, bg=BG).pack(side="left")
        self.search_var = tk.StringVar(value="")
        se = tk.Entry(filter_row, textvariable=self.search_var, width=14,
                      font=(FONT, 9), relief="solid", bd=1)
        se.pack(side="left", padx=(6, 12))
        self.search_var.trace_add("write", lambda *a: self._refresh())
        self.group_lbl = tk.Label(filter_row, text="분류", font=(FONT, 8),
                                   fg=MUTED, bg=BG)
        self.group_lbl.pack(side="left")
        self.group_filter = tk.StringVar(value="전체")
        self.group_combo = ttk.Combobox(filter_row, textvariable=self.group_filter,
                                        width=14, state="readonly", font=(FONT, 9))
        self.group_combo.pack(side="left", padx=(6, 0))
        self.group_combo.bind("<<ComboboxSelected>>",
                              lambda e: self._refresh())

        # 추가 버튼(탭마다 동작이 다름)
        self.add_btn = tk.Button(self, font=(FONT, 9, "bold"), bg="#e8e8ed",
                                  fg=TEXT, bd=0, padx=10, pady=8, cursor="hand2")
        self.add_btn.pack(fill="x", padx=16)

        # 공유 — 항목 단위로 동료와 주고받기 (개선안 30)
        share_row = tk.Frame(self, bg=BG, padx=16)
        share_row.pack(fill="x", pady=(6, 0))
        tk.Button(share_row, text="⬆ 이 탭 내보내기", command=self._export_tab,
                  font=(FONT, 8), fg=TEXT, bg=CARD, activebackground=BORDER,
                  bd=1, padx=8, pady=4, cursor="hand2").pack(side="left")
        tk.Button(share_row, text="⬇ 가져오기", command=self._import_archive,
                  font=(FONT, 8), fg=TEXT, bg=CARD, activebackground=BORDER,
                  bd=1, padx=8, pady=4, cursor="hand2").pack(side="left", padx=(6, 0))

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(10, 6))

        self.list_area = tk.Frame(self, bg=BG, padx=16)
        self.list_area.pack(fill="both", expand=True, pady=(0, 14))

        self._switch_tab("서식")
        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()-320}+{master.winfo_rooty()}")

    # ── 탭 전환 ──────────────────────────────────────
    def _switch_tab(self, cat):
        self.current_cat = cat
        for c, b in self.tab_btns.items():
            active = c == cat
            b.config(bg=ACCENT if active else CARD, fg="white" if active else TEXT)
        self.desc_label.config(text=TAB_DESC[cat])
        if cat == "서식":
            self.add_btn.config(text="+ 지금 선택한 글자에서 캡처해서 추가",
                                 command=self._add_style)
            self.add_btn.pack(fill="x", padx=16)
        elif cat == "문자":
            self.add_btn.config(text="+ 새 문자/문구 추가",
                                 command=self._add_char)
            self.add_btn.pack(fill="x", padx=16)
        elif cat == "템플릿":
            self.add_btn.config(text="+ 지금 선택 영역을 템플릿으로 저장",
                                 command=self._add_template)
            self.add_btn.pack(fill="x", padx=16)
        elif cat == "양식":
            self.add_btn.config(text="+ hwp 파일을 양식으로 등록",
                                 command=self._add_form)
            self.add_btn.pack(fill="x", padx=16)
        else:  # 내장 — 추가 불가(읽기 전용)
            self.add_btn.pack_forget()
        # 내장 탭은 분류 필터 대신 검색만 사용
        show_group = cat != "내장"
        if show_group:
            self.group_lbl.pack(side="left")
            self.group_combo.pack(side="left", padx=(6, 0))
        else:
            self.group_lbl.pack_forget()
            self.group_combo.pack_forget()
        self._refresh(cat)

    def _refresh(self, cat=None):
        cat = cat or self.current_cat
        for w in self.list_area.winfo_children():
            w.destroy()
        query = self.search_var.get().strip()

        if cat == "내장":
            results = builtin_chars.search(query)
            if not results:
                tk.Label(self.list_area, text="검색 결과가 없습니다.",
                         font=(FONT, 9), bg=BG, fg=MUTED).pack(anchor="w", pady=8)
                return
            for label, text, group in results[:200]:
                self._render_builtin_row(label, text, group)
            if len(results) > 200:
                tk.Label(self.list_area,
                         text=f"…외 {len(results)-200}개 (검색으로 좁혀주세요)",
                         font=(FONT, 8), bg=BG, fg=MUTED).pack(anchor="w", pady=4)
            return

        # 분류 콤보 갱신 (선택 유지)
        groups = ["전체"] + library.list_groups()
        cur = self.group_filter.get()
        self.group_combo["values"] = groups
        if cur not in groups:
            self.group_filter.set("전체")
            cur = "전체"
        items = library.list_items(cat)
        if cur != "전체":
            items = [it for it in items
                     if (it.get("group") or library.DEFAULT_GROUP) == cur]
        if query:
            ql = query.lower()
            items = [it for it in items if ql in self._search_blob(cat, it)]
        if not items:
            tk.Label(self.list_area, text="해당하는 항목이 없습니다.",
                     font=(FONT, 9), bg=BG, fg=MUTED).pack(anchor="w", pady=8)
            return
        for item in items:
            self._render_row(cat, item)

    def _search_blob(self, cat, item):
        parts = [item.get("name", ""), item.get("label", ""),
                 item.get("group", "")]
        if cat == "문자":
            parts.append(item.get("text", ""))
        return " ".join(parts).lower()

    def _render_builtin_row(self, label, text, group):
        row = tk.Frame(self.list_area, bg=ROWBG, highlightbackground=BORDER,
                        highlightthickness=1)
        row.pack(fill="x", pady=2)
        info = tk.Frame(row, bg=ROWBG, padx=10, pady=5)
        info.pack(side="left", fill="both", expand=True)
        tk.Label(info, text=text, font=(FONT, 13), bg=ROWBG, fg=TEXT,
                 anchor="w").pack(side="left")
        tk.Label(info, text=f"  \\{label}\\  · {group}", font=(FONT, 8),
                 bg=ROWBG, fg=MUTED, anchor="w").pack(side="left")
        tk.Button(row, text="삽입", font=(FONT, 9), bg=ACCENT, fg="white",
                  bd=0, padx=10, pady=5, cursor="hand2",
                  command=lambda t=text: self._insert_builtin(t)).pack(
                  side="right", padx=8)

    def _insert_builtin(self, text):
        if not _ensure_hwp(self):
            return
        try:
            hwp_engine.insert_plain(text)
        except Exception as e:
            messagebox.showerror("오류", f"{type(e).__name__}: {e}", parent=self)

    def _render_row(self, cat, item):
        row = tk.Frame(self.list_area, bg=ROWBG, highlightbackground=BORDER,
                        highlightthickness=1)
        row.pack(fill="x", pady=3)
        info = tk.Frame(row, bg=ROWBG, padx=10, pady=6)
        info.pack(side="left", fill="both", expand=True)
        if cat == "문자":
            # 문자는 내용 자체를 제목으로 (그 문자 그대로 보이게)
            t = item["text"].replace("\n", " ")
            title = (t if len(t) <= ROW_PREVIEW_MAX
                     else t[:ROW_PREVIEW_MAX] + "…")
            title_font = (FONT, 12)
        else:
            title = item["name"]
            title_font = (FONT, 10, "bold")
        tk.Label(info, text=title, font=title_font,
                 bg=ROWBG, fg=TEXT, anchor="w").pack(anchor="w")
        tk.Label(info, text=self._summary(cat, item), font=(FONT, 8),
                 bg=ROWBG, fg=MUTED, anchor="w", wraplength=260,
                 justify="left").pack(anchor="w")

        # 더블클릭으로도 수정 (팔레트 블럭과 동일한 조작)
        for w in (row, info):
            w.bind("<Double-Button-1>", lambda e, c=cat, it=item: self._edit(c, it))

        btns = tk.Frame(row, bg=ROWBG, padx=8)
        btns.pack(side="right")
        action_label = {"서식": "적용", "양식": "열기"}.get(cat, "삽입")
        tk.Button(btns, text=action_label, font=(FONT, 9), bg=ACCENT, fg="white",
                  bd=0, padx=10, pady=5, cursor="hand2",
                  command=lambda: self._act(cat, item)).pack(side="left", padx=2)
        tk.Button(btns, text="✎", font=(FONT, 9), bg=CARD, fg=TEXT,
                  bd=1, padx=8, pady=4, cursor="hand2",
                  command=lambda: self._edit(cat, item)).pack(side="left", padx=2)
        tk.Button(btns, text="삭제", font=(FONT, 9), bg="#e8e8ed", fg=TEXT,
                  bd=0, padx=10, pady=5, cursor="hand2",
                  command=lambda: self._delete(cat, item)).pack(side="left", padx=2)

    def _summary(self, cat, item):
        meta = f"\\{item.get('label', item['name'])}\\ · {item.get('group', library.DEFAULT_GROUP)}"
        if cat == "서식":
            fields = ", ".join(f"{k}:{v}" for k, v in item["fields"].items())
            return f"{fields}  |  {meta}"
        if cat == "문자":
            return f"{item['name']}  |  {meta}"
        slots = int(item.get("slot_count") or 0)
        slot_txt = f"빈칸 {slots}개" if slots else "빈칸 없음"
        return f"{slot_txt}  |  {meta}"

    # ── 서식 ─────────────────────────────────────────
    def _add_style(self):
        if not _ensure_hwp(self):
            return
        if not hwp_engine.has_selection():
            messagebox.showwarning("선택 없음",
                "한글에서 저장할 서식이 적용된 글자를 먼저 선택해주세요.", parent=self)
            return
        dlg = StyleFieldDialog(self)
        self.wait_window(dlg)
        if not dlg.result:
            return
        delta = engine_library.capture_charshape(dlg.result)
        if not delta:
            messagebox.showwarning("캡처 실패", "선택한 항목을 읽지 못했습니다.", parent=self)
            return
        meta = MetaDialog(self, title="서식 등록")
        self.wait_window(meta)
        if not meta.result:
            return
        name, label, group = meta.result
        library.add_style(name, delta, label=label, group=group)
        self._refresh("서식")
        self._notify()

    # ── 문자 ─────────────────────────────────────────
    def _read_selected_text(self):
        return hwp_engine.read_selection_text()

    def _add_char(self):
        if not _ensure_hwp(self):
            return
        prefill = self._read_selected_text() if hwp_engine.has_selection() else ""
        dlg = TextInputDialog(self, prefill)
        self.wait_window(dlg)
        if dlg.result is None or not dlg.result.strip():
            return
        content = dlg.result
        default_name = content.strip().replace("\n", " ")[:AUTO_NAME_MAX]
        meta = MetaDialog(self, title="문자/문구 등록", name=default_name)
        self.wait_window(meta)
        if not meta.result:
            return
        name, label, group = meta.result
        library.add_char(name, content, label=label, group=group)
        self._refresh("문자")
        self._notify()

    # ── 템플릿 ───────────────────────────────────────
    def _add_template(self):
        if not _ensure_hwp(self):
            return
        if not hwp_engine.has_selection():
            # 드래그가 없어도, 표 안을 클릭만 해뒀으면 표 전체를 자동 선택
            if not engine_library.auto_select_table_if_inside():
                messagebox.showwarning("선택 없음",
                    "한글에서 템플릿으로 저장할 영역을 드래그로 선택하거나,\n"
                    "표를 저장하려면 표 안을 클릭만 해둬도 됩니다.", parent=self)
                return
        # 빈칸 스캔 — \ 하나가 빈칸 하나
        captured_text = hwp_engine.read_selection_text(retries=6)
        slot_count = captured_text.count("\\")
        if slot_count:
            note = (f"빈칸(\\) {slot_count}개 발견 — 마크다운 변환 시 아랫줄 "
                    f"{slot_count}줄이 위에서부터 순서대로 채워집니다.\n"
                    "   (비울 칸에는 '-' 한 줄)")
        elif "/" in captured_text:
            # 실제로 겪은 혼동: 빈칸을 슬래시(/)로 찍으면 인식 안 됨 (2026-07-16)
            note = ("⚠ 빈칸 표시가 없습니다. 혹시 슬래시(/)를 쓰셨나요?\n"
                    "   빈칸은 역슬래시(\\)여야 합니다 — 한글에서 ₩ 로 보이는 그 키입니다.")
        else:
            note = ("빈칸 표시(\\)가 없습니다. 글자가 들어갈 자리에 \\ 를 넣어두면\n"
                    "마크다운 변환 때 아랫줄 내용이 순서대로 채워집니다.")
        meta = MetaDialog(self, title="템플릿 등록", extra_note=note)
        self.wait_window(meta)
        if not meta.result:
            return
        name, label, group = meta.result
        # 조각을 최종 위치에 '바로' 저장한다 — 임시 이름으로 저장 후 이름을 바꾸면
        # 한글이 그 파일을 물고 있어 WinError 32 가 났다(2026-07-19). save_to 로
        # 넘기면 library 가 uuid 경로를 만들어 여기에 직접 저장시킨다.
        try:
            library.add_template_from_capture(
                name, engine_library.capture_fragment, label=label,
                group=group, slot_count=slot_count)
        except Exception as e:
            applog.exc("템플릿 캡처 실패", e)
            messagebox.showerror("캡처 실패", str(e), parent=self)
            return
        # 구버전이 한글에 열어둔 _tmp 문서가 있으면 닫고 디스크에서도 청소
        try:
            engine_library.close_stale_temp_docs()
            library.cleanup_temp_fragments()
        except Exception as e:
            applog.exc("임시 파일 청소 실패 (무해)", e)
        self._refresh("템플릿")
        self._notify()

    # ── 양식 ─────────────────────────────────────────
    def _add_form(self):
        """hwp 파일을 통째로 양식으로 등록 (한글을 안 열어도 됨)."""
        path = filedialog.askopenfilename(
            title="양식으로 등록할 한글 파일 선택",
            filetypes=[("한글 파일", "*.hwp *.hwpx"), ("모든 파일", "*.*")],
            parent=self)
        if not path:
            return
        # 빈칸(\) 개수 세기 — 한글로 열어서 확인 (실패해도 등록은 진행)
        slot_count = 0
        try:
            hwp_engine.connect()
            slot_count = engine_library.count_slots_in_file(path)
        except Exception:
            pass
        if slot_count:
            note = (f"빈칸(\\) {slot_count}개 발견 — \\라벨\\ 변환 시 아랫줄 "
                    f"{slot_count}줄이 순서대로 채워집니다. (비울 칸엔 '-')")
        else:
            note = ("빈칸(\\)이 없습니다. 양식에 \\ 를 넣어두면 변환 때 채울 수 있습니다.\n"
                    "지금 등록해도 '새 문서로 열기'는 됩니다.")
        default_name = pathlib.Path(path).stem
        meta = MetaDialog(self, title="양식 등록", name=default_name,
                          extra_note=note)
        self.wait_window(meta)
        if not meta.result:
            return
        name, label, group = meta.result
        try:
            library.add_form_from_file(name, path, label=label, group=group,
                                       slot_count=slot_count)
        except Exception as e:
            messagebox.showerror("등록 실패", str(e), parent=self)
            return
        self._refresh("양식")
        self._notify()

    # ── 공통: 적용/삽입 · 삭제 ───────────────────────
    def _act(self, cat, item):
        if not _ensure_hwp(self):
            return
        try:
            if cat == "서식":
                if not hwp_engine.has_selection():
                    messagebox.showwarning("선택 없음",
                        "서식을 입힐 글자를 한글에서 먼저 선택해주세요.", parent=self)
                    return
                engine_library.apply_charshape_delta(item["fields"])
            elif cat == "문자":
                hwp_engine.insert_plain(item["text"])
            elif cat == "양식":
                engine_library.open_form(library.template_path(item))
            else:
                engine_library.insert_fragment(library.template_path(item))
        except Exception as e:
            messagebox.showerror("오류", f"{type(e).__name__}: {e}", parent=self)

    def _delete(self, cat, item):
        name = item["name"]
        used = library.count_palette_refs(cat, item["id"])
        msg = f"'{name}' 항목을 삭제할까요?"
        if used:
            msg += (f"\n\n⚠ 팔레트 {used}곳에서 사용 중입니다."
                    "\n   그 블럭들도 함께 삭제됩니다.")
        if messagebox.askyesno("삭제", msg, parent=self):
            library.delete_item(cat, item["id"])
            self._refresh(cat)
            self._notify()

    # ── 내보내기 / 가져오기 (개선안 30) ────────────────
    def _export_tab(self):
        """지금 보고 있는 탭의 항목을 통째로 zip 으로 내보낸다."""
        cat = self.current_cat
        if cat == "내장":
            messagebox.showinfo(
                "내보낼 수 없음",
                "내장 문자는 프로그램에 들어 있어 따로 주고받을 필요가 없습니다.",
                parent=self)
            return
        items = library.list_items(cat)
        if not items:
            messagebox.showinfo("항목 없음", f"'{cat}' 탭에 내보낼 항목이 없습니다.",
                                parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self, title=f"'{cat}' 내보내기",
            defaultextension=".zip", initialfile=f"hwp_palette_{cat}.zip",
            filetypes=[("hwp_palette 라이브러리", "*.zip")])
        if not path:
            return
        try:
            n = library.export_items([(cat, it) for it in items], path)
        except Exception as e:
            applog.exc(f"라이브러리 내보내기 실패 ({cat})", e)
            messagebox.showerror("내보내기 실패", f"{type(e).__name__}: {e}",
                                 parent=self)
            return
        skipped = len(items) - n
        msg = f"'{cat}' {n}개를 내보냈습니다.\n{pathlib.Path(path).name}"
        if skipped:
            msg += f"\n\n(조각 파일이 없어 {skipped}개는 빠졌습니다 — app.log 참고)"
        messagebox.showinfo("내보내기 완료", msg, parent=self)

    def _import_archive(self):
        """받은 zip 을 라이브러리에 추가한다. 덮어쓰기는 하지 않는다."""
        path = filedialog.askopenfilename(
            parent=self, title="라이브러리 가져오기",
            filetypes=[("hwp_palette 라이브러리", "*.zip"), ("모든 파일", "*.*")])
        if not path:
            return
        try:
            r = library.import_archive(path)
        except Exception as e:
            applog.exc(f"라이브러리 가져오기 실패 ({path})", e)
            messagebox.showerror("가져오기 실패", f"{type(e).__name__}: {e}",
                                 parent=self)
            return
        lines = [f"{r['added']}개를 가져왔습니다. (기존 항목은 그대로 둡니다)"]
        if r["renamed"]:
            lines.append("\n이름이 겹쳐 바꾼 항목:")
            lines += [f"  {a} → {b}" for a, b in r["renamed"][:8]]
        if r["relabeled"]:
            lines.append("\n라벨이 겹쳐 바꾼 항목:")
            lines += [f"  \\{a}\\ → \\{b}\\" for a, b in r["relabeled"][:8]]
            lines.append("(라벨을 그대로 두면 마크다운 변환에서 호출되지 않습니다)")
        messagebox.showinfo("가져오기 완료", "\n".join(lines), parent=self)
        self._refresh()
        self._notify()

    def _edit(self, cat, item):
        """등록된 항목의 이름·라벨·분류 수정 (id 유지 → 팔레트 연결 안 깨짐)."""
        meta = MetaDialog(self, title=f"{cat} 수정", name=item["name"],
                          label=item.get("label", ""), exclude_id=item["id"])
        try:
            meta.group_var.set(item.get("group", library.DEFAULT_GROUP))
        except Exception:
            pass
        self.wait_window(meta)
        if not meta.result:
            return
        name, label, group = meta.result
        library.update_item(cat, item["id"], name=name, label=label, group=group)
        self._refresh(cat)
        self._notify()

    def _notify(self):
        if self.on_saved:
            self.on_saved()


def open_manager(master, on_saved=None):
    return LibraryManager(master, on_saved=on_saved)
