# -*- coding: utf-8 -*-
"""
hwp_palette — 한글(HWP) 커스텀 팔레트 · 마크다운 변환 도구 (UI)
(30_exam_edit → exam_scribe → hwp_palette 로 발전)

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

import applog
import parser as md_parser
import hwp_engine
import engine_library
import exam_engine
import settings
import settings_ui
import library
import library_ui
import palette
import palette_ui

# 설정 파일 입출력은 settings 모듈로 통합
load_config = settings.load_config
save_config = settings.save_config


print(f"{'='*45}")
print(f"  hwp_palette v{VERSION}")
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


def fn_open_library():
    library_ui.open_manager(root)


# ── 한컴 연결 ───────────────────────────────────────────
def ensure_hwp():
    try:
        hwp_engine.connect()
        return True
    except Exception as e:
        applog.exc("한글 연결 실패", e)
        messagebox.showerror("연결 실패", f"한글을 먼저 실행해주세요.\n{e}")
        return False


def report_error(what, error, detail=False):
    """실패를 세 곳에 동시에 남긴다 (개선안 12).

    창을 닫으면 사라지는 메시지박스만으로는 "왜 안 됐지"가 남지 않았다.
      · app.log  — 나중에 원인을 찾기 위한 기록
      · 메시지박스 — 지금 당장 알아야 하니까
      · 상태표시줄 — 메시지박스를 닫은 뒤에도 남아 있게
    """
    applog.exc(what, error, detail=detail)
    messagebox.showerror(what, f"{type(error).__name__}: {error}")
    try:
        status_var.set(f"⚠ {what}")
    except Exception:
        pass        # UI가 아직 안 만들어진 시점 — 로그는 이미 남았다


def read_selected_text():
    """선택 텍스트 읽기 — 윈도우 클립보드 직접 접근(hwp_engine)으로 통일.
    (Tk 클립보드는 한글 Copy와 타이밍이 어긋나 빈 값이 잦았음, 2026-07-15)"""
    return hwp_engine.read_selection_text()


# ── 버튼 함수 ───────────────────────────────────────────
def fn_new():
    if not ensure_hwp(): return
    try:
        hwp_engine.new_document()
        status_var.set("✅ 새 문서")
    except Exception as e:
        report_error("새 문서 만들기 실패", e)


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
            report_error(f"파일 열기 실패: {pathlib.Path(path).name}", e)


def fn_save():
    if not ensure_hwp(): return
    try:
        hwp_engine.save_document()
        status_var.set("✅ 저장 완료")
    except Exception as e:
        report_error("저장 실패", e)


def _form_plan_conflict(ops):
    r"""양식 변환이 다른 내용을 삼키게 되는 상황이면 안내 문구를, 아니면 None.

    양식(\양식라벨\)은 새 문서를 열기 때문에, 지금 문서에 넣을 다른 줄이나
    템플릿이 함께 선택돼 있으면 그것들은 어디에도 들어가지 못하고 사라진다.
    """
    forms = [o for o in ops if o[0] == "form"]
    if not forms:
        return None
    if len(forms) > 1:
        names = ", ".join(o[1].get("name", "?") for o in forms)
        return (f"양식이 여러 개 선택됐습니다: {names}\n\n"
                "양식은 새 문서를 열기 때문에 한 번에 하나만 변환할 수 있습니다.")
    others = [o for o in ops
              if o[0] != "form" and not (o[0] == "line" and not o[1].strip())]
    if others:
        return ("선택한 내용에 양식 말고 다른 줄이 섞여 있습니다.\n\n"
                "양식은 새 문서를 열기 때문에, 나머지 내용은 넣을 곳이 없어\n"
                "사라집니다. 양식 라벨(과 빈칸에 넣을 줄)만 선택해 변환해주세요.")
    return None


def fn_convert():
    """선택 영역 마크다운 변환 — 시험문제 문법 또는 라이브러리 \\라벨\\ 문법"""
    hwp_engine._diag("fn_convert: 버튼 눌린 직후")
    if not ensure_hwp(): return
    hwp_engine._diag("fn_convert: ensure_hwp 후")
    try:
        selected = read_selected_text()
        hwp_engine._diag("fn_convert: read_selected_text(Copy) 후")
        if not selected or not selected.strip():
            messagebox.showwarning("선택 없음",
                "한글에서 변환할 텍스트를 드래그로 선택해주세요.")
            return
        data = md_parser.parse(selected)
        if md_parser.has_recognized_content(data):
            # 시험문제 변환 (기존 동작)
            hwp_engine.delete_selection()
            should_increment = exam_engine.insert_question(data, num_var.get(), num_use.get())
            hwp_engine._diag("fn_convert: insert_question(시험문제 변환) 후")
            if should_increment:
                num_var.set(num_var.get() + 1)
            status_var.set("✅ 변환 완료!")
            return
        if md_parser.has_library_tokens(selected):
            # 라이브러리 변환: \라벨\ → 문자 치환 / 템플릿 삽입 + 빈칸 채움
            lookup = library.label_lookup()
            ops, warns = md_parser.build_library_plan(selected, lookup)
            # 양식은 '새 문서를 여는' 것이라, 같은 선택에 딸린 다른 내용은 갈 곳이
            # 없다. 예전에는 선택을 지운 뒤에야 그 사실이 드러나 사용자 글이 조용히
            # 사라졌다 → 지우기 전에 막는다.
            blocked = _form_plan_conflict(ops)
            if blocked:
                messagebox.showwarning("양식은 따로 변환해주세요", blocked)
                status_var.set("⚠ 양식은 라벨만 따로 선택해 변환해주세요")
                return
            hwp_engine.delete_selection()
            result = engine_library.execute_library_plan(
                ops, library.template_path, form_path_fn=library.template_path)
            hwp_engine._diag("fn_convert: execute_library_plan 후")
            if result.get("error"):
                applog.warn(f"라이브러리 변환 실패: {result['error']}")
                messagebox.showerror("변환 실패", result["error"])
                status_var.set(f"⚠ {result['error']}")
                return
            if result.get("forms"):
                msg = f"✅ 양식 열기 완료 (빈칸 {result['slots_filled']}개 채움)"
            else:
                msg = (f"✅ 라이브러리 변환: 템플릿 {result['templates']}개, "
                       f"빈칸 {result['slots_filled']}개")
            if warns:
                messagebox.showwarning("변환 주의", "\n".join(warns[:8]))
            status_var.set(msg)
            return
        messagebox.showwarning("파싱 실패",
            "마크다운 형식을 인식하지 못했어요.\n"
            "시험문제: '발문:', '자료:', '질문:', '보기:', '선지:'\n"
            "라이브러리: \\라벨\\ (등록한 라벨)")
        status_var.set("⚠ 마크다운 형식을 인식하지 못했습니다")
    except Exception as e:
        # detail=True — 변환은 단계가 많아 스택 없이는 원인 지점을 못 찾는다
        report_error("마크다운 변환 실패", e, detail=True)


def fn_reset_format():
    """선택 영역을 환경설정의 기본 서식으로 되돌림 (원문자 삭제 포함)."""
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
        cleaned = md_parser.strip_circled_markers(selected)
        engine_library.apply_default_format(palette.get_default_format(), text=cleaned)
        status_var.set("✅ 기본 서식으로 변환")
    except Exception as e:
        report_error("기본 서식 변환 실패", e)


def fn_open_palette_settings():
    palette_ui.open_settings(root, on_saved=render_palette)


def fn_pick_photo():
    """사진 삽입 — 파일 선택 후 커서 위치(셀)에 삽입 (따로 뺀 기능)."""
    if not ensure_hwp(): return
    path = filedialog.askopenfilename(
        title="삽입할 사진 선택",
        filetypes=[("이미지", "*.png *.jpg *.jpeg *.gif *.bmp *.tif *.tiff *.webp"),
                   ("모든 파일", "*.*")])
    if not path:
        return
    try:
        hwp_engine.insert_picture_to_cell(path)
        status_var.set(f"✅ 사진 삽입: {pathlib.Path(path).name}")
    except Exception as e:
        report_error(f"사진 삽입 실패: {pathlib.Path(path).name}", e)


def _template_path_by_ref(block):
    """블럭이 가리키는 템플릿의 조각 경로. ref(id) 우선, 없으면 이름(구 데이터)."""
    it = library.get_item("템플릿", item_id=block.get("ref"),
                          name=block.get("template"))
    return library.template_path(it) if it else None


def _template_slot_count_by_ref(block):
    r"""블럭이 가리키는 템플릿의 빈칸(\) 개수. 빈칸 청소 범위를 개수로 제한한다."""
    it = library.get_item("템플릿", item_id=block.get("ref"),
                          name=block.get("template"))
    return int(it.get("slot_count") or 0) if it else None


def _form_path_by_ref(block):
    """블럭/항목이 가리키는 양식 파일 경로."""
    it = library.get_item("양식", item_id=block.get("ref") or block.get("id"),
                          name=block.get("form") or block.get("name"))
    return library.template_path(it) if it else None


def run_palette_block(block):
    """팔레트 블럭 클릭 — 종류에 따라 삽입/적용."""
    if not ensure_hwp(): return
    try:
        ok, msg = engine_library.run_block(
            block, template_path_fn=_template_path_by_ref,
            form_path_fn=_form_path_by_ref,
            slot_count_fn=_template_slot_count_by_ref)
        if not ok:
            applog.warn(f"팔레트 블럭 실행 거부: {msg}")
        status_var.set(("✅ " if ok else "⚠ ") + msg)
    except Exception as e:
        report_error("팔레트 블럭 실행 실패", e, detail=True)


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
root.title(f"hwp_palette v{VERSION}")
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
tk.Label(title, text="hwp_palette",
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
# 환경설정 / 양식 설정 / 라이브러리 버튼 — 오른쪽 끝
tk.Button(file_row, text="⚙ 환경설정", command=lambda: fn_open_palette_settings(),
          font=(FONT, 9), fg=TEXT, bg=CARD,
          activebackground=BORDER, bd=0, padx=12, pady=6,
          cursor="hand2").pack(side="right")
tk.Button(file_row, text="📐 양식", command=fn_open_settings,
          font=(FONT, 9), fg=TEXT, bg=CARD,
          activebackground=BORDER, bd=0, padx=12, pady=6,
          cursor="hand2").pack(side="right", padx=(0, 6))
tk.Button(file_row, text="📚 라이브러리", command=lambda: fn_open_library(),
          font=(FONT, 9), fg=TEXT, bg=CARD,
          activebackground=BORDER, bd=0, padx=12, pady=6,
          cursor="hand2").pack(side="right", padx=(0, 6))

# 안내 (접이식)
guide_wrap = tk.Frame(root, bg=BG, padx=14, pady=4)
guide_wrap.pack(fill="x")

_guide_open = [False]
guide_body = tk.Frame(guide_wrap, bg=SUBBG, highlightbackground=BORDER, highlightthickness=1)

GUIDE_TEXT = (
    "■ 시험문제 문법 (한 문항을 통째로 변환)\n"
    "  발문:  …   → 1. …  (문항 번호 자동)\n"
    "  질문:  …   → 들여쓴 질문 문단\n"
    "  보기:      → 〈보 기〉 박스, 아랫줄이 ㄱ.ㄴ.ㄷ.\n"
    "  선지:      → ① ② ③ … 표 배치 (선지1/선지3/선지5)\n"
    "\n"
    "■ 라이브러리 문법 (등록한 항목 호출)\n"
    "  \\라벨\\        → 문자·문구 삽입 / 템플릿 삽입\n"
    "  \\원1\\ \\로마3\\ → 내장 문자 (① Ⅲ …)\n"
    "  \\서식\\내용\\/  → 감싼 부분에만 그 서식 적용 (예: \\굵게\\중요\\/)\n"
    "  템플릿은 단독 줄로 쓰고, 아랫줄들이\n"
    "  템플릿 속 빈칸 \\ 에 위에서부터 순서대로 채워집니다.\n"
    "  (비울 칸에는 '-' 한 줄)\n"
    "\n"
    "※ 변환할 부분을 드래그 → 마크다운 변환 (Ctrl+T)\n"
    "※ 되돌리기: 한글 창에서 Ctrl+Z. 템플릿 삽입·변환은 여러 동작이 묶여\n"
    "   있어 여러 번 눌러야 완전히 돌아갑니다. (되돌리기는 한글이 하는 것이라\n"
    "   이 창의 버튼으로는 취소되지 않습니다)"
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

# 고정 버튼 2개: 마크다운 변환 / 기본 서식으로 변환 (+ 사진)
btn_area = tk.Frame(root, bg=BG, padx=14, pady=8)
btn_area.pack(fill="x")
tk.Button(btn_area, text="마크다운 변환  (Ctrl+T)",
          command=fn_convert,
          font=(FONT, 12, "bold"), fg="white", bg=ACCENT,
          activebackground="#0077ed", activeforeground="white",
          bd=0, pady=10, cursor="hand2").pack(fill="x")
sub_btn = tk.Frame(btn_area, bg=BG)
sub_btn.pack(fill="x", pady=(6, 0))
tk.Button(sub_btn, text="↺ 기본 서식으로 변환", command=fn_reset_format,
          font=(FONT, 9, "bold"), fg=TEXT, bg=YELLOW,
          activebackground=BORDER, bd=0, pady=7,
          cursor="hand2").pack(side="left", fill="x", expand=True, padx=(0, 4))
tk.Button(sub_btn, text="🖼 사진", command=fn_pick_photo,
          font=(FONT, 9), fg=TEXT, bg=CARD, activebackground=BORDER,
          bd=1, padx=12, pady=7, cursor="hand2").pack(side="left")

# ── 커스텀 팔레트 (탭 + 블럭) ──────────────────────────
tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(8, 0))

_pal_state = {"tab": 0}

pal_tabbar = tk.Frame(root, bg=BG, padx=14)
pal_tabbar.pack(fill="x", pady=(8, 0))

pal_area = tk.Frame(root, bg=BG, padx=14, pady=4)
pal_area.pack(fill="x", pady=(2, 6))


def _select_pal_tab(i):
    _pal_state["tab"] = i
    render_palette()


def render_palette():
    for w in pal_tabbar.winfo_children():
        w.destroy()
    for w in pal_area.winfo_children():
        w.destroy()

    tabs = palette.load_tabs()
    if not tabs:
        tk.Label(pal_area, text="‘⚙ 환경설정’에서 탭과 블럭을 만들어보세요.",
                 font=(FONT, 8), fg=MUTED, bg=BG).pack(anchor="w")
        return
    cur = _pal_state["tab"]
    if cur >= len(tabs):
        cur = _pal_state["tab"] = 0

    # 탭 버튼들 + ⚙
    for i, t in enumerate(tabs):
        active = i == cur
        tk.Button(pal_tabbar, text=t["name"], font=(FONT, 9, "bold"),
                  bg=ACCENT if active else CARD, fg="white" if active else TEXT,
                  bd=0, padx=10, pady=5, cursor="hand2",
                  command=lambda idx=i: _select_pal_tab(idx)).pack(side="left", padx=(0, 3))
    tk.Button(pal_tabbar, text="⚙", font=(FONT, 9),
              command=lambda: fn_open_palette_settings(),
              bg=CARD, fg=MUTED, bd=0, padx=8, pady=5,
              cursor="hand2").pack(side="right")

    # 블럭 그리드
    tab = tabs[cur]
    cols = tab.get("cols", 5)
    blocks = tab.get("blocks", [])
    if not blocks:
        tk.Label(pal_area, text="이 탭에 블럭이 없습니다. ⚙로 추가하세요.",
                 font=(FONT, 8), fg=MUTED, bg=BG).pack(anchor="w")
        return

    grid = tk.Frame(pal_area, bg=BG)
    grid.pack(fill="x")
    for c in range(cols):
        grid.columnconfigure(c, weight=1, uniform="pal")
    r = c = 0
    for blk in blocks:
        span = min(int(blk.get("span", 1)), cols)
        if c + span > cols:      # 칸 넘치면 다음 줄
            r += 1
            c = 0
        _make_block_button(grid, blk).grid(
            row=r, column=c, columnspan=span, sticky="ew", padx=2, pady=2)
        c += span
        if c >= cols:
            r += 1
            c = 0


# 블럭 종류별 배경색·기호 — 환경설정 미리보기(palette_ui._make_tile/_tile_text)와
# 반드시 같아야 한다. 'form'이 여기에만 빠져 있어서, 양식 블럭이 환경설정에서는
# 📄+연녹색인데 메인 팔레트에서는 ƒ+흰 배경으로 보였다.
# type "function"은 UI에서 '서식 조합'으로 부른다 (개선안 10 — 저장 키는 그대로).
_BLOCK_COLOR = {"char": CARD, "template": "#eef4ff",
                "function": "#fff4e6", "form": "#eafaf1"}
_BLOCK_PREFIX = {"template": "▦ ", "function": "ƒ ", "form": "📄 "}
_BLOCK_LABEL_MAX = 14


def _block_label(blk):
    """블럭에 표시할 이름. 템플릿·양식은 라이브러리의 '현재' 이름을 따라간다."""
    btype = blk.get("type")
    if btype == "char":
        return blk.get("value", "")
    if btype in ("template", "form"):
        cat = "양식" if btype == "form" else "템플릿"
        key = "form" if btype == "form" else "template"
        it = library.get_item(cat, item_id=blk.get("ref"), name=blk.get(key))
        return it["name"] if it else f"{blk.get(key, '?')} (삭제됨)"
    return blk.get("name", "")


def _add_tooltip(widget, text):
    """마우스를 올리면 전체 이름을 말풍선으로 보여준다 (개선안 15).

    블럭 이름은 칸 폭 때문에 잘릴 수밖에 없는데, 잘린 채로는 비슷한 이름을
    구별할 수 없었다. 잘렸을 때만 붙인다.
    """
    tip = {"win": None}

    def show(_event=None):
        if tip["win"] is not None:
            return
        win = tk.Toplevel(widget)
        win.wm_overrideredirect(True)       # 제목표시줄 없는 말풍선
        win.wm_geometry(f"+{widget.winfo_rootx() + 10}"
                        f"+{widget.winfo_rooty() + widget.winfo_height() + 4}")
        # 메인 창이 topmost라 말풍선도 올려주지 않으면 뒤로 숨는다
        win.attributes("-topmost", True)
        tk.Label(win, text=text, font=(FONT, 8), fg=TEXT, bg="#ffffe0",
                 bd=1, relief="solid", padx=6, pady=3).pack()
        tip["win"] = win

    def hide(_event=None):
        if tip["win"] is not None:
            tip["win"].destroy()
            tip["win"] = None

    widget.bind("<Enter>", show, add="+")
    widget.bind("<Leave>", hide, add="+")
    widget.bind("<ButtonPress-1>", hide, add="+")   # 눌렀으면 말풍선은 치운다
    # 탭 전환으로 버튼이 destroy 될 때 <Leave> 가 안 와도 말풍선은 남지 않는다 —
    # Toplevel 을 버튼의 자식으로 만들었기 때문에 Tk 가 함께 정리한다(실측 확인).


def _make_block_button(parent, blk):
    full = _BLOCK_PREFIX.get(blk.get("type"), "") + _block_label(blk)
    label = (full if len(full) <= _BLOCK_LABEL_MAX
             else full[:_BLOCK_LABEL_MAX] + "…")
    btn = tk.Button(parent, text=label,
                    command=lambda b=blk: run_palette_block(b),
                    font=(FONT, 10), fg=TEXT,
                    bg=_BLOCK_COLOR.get(blk.get("type"), CARD),
                    activebackground=BORDER, bd=1, relief="solid", pady=6,
                    cursor="hand2")
    if label != full:
        _add_tooltip(btn, full)
    return btn


render_palette()

# 상태 표시 + 버전/날짜 (CLAUDE.md 규칙: 하단 필수 표기)
status_var = tk.StringVar(value=f"양식: {settings.get_active_name()}")
tk.Label(root, textvariable=status_var,
         font=(FONT, 8), fg=MUTED, bg=BG).pack(pady=(6, 0))
tk.Label(root, text=f"v{VERSION} · {RELEASE_DATE}",
         font=(FONT, 7), fg=MUTED, bg=BG).pack(pady=(0, 10))

# 단축키: Ctrl+T = 마크다운 변환
root.bind_all("<Control-t>", lambda e: fn_convert())
root.bind_all("<Control-T>", lambda e: fn_convert())

root.update_idletasks()
sw = root.winfo_screenwidth()
ww = root.winfo_width()
root.geometry(f"+{sw - ww - 20}+80")
root.mainloop()
