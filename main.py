# -*- coding: utf-8 -*-
"""
마크다운 → 한글 시험문제 변환기 — UI
(30_exam_edit/exam_convert_v4_8_1(0525).py를 exam_scribe로 이식)

버전 정보
─────────────────────────────────────────
v1.3.0 (2026-07-05)
  [기능 추가] 보기박스 시각 편집 — 도식을 보며 수치 조절
  - bogi_visual_ui.py 추가: 캔버스에 보기박스를 축척으로 그리고 슬라이더로 실시간
    재렌더, 지금 조절 중인 치수를 파란 화살표로 강조(어떤 숫자가 어디인지 보며 수정)
  - '실제 한글에 미리 삽입' 버튼으로 미저장 값 즉시 실물 확인
  - 설정창 보기박스 그룹에 '🖼 도식 보며 편집' 진입 버튼
v1.2.1 (2026-07-05)
  [버그 수정] 양식 설정에서 단 폭을 바꿔도 표 크기가 안 변하던 문제 (실측 검증)
  - WidthType=0은 '명시적 너비'가 아니라 '단에 맞춤'(지정 무시)이었음 → 2로 수정.
    하드코딩 93.99mm가 실제 단 폭과 우연히 일치해 지금까지 은폐돼 있었음
  - 표 폭 보정: ColWidth는 셀 '내용' 폭이라 열마다 좌우 여백 3.6mm가 더 붙음
    → 열 폭에서 미리 빼서 완성 폭이 지정값과 일치하게 함
  - 표 탈출 버그: 보기박스처럼 셀 병합(선택 상태)으로 끝나면 CloseEx가 표 밖으로
    안 나가서 다음 표(선지 등)가 보기박스 셀 안에 중첩되던 문제
    → Cancel 후 본문(list 0) 도달까지 CloseEx 반복으로 수정
  - 행 높이는 '최소값'으로 동작(내용이 크면 늘어남)함을 설정창에 명시
v1.2.0 (2026-07-05)
  [기능 추가] 빠른 입력 버튼 편집 — 원하는 칸에 유니코드 기호를 넣어 버튼 생성
  - quickbuttons_ui.py(편집 창) 추가, 저장은 전역 config(프리셋과 무관)
  - 기호 직접 붙여넣기 또는 U+2126 형식 코드포인트 입력 지원
  - 과학 교사용 기본 기호(Ω → ℃ ± ² ₁ α β Δ …) 시드
v1.1.0 (2026-07-05)
  [기능 추가] 양식 프리셋 — 표/박스/글꼴의 모든 스펙을 프로그램 안에서 수정
  - settings.py(프리셋 저장소) / settings_ui.py(설정 창) 추가
  - 학교·시험지별로 양식을 이름 붙여 저장·전환, JSON으로 내보내/가져와 공유
  - 단 폭(2단↔1단)·글꼴·글자크기·박스 높이·줄간격·셀 여백·테두리 전부 설정화
  - hwp_engine의 하드코딩 치수를 활성 프리셋 참조로 교체
v1.0.0 (2026-07-05)
  [이관] 30_exam_edit의 마크다운 변환기를 exam_scribe 프로젝트로 이식
  - parser.py(마크다운 파싱) / hwp_engine.py(한컴 자동화) / main.py(UI) 3파일로 분리
  - [버그 수정] 마크다운 변환·원문자 삽입 시 클립보드를 임시 Tk 인스턴스로 읽어
    간헐적으로 빈 값이 반환되던 문제 — 메인 root 클립보드 + 재시도로 통일
─────────────────────────────────────────
"""

VERSION = "1.3.0"
RELEASE_DATE = "2026-07-05"

import pathlib
import time
import tkinter as tk
from tkinter import messagebox, filedialog

import parser as md_parser
import hwp_engine
import settings
import settings_ui
import quickbuttons_ui

# 설정 파일 입출력은 settings 모듈로 통합
load_config = settings.load_config
save_config = settings.save_config


print(f"{'='*45}")
print(f"  마크다운 → 한글 변환기 v{VERSION}")
print(f"  실행: python {pathlib.Path(__file__).name}")
print(f"{'='*45}")


# ── 활성 양식 프리셋 로드 (시작 시 + 설정 저장 시) ──────
hwp_engine.set_active_spec(settings.get_active_spec())


def on_settings_saved(spec):
    """설정 창에서 저장/전환 시 활성 스펙을 엔진에 반영."""
    hwp_engine.set_active_spec(spec)
    try:
        status_var.set(f"✅ 양식: {settings.get_active_name()}")
    except Exception:
        pass


def fn_open_settings():
    settings_ui.open_settings(root, on_saved=on_settings_saved)


# ── 한컴 연결 ───────────────────────────────────────────
def ensure_hwp():
    try:
        hwp_engine.connect()
        return True
    except Exception as e:
        messagebox.showerror("연결 실패", f"한글을 먼저 실행해주세요.\n{e}")
        return False


def read_selected_text():
    """Copy 후 클립보드에서 선택 텍스트 읽기.
    메인 root 클립보드 사용 + root.update()로 반영 보장 + 최대 5회 재시도."""
    try:
        root.clipboard_clear()
    except Exception:
        pass
    hwp_engine.copy_selection()
    selected = ""
    for _ in range(5):
        try:
            root.update()
            selected = root.clipboard_get()
            if selected:
                break
        except Exception:
            selected = ""
        time.sleep(0.05)
    return selected


# ── 버튼 함수 ───────────────────────────────────────────
def fn_new():
    if not ensure_hwp(): return
    try:
        hwp_engine.new_document()
        status_var.set("✅ 새 문서")
    except Exception as e:
        messagebox.showerror("오류", str(e))


def fn_open():
    if not ensure_hwp(): return
    path = filedialog.askopenfilename(
        title="한글 파일 선택",
        filetypes=[("한글 파일", "*.hwp *.hwpx"), ("모든 파일", "*.*")])
    if path:
        try:
            hwp_engine.open_document(path)
            status_var.set(f"✅ {pathlib.Path(path).name}")
        except Exception as e:
            messagebox.showerror("오류", str(e))


def fn_save():
    if not ensure_hwp(): return
    try:
        hwp_engine.save_document()
        status_var.set("✅ 저장 완료")
    except Exception as e:
        messagebox.showerror("오류", str(e))


def fn_convert():
    """선택 영역 마크다운 → 시험문제 변환"""
    if not ensure_hwp(): return
    try:
        selected = read_selected_text()
        if not selected or not selected.strip():
            messagebox.showwarning("선택 없음",
                "한글에서 변환할 텍스트를 드래그로 선택해주세요.")
            return
        data = md_parser.parse(selected)
        if not md_parser.has_recognized_content(data):
            messagebox.showwarning("파싱 실패",
                "마크다운 형식을 인식하지 못했어요.\n"
                "'발문:', '자료:', '질문:', '보기:', '선지:' 형식을 확인해주세요.")
            return
        hwp_engine.delete_selection()
        should_increment = hwp_engine.insert_question(data, num_var.get(), num_use.get())
        if should_increment:
            num_var.set(num_var.get() + 1)
        status_var.set("✅ 변환 완료!")
    except Exception as e:
        messagebox.showerror("오류", f"{type(e).__name__}: {e}")


def fn_insert_bogi():
    """빈 보기 박스만 삽입"""
    if not ensure_hwp(): return
    try:
        hwp_engine.insert_bogi_box(items=None)
        status_var.set("✅ 보기 박스 삽입")
    except Exception as e:
        messagebox.showerror("오류", f"{type(e).__name__}: {e}")


def fn_insert_material():
    """기본형 자료박스 삽입 (빈 박스)"""
    if not ensure_hwp(): return
    try:
        hwp_engine.insert_material_box("")
        status_var.set("✅ 자료 박스 삽입")
    except Exception as e:
        messagebox.showerror("오류", f"{type(e).__name__}: {e}")


def fn_insert_picture(img_path):
    if not ensure_hwp(): return
    try:
        hwp_engine.insert_picture_to_cell(img_path)
        status_var.set(f"✅ 사진 삽입: {pathlib.Path(img_path).name}")
    except Exception as e:
        messagebox.showerror("오류", f"{type(e).__name__}: {e}")


def fn_reset_format():
    """드래그한 영역의 모든 변형을 기본으로 되돌림
       (원문자 삭제 + 굵게/밑줄/자간 등 글자서식 + 줄간격/정렬 초기화)"""
    if not ensure_hwp(): return
    try:
        if not hwp_engine.has_selection():
            messagebox.showwarning("선택 없음",
                "기본으로 되돌릴 영역을 드래그로 선택해주세요.")
            return

        selected = read_selected_text()
        if not selected:
            messagebox.showwarning("읽기 실패",
                "선택 내용을 읽지 못했어요. 영역을 다시 드래그한 뒤 시도해주세요.")
            return

        if not messagebox.askyesno("기본 서식으로 변환",
                "선택 영역의 원문자를 삭제하고 모든 서식(굵게·밑줄·자간·줄간격 등)을 "
                "기본으로 되돌립니다.\n계속할까요?"):
            return

        cleaned = md_parser.strip_circled_markers(selected)
        hwp_engine.apply_reset_format(cleaned)
        status_var.set("✅ 기본 서식으로 변환 완료")
    except Exception as e:
        messagebox.showerror("오류", f"{type(e).__name__}: {e}")


def hwp_run(action):
    if not ensure_hwp(): return
    try:
        hwp_engine.run_action(action)
    except Exception as e:
        status_var.set(f"오류: {e}")


def insert_char(ch):
    if not ensure_hwp(): return
    try:
        if hwp_engine.has_selection():
            selected = read_selected_text()
            if selected and selected.strip():
                hwp_engine.insert_marked_choice(ch, selected)
                return
        hwp_engine.insert_plain(ch)
    except Exception as e:
        status_var.set(f"오류: {e}")


def insert_quick(s):
    """빠른 입력 버튼 — 기호를 그대로 삽입 (현재 문서 서식 유지)."""
    if not ensure_hwp(): return
    try:
        hwp_engine.insert_plain(s)
        status_var.set(f"삽입: {s}")
    except Exception as e:
        status_var.set(f"오류: {e}")


_markpen_on = [False]
def toggle_markpen():
    if not ensure_hwp(): return
    try:
        new_state = not _markpen_on[0]
        hwp_engine.set_markpen(new_state)
        _markpen_on[0] = new_state
        if new_state:
            markpen_btn.config(bg="#FFD60A", fg=TEXT)
            status_var.set("형광펜 ON")
        else:
            markpen_btn.config(bg=CARD, fg="#d99e00")
            status_var.set("형광펜 OFF")
    except Exception as e:
        status_var.set(f"오류: {e}")


# ── UI (Apple 스타일 밝은 톤) ──────────────────
BG     = "#f5f5f7"
CARD   = "#ffffff"
ACCENT = "#0071e3"
GREEN  = "#0071e3"
YELLOW = "#e8e8ed"
TEXT   = "#1d1d1f"
MUTED  = "#86868b"
BORDER = "#d2d2d7"
SUBBG  = "#fafafa"
FONT   = "맑은 고딕"


root = tk.Tk()
root.title(f"변환기 v{VERSION}")
root.configure(bg=BG)
root.resizable(False, False)
root.attributes("-topmost", True)

def start_drag(e): root._x, root._y = e.x, e.y
def drag(e): root.geometry(
    f"+{root.winfo_x()+e.x-root._x}+{root.winfo_y()+e.y-root._y}")

# 타이틀
title = tk.Frame(root, bg=CARD, pady=10, padx=14)
title.pack(fill="x")
title.bind("<ButtonPress-1>", start_drag)
title.bind("<B1-Motion>", drag)
tk.Label(title, text="마크다운 → 한글 변환기",
         font=(FONT, 11, "bold"), fg=TEXT, bg=CARD).pack(side="left")
tk.Label(title, text=f"v{VERSION}",
         font=(FONT, 8), fg=MUTED, bg=CARD).pack(side="left", padx=(6, 0))
tk.Button(title, text="✕", command=root.destroy,
          font=(FONT, 10), fg=MUTED, bg=CARD,
          activebackground="#ff5c5c", activeforeground="white",
          bd=0, cursor="hand2").pack(side="right")
tk.Frame(root, bg=BORDER, height=1).pack(fill="x")

# 파일 버튼
file_row = tk.Frame(root, bg=BG, padx=14, pady=10)
file_row.pack(fill="x")
for label, cmd in [("📄 새 문서", fn_new), ("📂 열기", fn_open), ("💾 저장", fn_save)]:
    tk.Button(file_row, text=label, command=cmd,
              font=(FONT, 9), fg=TEXT, bg=CARD,
              activebackground=BORDER, bd=0, padx=12, pady=6,
              cursor="hand2").pack(side="left", padx=(0, 6))
# 설정(양식 프리셋) 버튼 — 오른쪽 끝
tk.Button(file_row, text="⚙ 양식 설정", command=fn_open_settings,
          font=(FONT, 9), fg=TEXT, bg=CARD,
          activebackground=BORDER, bd=0, padx=12, pady=6,
          cursor="hand2").pack(side="right")

# 안내 (접이식)
guide_wrap = tk.Frame(root, bg=BG, padx=14, pady=4)
guide_wrap.pack(fill="x")

_guide_open = [False]
guide_body = tk.Frame(guide_wrap, bg=SUBBG, highlightbackground=BORDER, highlightthickness=1)

GUIDE_TEXT = (
    "[입력 형식]                          [변환 결과]\n"
    "발문: 다음 그림은…              →  1. 다음 그림은…\n"
    "자료:                                 →  (자료 박스)\n"
    "사진자료: / 실험자료:          →  (사진/실험 박스)\n"
    "질문: 옳은 것은?                  →  (들여쓴 질문)\n"
    "보기:                                 →  〈보 기〉 박스\n"
    "  항목1 / 항목2                    →  ㄱ. 항목1  ㄴ. 항목2\n"
    "선지: (또는 선지1/선지3/선지5)\n"
    "  ㄱ / ㄱㄴ / ㄱㄴㄷ            →  ① ㄱ  ② ㄴ … (표 배치)"
)
tk.Label(guide_body, text=GUIDE_TEXT, font=("Consolas", 8),
         fg=TEXT, bg=SUBBG, justify="left").pack(anchor="w", padx=12, pady=10)

def _toggle_guide():
    if _guide_open[0]:
        guide_body.pack_forget()
        guide_toggle.config(text="ⓘ  마크다운 입력 형식 보기")
        _guide_open[0] = False
    else:
        guide_body.pack(fill="x", pady=(6, 0))
        guide_toggle.config(text="ⓘ  마크다운 입력 형식 숨기기")
        _guide_open[0] = True

guide_toggle = tk.Button(guide_wrap, text="ⓘ  마크다운 입력 형식 보기",
          command=_toggle_guide, font=(FONT, 9), fg=ACCENT, bg=BG,
          activebackground=BG, activeforeground=ACCENT, bd=0,
          padx=2, pady=4, cursor="hand2", anchor="w")
guide_toggle.pack(fill="x")

# 문항 번호
num_row = tk.Frame(root, bg=BG, padx=14, pady=4)
num_row.pack(fill="x")
num_use = tk.BooleanVar(value=True)
num_var = tk.IntVar(value=1)

def _toggle_num():
    state = "normal" if num_use.get() else "disabled"
    num_spin.config(state=state)
    num_reset.config(state=state)

tk.Checkbutton(num_row, text="문항 번호 사용", variable=num_use,
               command=_toggle_num, font=(FONT, 9), fg=TEXT, bg=BG,
               activebackground=BG, selectcolor=CARD,
               cursor="hand2").pack(side="left", padx=(0,8))
num_spin = tk.Spinbox(num_row, from_=1, to=100, textvariable=num_var,
           width=4, font=(FONT, 10), justify="center",
           relief="flat", bg=CARD, fg=TEXT, buttonbackground=CARD,
           highlightbackground=BORDER, highlightthickness=1)
num_spin.pack(side="left")
num_reset = tk.Button(num_row, text="초기화", command=lambda: num_var.set(1),
          font=(FONT, 8), fg=MUTED, bg=CARD, bd=0, padx=8, pady=3,
          activebackground=BORDER, cursor="hand2")
num_reset.pack(side="left", padx=(6,0))

# 메인 버튼
btn_area = tk.Frame(root, bg=BG, padx=14, pady=8)
btn_area.pack(fill="x")

tk.Button(btn_area, text="마크다운 변환",
          command=fn_convert,
          font=(FONT, 13, "bold"), fg="white", bg=ACCENT,
          activebackground="#0077ed", activeforeground="white",
          bd=0, padx=10, cursor="hand2", width=12).pack(side="left", fill="y", padx=(0, 8))

insert_col = tk.Frame(btn_area, bg=BG)
insert_col.pack(side="left", fill="both", expand=True)
for label, cmd in [("📦  보기박스 삽입", fn_insert_bogi),
                   ("🗂  자료박스 삽입", fn_insert_material)]:
    tk.Button(insert_col, text=label, command=cmd,
              font=(FONT, 10, "bold"), fg=TEXT, bg=YELLOW,
              activebackground=BORDER, bd=0, pady=10,
              cursor="hand2").pack(fill="x", pady=(0, 6))

# 서식 도구
tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(4, 0))
tk.Label(root, text="서식", font=(FONT, 8), fg=MUTED, bg=BG).pack(anchor="w", padx=14, pady=(8, 2))

fmt_area = tk.Frame(root, bg=BG, padx=14, pady=2)
fmt_area.pack(fill="x")

for label, action in [("B", "CharShapeBold"), ("U", "CharShapeUnderline"), ("I", "CharShapeItalic")]:
    styles = {"B": "bold", "U": "normal", "I": "italic"}
    tk.Button(fmt_area, text=label,
              command=lambda a=action: hwp_run(a),
              font=(FONT, 10, styles[label]), fg=TEXT, bg=CARD,
              activebackground=BORDER, bd=0, padx=10, pady=4,
              cursor="hand2", width=3).pack(side="left", padx=(0, 3))

markpen_btn = tk.Button(fmt_area, text="🖍",
          command=toggle_markpen,
          font=(FONT, 11), fg="#d99e00", bg=CARD,
          activebackground=BORDER, bd=0, padx=8, pady=4,
          cursor="hand2", width=3)
markpen_btn.pack(side="left", padx=(3, 3))

tk.Frame(fmt_area, bg=BORDER, width=1).pack(side="left", fill="y", padx=(4, 6))

tk.Label(fmt_area, text="자간", font=(FONT, 8), fg=MUTED, bg=BG).pack(side="left", padx=(0,3))
for label, action in [("−", "CharShapeSpacingDecrease"),
                      ("+", "CharShapeSpacingIncrease")]:
    tk.Button(fmt_area, text=label,
              command=lambda a=action: hwp_run(a),
              font=(FONT, 10, "bold"), fg=TEXT, bg=CARD,
              activebackground=BORDER, bd=0, pady=4,
              cursor="hand2", width=2).pack(side="left", padx=(0, 2))

tk.Frame(fmt_area, bg=BORDER, width=1).pack(side="left", fill="y", padx=(4, 6))

tk.Label(fmt_area, text="줄간격", font=(FONT, 8), fg=MUTED, bg=BG).pack(side="left", padx=(0,3))
for label, action in [("−", "ParagraphShapeDecreaseLineSpacing"),
                      ("+", "ParagraphShapeIncreaseLineSpacing")]:
    tk.Button(fmt_area, text=label,
              command=lambda a=action: hwp_run(a),
              font=(FONT, 10, "bold"), fg=TEXT, bg=CARD,
              activebackground=BORDER, bd=0, pady=4,
              cursor="hand2", width=2).pack(side="left", padx=(0, 2))

reset_row = tk.Frame(root, bg=BG, padx=14, pady=8)
reset_row.pack(fill="x", pady=(0, 4))
tk.Button(reset_row, text="↺  모든 변형을 기본으로",
          command=fn_reset_format,
          font=(FONT, 9, "bold"), fg=TEXT, bg=YELLOW,
          activebackground=BORDER, bd=0, pady=7,
          cursor="hand2").pack(fill="x")

# 원문자
tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(8, 0))
tk.Label(root, text="원문자", font=(FONT, 8), fg=MUTED, bg=BG).pack(anchor="w", padx=14, pady=(8, 2))

circ_area = tk.Frame(root, bg=BG, padx=14, pady=4)
circ_area.pack(fill="x", pady=(0, 4))
for row_chars in [["①","②","③","④","⑤"],
                  ["㉠","㉡","㉢","㉣","㉤"],
                  ["ⓐ","ⓑ","ⓒ","ⓓ","ⓔ"]]:
    row = tk.Frame(circ_area, bg=BG)
    row.pack(fill="x", pady=1)
    for ch in row_chars:
        tk.Button(row, text=ch,
                  command=lambda c=ch: insert_char(c),
                  font=(FONT, 11), fg=TEXT, bg=CARD,
                  activebackground=BORDER, bd=0, pady=4,
                  cursor="hand2", width=4).pack(side="left", padx=2)

# 빠른 입력 (사용자 편집 가능)
tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(8, 0))
quick_head = tk.Frame(root, bg=BG, padx=14, pady=8)
quick_head.pack(fill="x", pady=(8, 0))
tk.Label(quick_head, text="빠른 입력", font=(FONT, 8), fg=MUTED, bg=BG).pack(side="left")
tk.Button(quick_head, text="✏ 편집", command=lambda: fn_open_quick_editor(),
          font=(FONT, 8), fg=TEXT, bg=CARD, activebackground=BORDER,
          bd=0, padx=8, pady=2, cursor="hand2").pack(side="right")

quick_area = tk.Frame(root, bg=BG, padx=14, pady=4)
quick_area.pack(fill="x", pady=(0, 4))

def render_quick_buttons():
    for w in quick_area.winfo_children():
        w.destroy()
    items = settings.get_quick_buttons()
    last = -1
    for i, v in enumerate(items):
        if v.strip():
            last = i
    if last < 0:
        tk.Label(quick_area, text="‘✏ 편집’으로 기호를 추가하세요",
                 font=(FONT, 8), fg=MUTED, bg=BG).pack(anchor="w")
        return
    cols = settings.QUICK_COLS
    for r in range((last // cols) + 1):
        row = tk.Frame(quick_area, bg=BG)
        row.pack(fill="x", pady=1)
        for c in range(cols):
            idx = r * cols + c
            ch = items[idx] if idx < len(items) else ""
            if ch.strip():
                tk.Button(row, text=ch,
                          command=lambda s=ch: insert_quick(s),
                          font=(FONT, 11), fg=TEXT, bg=CARD,
                          activebackground=BORDER, bd=0, pady=4,
                          cursor="hand2", width=4).pack(side="left", padx=2)
            else:
                tk.Label(row, text="", width=4, bg=BG).pack(side="left", padx=2)

def fn_open_quick_editor():
    quickbuttons_ui.open_editor(root, on_saved=render_quick_buttons)

render_quick_buttons()

# 사진 삽입
tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(8, 0))

photo_head = tk.Frame(root, bg=BG, padx=14, pady=8)
photo_head.pack(fill="x", pady=(8, 0))
tk.Label(photo_head, text="사진 삽입", font=(FONT, 8), fg=MUTED, bg=BG).pack(side="left")

IMG_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp")
_cfg = load_config()
photo_dir = [_cfg.get("photo_dir", "")]

def refresh_photo_list():
    photo_listbox.delete(0, tk.END)
    d = photo_dir[0]
    if not d or not pathlib.Path(d).is_dir():
        photo_listbox.insert(tk.END, "  (폴더를 먼저 선택하세요)")
        photo_path_label.config(text="폴더 미지정")
        return
    p = pathlib.Path(d)
    files = sorted([f.name for f in p.iterdir()
                    if f.is_file() and f.suffix.lower() in IMG_EXTS])
    if not files:
        photo_listbox.insert(tk.END, "  (이 폴더에 사진이 없습니다)")
    else:
        for name in files:
            photo_listbox.insert(tk.END, name)
    shown = d if len(d) <= 32 else "…" + d[-31:]
    photo_path_label.config(text=shown)

def choose_photo_dir():
    d = filedialog.askdirectory(title="사진 폴더 선택")
    if d:
        photo_dir[0] = d
        cfg = load_config(); cfg["photo_dir"] = d; save_config(cfg)
        refresh_photo_list()

def insert_selected_photo(event=None):
    d = photo_dir[0]
    if not d:
        return
    sel = photo_listbox.curselection()
    if not sel:
        return
    name = photo_listbox.get(sel[0])
    if name.strip().startswith("("):
        return
    img_path = pathlib.Path(d) / name
    if img_path.is_file():
        fn_insert_picture(img_path)

tk.Button(photo_head, text="📁 폴더 선택", command=choose_photo_dir,
          font=(FONT, 8), fg=TEXT, bg=CARD, activebackground=BORDER,
          bd=0, padx=8, pady=2, cursor="hand2").pack(side="right")
tk.Button(photo_head, text="↻", command=lambda: refresh_photo_list(),
          font=(FONT, 9), fg=TEXT, bg=CARD, activebackground=BORDER,
          bd=0, padx=8, pady=2, cursor="hand2").pack(side="right", padx=(0, 4))

photo_path_label = tk.Label(root, text="폴더 미지정", font=(FONT, 7),
          fg=MUTED, bg=BG, anchor="w")
photo_path_label.pack(fill="x", padx=14)

photo_box = tk.Frame(root, bg=BG, padx=14, pady=4)
photo_box.pack(fill="x")
photo_scroll = tk.Scrollbar(photo_box)
photo_scroll.pack(side="right", fill="y")
photo_listbox = tk.Listbox(photo_box, height=4, font=(FONT, 9),
          bg=CARD, fg=TEXT, bd=0, highlightthickness=1,
          highlightbackground=BORDER, selectbackground=ACCENT,
          selectforeground="white", activestyle="none",
          yscrollcommand=photo_scroll.set)
photo_listbox.pack(side="left", fill="both", expand=True)
photo_scroll.config(command=photo_listbox.yview)
photo_listbox.bind("<Double-Button-1>", insert_selected_photo)

tk.Button(root, text="🖼  선택한 사진 삽입", command=insert_selected_photo,
          font=(FONT, 9, "bold"), fg=TEXT, bg=YELLOW,
          activebackground=BORDER, bd=0, pady=6,
          cursor="hand2").pack(fill="x", padx=14, pady=(0, 4))

refresh_photo_list()
root.bind("<FocusIn>", lambda e: refresh_photo_list())

# 상태 표시 + 버전/날짜 (CLAUDE.md 규칙: 하단 필수 표기)
status_var = tk.StringVar(value=f"양식: {settings.get_active_name()}")
tk.Label(root, textvariable=status_var,
         font=(FONT, 8), fg=MUTED, bg=BG).pack(pady=(6, 0))
tk.Label(root, text=f"v{VERSION} · {RELEASE_DATE}",
         font=(FONT, 7), fg=MUTED, bg=BG).pack(pady=(0, 10))

root.update_idletasks()
sw = root.winfo_screenwidth()
ww = root.winfo_width()
root.geometry(f"+{sw - ww - 20}+80")
root.mainloop()
