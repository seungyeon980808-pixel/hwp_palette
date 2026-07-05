# -*- coding: utf-8 -*-
"""빠른 입력 버튼 편집 창 (Toplevel).

그리드 칸을 골라 유니코드 기호를 입력하면 그 위치에 버튼이 생긴다.
- 칸에 기호를 직접 붙여넣거나(예: Ω), 코드포인트(U+2126)로도 입력 가능
- 빈 칸은 버튼이 안 생긴다
- 저장 위치는 전역(config.json). 양식 프리셋과 무관.
"""

import tkinter as tk
from tkinter import messagebox

import settings

COLS = settings.QUICK_COLS   # 5
ROWS = 6                     # 편집 격자 행 수 (총 30칸)

BG   = "#f5f5f7"
CARD = "#ffffff"
TEXT = "#1d1d1f"
MUTED = "#86868b"
ACCENT = "#0071e3"
BORDER = "#d2d2d7"
FONT = "맑은 고딕"


def resolve(s):
    """'U+2126'/'0x2126' → 글리프. 그 외에는 입력 그대로."""
    s = (s or "").strip()
    if not s:
        return ""
    t = s.upper()
    if t.startswith("U+") or t.startswith("0X"):
        try:
            return chr(int(t[2:], 16))
        except Exception:
            return s
    return s


class QuickButtonEditor(tk.Toplevel):
    def __init__(self, master, on_saved=None):
        super().__init__(master)
        self.on_saved = on_saved
        self.title("빠른 입력 버튼 편집")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        tk.Label(self, text="빠른 입력 버튼 편집", font=(FONT, 11, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(self,
                 text="원하는 칸에 기호를 붙여넣거나 U+2126 형식으로 입력하세요.\n"
                      "빈 칸은 버튼이 생기지 않습니다.",
                 font=(FONT, 8), bg=BG, fg=MUTED, justify="left").pack(
                 anchor="w", padx=14, pady=(0, 8))

        grid = tk.Frame(self, bg=BG, padx=14)
        grid.pack()
        self.entries = []
        items = settings.get_quick_buttons()
        for r in range(ROWS):
            rowf = tk.Frame(grid, bg=BG)
            rowf.pack()
            for c in range(COLS):
                idx = r * COLS + c
                val = items[idx] if idx < len(items) else ""
                var = tk.StringVar(value=val)
                e = tk.Entry(rowf, textvariable=var, width=4, justify="center",
                             font=(FONT, 13), relief="solid", bd=1,
                             bg=CARD, fg=TEXT)
                e.pack(side="left", padx=3, pady=3)
                self.entries.append(var)

        foot = tk.Frame(self, bg=BG, padx=14, pady=12)
        foot.pack(fill="x")
        tk.Button(foot, text="미리보기 반영", command=self._apply_preview,
                  font=(FONT, 9), bg="#e8e8ed", fg=TEXT, bd=0, padx=10, pady=6,
                  cursor="hand2").pack(side="left")
        tk.Button(foot, text="💾 저장", command=self._save,
                  font=(FONT, 10, "bold"), bg=ACCENT, fg="white", bd=0,
                  padx=16, pady=6, cursor="hand2").pack(side="right")
        tk.Button(foot, text="닫기", command=self.destroy,
                  font=(FONT, 10), bg="#e8e8ed", fg=TEXT, bd=0,
                  padx=16, pady=6, cursor="hand2").pack(side="right", padx=(0, 6))

        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx()-300}+{master.winfo_rooty()+120}")

    def _collect(self):
        """빈 뒤쪽 칸은 잘라내고 플랫 리스트로 반환 (중간 빈칸은 위치 유지)."""
        vals = [resolve(v.get()) for v in self.entries]
        last = -1
        for i, v in enumerate(vals):
            if v.strip():
                last = i
        return vals[:last + 1]

    def _apply_preview(self):
        """U+ 코드를 글리프로 바꿔 칸에 즉시 반영 (저장 전 확인용)."""
        for v in self.entries:
            v.set(resolve(v.get()))

    def _save(self):
        settings.save_quick_buttons(self._collect())
        if self.on_saved:
            self.on_saved()
        messagebox.showinfo("저장", "빠른 입력 버튼을 저장했습니다.", parent=self)


def open_editor(master, on_saved=None):
    return QuickButtonEditor(master, on_saved=on_saved)
