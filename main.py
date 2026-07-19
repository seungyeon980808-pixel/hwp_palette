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
import tkinter as tk
from tkinter import messagebox, filedialog

import applog
import paths
import theme
import onboarding
import parser as md_parser
import hwp_engine
import engine_library
import exam_engine
import settings
import settings_ui
import form_fill_ui
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

# 구버전이 남긴 _tmp_*.hwp 찌꺼기 청소 (WinError 32 로 실패했던 캡처의 잔재)
library.cleanup_temp_fragments()


def on_settings_saved(spec):
    """설정 창에서 저장/전환 시 활성 스펙을 엔진에 반영."""
    hwp_engine.set_active_spec(spec)
    try:
        notify("ok", f"양식: {settings.get_active_name()}")
    except Exception:
        pass


def fn_open_settings():
    settings_ui.open_settings(root, on_saved=on_settings_saved)


def fn_open_library():
    library_ui.open_manager(root)


def fn_open_form_fill():
    """양식 채우기 — 채울 자리를 뽑아 AI에 넘기고, 채운 걸 받아 넣는다."""
    form_fill_ui.open_form_fill(root)


# ── 한컴 연결 ───────────────────────────────────────────
def ensure_hwp():
    try:
        hwp_engine.connect()
        return True
    except Exception as e:
        applog.exc("한글 연결 실패", e)
        messagebox.showerror("연결 실패", f"한글을 먼저 실행해주세요.\n{e}")
        return False


# ── 알림 (UI 제안 3·16) ────────────────────────────────
# 예전엔 성공·경고·오류가 모두 같은 회색 한 줄이라 눈에 안 들어왔고, 다음 메시지가
# 오면 이전 것이 사라져 "무슨 경고였지?"를 다시 볼 수 없었다.
# 색 상수(MUTED/BG)는 아래 UI 절에서 정의되므로 theme 에서 직접 받는다
_NOTICE_COLORS = theme.notice_colors()      # 종류 → (글자색, 배경색)
_notices = []               # 최근 알림 [(시각, 종류, 내용), ...]
_NOTICE_KEEP = 20


def notify(kind, text, detail=""):
    """상태줄에 색으로 알리고, 최근 목록에도 남긴다(클릭해 다시 볼 수 있게)."""
    import datetime
    _notices.append((datetime.datetime.now().strftime("%H:%M:%S"), kind,
                     text + (f"\n{detail}" if detail else "")))
    del _notices[:-_NOTICE_KEEP]
    try:
        fg, bg = _NOTICE_COLORS.get(kind, _NOTICE_COLORS["info"])
        status_var.set(text)            # 여기서 notify 를 부르면 무한 재귀다
        status_lbl.config(fg=fg, bg=bg)
    except Exception:
        pass                # UI 가 아직 없는 시점 — 목록에는 이미 남았다


def _show_notice_log():
    """상태줄을 누르면 최근 알림을 펼쳐 보여준다."""
    if not _notices:
        messagebox.showinfo("최근 알림", "아직 알림이 없습니다.")
        return
    win = tk.Toplevel(root)
    win.title("최근 알림")
    win.configure(bg=BG)
    win.attributes("-topmost", True)
    tk.Label(win, text="최근 알림 (새 것이 위)", font=_font(10, "bold"),
             bg=BG, fg=TEXT).pack(anchor="w", padx=14, pady=(12, 6))
    box = tk.Text(win, width=60, height=min(20, len(_notices) * 2 + 2),
                  font=("Consolas", 9), relief="solid", bd=1, wrap="word")
    box.pack(fill="both", expand=True, padx=14)
    for t, kind, text in reversed(_notices):
        mark = {"ok": "정상", "warn": "주의", "error": "오류"}.get(kind, "안내")
        box.insert("end", f"[{t}] {mark}  {text}\n")
    box.config(state="disabled")
    tk.Button(win, text="닫기", command=win.destroy, font=_font(9),
              bg=ACCENT, fg="white", bd=0, padx=14,
              pady=5, cursor="hand2").pack(anchor="e", padx=14, pady=10)


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
        notify("error", what)
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
        notify("ok", "새 문서")
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
            notify("ok", f"{pathlib.Path(path).name}")
        except Exception as e:
            report_error(f"파일 열기 실패: {pathlib.Path(path).name}", e)


def fn_save():
    if not ensure_hwp(): return
    try:
        hwp_engine.save_document()
        notify("ok", "저장 완료")
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


def _plan_summary(ops, warns):
    """실행 계획을 한눈에 보이는 문구로 (UI 제안 5)."""
    kinds = {}
    slots = 0
    for op in ops:
        kinds[op[0]] = kinds.get(op[0], 0) + 1
        if op[0] in ("template", "form"):
            slots += len(op[2])
    label = {"line": "글자 줄", "rich_line": "서식 적용 줄",
             "template": "템플릿", "form": "양식"}
    parts = [f"{label.get(k, k)} {v}개" for k, v in kinds.items()]
    if slots:
        parts.append(f"빈칸 {slots}개 채움")
    if warns:
        parts.append(f"주의 {len(warns)}건")
    return " · ".join(parts) or "바꿀 내용 없음"


def _confirm_plan(ops, warns):
    """되돌리기 어려운 변환 전에 무엇이 일어날지 보여주고 확인받는다.

    변환은 선택 영역을 지우고 시작하므로, 잘못 누르면 한글에서 Ctrl+Z 를 여러 번
    눌러야 한다. 파서가 이미 계획(ops)을 다 계산해 두므로 보여주는 비용은 0이다.
    주의가 있거나 문서를 크게 바꿀 때만 묻는다 — 매번 물으면 성가시다.
    """
    heavy = sum(1 for o in ops if o[0] in ("template", "form"))
    if not warns and heavy == 0:
        return True                     # 글자만 바꾸는 가벼운 변환은 그냥 진행
    lines = ["이렇게 바꿉니다:", "", "  " + _plan_summary(ops, warns)]
    if warns:
        lines += ["", "주의:"] + [f"  · {w}" for w in warns[:6]]
        if len(warns) > 6:
            lines.append(f"  … 외 {len(warns) - 6}건")
    lines += ["", "진행할까요?"]
    return messagebox.askokcancel("변환 미리보기", "\n".join(lines))


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
            notify("ok", "변환 완료!")
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
                notify("warn", "양식은 라벨만 따로 선택해 변환해주세요")
                return
            if not _confirm_plan(ops, warns):
                notify("info", "변환을 취소했습니다")
                return
            hwp_engine.delete_selection()
            result = engine_library.execute_library_plan(
                ops, library.template_path, form_path_fn=library.template_path)
            hwp_engine._diag("fn_convert: execute_library_plan 후")
            if result.get("error"):
                applog.warn(f"라이브러리 변환 실패: {result['error']}")
                messagebox.showerror("변환 실패", result["error"])
                notify("warn", f"{result['error']}")
                return
            if result.get("forms"):
                msg = f"✅ 양식 열기 완료 (빈칸 {result['slots_filled']}개 채움)"
            else:
                msg = (f"✅ 라이브러리 변환: 템플릿 {result['templates']}개, "
                       f"빈칸 {result['slots_filled']}개")
            if warns:
                # 경고를 목록에도 남긴다 — 창을 닫아도 상태줄 클릭으로 다시 본다
                notify("warn", f"{msg}  (주의 {len(warns)}건 — 눌러서 보기)",
                       detail="\n".join(warns))
                messagebox.showwarning("변환 주의", "\n".join(warns[:8]))
            else:
                notify("ok", msg)
            return
        messagebox.showwarning("파싱 실패",
            "마크다운 형식을 인식하지 못했어요.\n"
            "시험문제: '발문:', '자료:', '질문:', '보기:', '선지:'\n"
            "라이브러리: \\라벨\\ (등록한 라벨)")
        notify("warn", "마크다운 형식을 인식하지 못했습니다")
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
        notify("ok", "기본 서식으로 변환")
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
        notify("ok", f"사진 삽입: {pathlib.Path(path).name}")
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
        notify("ok" if ok else "warn", msg)
    except Exception as e:
        report_error("팔레트 블럭 실행 실패", e, detail=True)


# ── UI 색 ─────────────────────────────────────
# 값은 theme.py 에 있다 (밝게/어둡게 두 벌). 여기서는 이름만 받아 쓴다 —
# 아래 코드가 BG/TEXT 를 수백 번 참조하므로 이름은 그대로 둔다.
_C     = theme.colors()
BG     = _C["bg"]
CARD   = _C["card"]
ACCENT = _C["accent"]
GREEN  = _C["green"]
YELLOW = _C["yellow"]
TEXT   = _C["text"]
MUTED  = _C["muted"]
BORDER = _C["border"]
SUBBG  = _C["subbg"]
FONT   = theme.FONT

# 화면 크기 모드 — '크게'(1.3배)로 두면 글자·칸이 모두 30% 커진다.
# 위젯을 만든 뒤에는 일괄 변경이 안 되므로(각각 폰트를 다시 줘야 함),
# 시작할 때 읽어서 모든 크기에 곱하고, 전환 시에는 프로그램을 다시 시작한다.
SCALE = settings.get_ui_scale()


def _font(size, weight=None):
    n = max(7, int(round(size * SCALE)))
    return (FONT, n) if weight is None else (FONT, n, weight)


root = tk.Tk()
root.title(f"hwp_palette v{VERSION}")
root.configure(bg=BG)
root.resizable(False, False)
root.attributes("-topmost", True)

def start_drag(e): root._x, root._y = e.x, e.y
def drag(e): root.geometry(
    f"+{root.winfo_x()+e.x-root._x}+{root.winfo_y()+e.y-root._y}")

# ── 앱 아이콘 (사용자 제작 hwp-final.svg 를 PNG 로 구운 것) ──
_ICON_96 = paths.RESOURCE_DIR / "assets" / "icon-96.png"
_icon_img = _icon_small = None
try:
    _icon_img = tk.PhotoImage(file=str(_ICON_96))
    root.iconphoto(True, _icon_img)                    # 작업표시줄/제목표시줄
    _icon_small = _icon_img.subsample(4)               # 96 → 24px (창 안 표기용)
except Exception as e:
    applog.exc("앱 아이콘 로드 실패 — 기본 아이콘으로 실행", e)


def _restart():
    """프로그램을 다시 띄운다 (화면 크기·색 모드 전환용).

    Tk 위젯은 만든 뒤에 폰트·색을 일괄로 못 바꾼다(위젯마다 config 를 다시 줘야
    하고, 이미 닫힌 창은 손댈 수도 없다). 재시작이 가장 확실하고 코드도 짧다.
    exe 로 묶으면 sys.executable 이 곧 프로그램이라 인자를 붙이면 안 된다.
    """
    import os
    import sys
    _remember_pos(quit_after=False)          # 지금 자리에서 다시 뜨도록
    if getattr(sys, "frozen", False):        # PyInstaller exe
        os.execl(sys.executable, sys.executable)
    else:
        os.execl(sys.executable, sys.executable,
                 str(pathlib.Path(__file__).resolve()))


def _toggle_scale():
    """작게(1.0) ↔ 크게(1.3) 전환."""
    settings.set_ui_scale(1.3 if SCALE < 1.15 else 1.0)
    _restart()


def _toggle_theme():
    """밝게 ↔ 어둡게 전환 (UI 제안 17)."""
    theme.set_mode("light" if theme.is_dark() else "dark")
    _restart()


# 타이틀
title = tk.Frame(root, bg=CARD, pady=5, padx=10)
title.pack(fill="x")
title.bind("<ButtonPress-1>", start_drag)
title.bind("<B1-Motion>", drag)
if _icon_small is not None:
    _icon_lbl = tk.Label(title, image=_icon_small, bg=CARD)
    _icon_lbl.pack(side="left", padx=(0, 6))
    _icon_lbl.bind("<ButtonPress-1>", start_drag)
    _icon_lbl.bind("<B1-Motion>", drag)
tk.Label(title, text="hwp_palette",
         font=_font(10, "bold"), fg=TEXT, bg=CARD).pack(side="left")
# 한글 연결 표시등 (UI 제안 4) — 눌러서 실패해야 알던 것을 미리 보여준다
conn_dot = tk.Label(title, text="●", font=_font(9), fg="#c7c7cc", bg=CARD)
conn_dot.pack(side="left", padx=(8, 0))
tk.Label(title, text=f"v{VERSION}",
         font=_font(8), fg=MUTED, bg=CARD).pack(side="left", padx=(6, 0))
tk.Button(title, text="✕", command=root.destroy,
          font=_font(10), fg=MUTED, bg=CARD,
          activebackground="#ff5c5c", activeforeground="white",
          bd=0, cursor="hand2").pack(side="right")
tk.Button(title, text=("크게" if SCALE < 1.15 else "작게"),
          command=_toggle_scale, font=_font(8), fg=MUTED, bg=CARD,
          activebackground=BORDER, bd=0, padx=6,
          cursor="hand2").pack(side="right", padx=(0, 4))
# 밝게/어둡게 (UI 제안 17) — 누르면 다시 시작하며 창 위치는 유지된다
_theme_btn = tk.Button(title, text=("어둡게" if not theme.is_dark() else "밝게"),
                       command=_toggle_theme, font=_font(8), fg=MUTED, bg=CARD,
                       activebackground=BORDER, bd=0, padx=6,
                       cursor="hand2")
_theme_btn.pack(side="right", padx=(0, 4))
tk.Frame(root, bg=BORDER, height=1).pack(fill="x")

# 파일 버튼
file_row = tk.Frame(root, bg=BG, padx=10, pady=5)
file_row.pack(fill="x")
for label, cmd in [("새 문서", fn_new), ("열기", fn_open), ("저장", fn_save)]:
    tk.Button(file_row, text=label, command=cmd,
              font=_font(8), fg=TEXT, bg=CARD,
              activebackground=BORDER, bd=0, padx=5, pady=3,
              cursor="hand2").pack(side="left", padx=(0, 6))
# 환경설정 / 양식 설정 / 라이브러리 버튼 — 오른쪽 끝
tk.Button(file_row, text="환경설정", command=lambda: fn_open_palette_settings(),
          font=_font(8), fg=TEXT, bg=CARD,
          activebackground=BORDER, bd=0, padx=5, pady=3,
          cursor="hand2").pack(side="right")
tk.Button(file_row, text="양식", command=fn_open_settings,
          font=_font(8), fg=TEXT, bg=CARD,
          activebackground=BORDER, bd=0, padx=5, pady=3,
          cursor="hand2").pack(side="right", padx=(0, 6))
tk.Button(file_row, text="라이브러리", command=lambda: fn_open_library(),
          font=_font(8), fg=TEXT, bg=CARD,
          activebackground=BORDER, bd=0, padx=5, pady=3,
          cursor="hand2").pack(side="right", padx=(0, 6))

# 안내 (접이식)
guide_wrap = tk.Frame(root, bg=BG, padx=10, pady=1)
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
    "  \\사진이름\\     → 사진 폴더의 그림 삽입 (라이브러리 창에서 폴더 연결)\n"
    "\n"
    "■ 서식 적용 (LaTeX 스타일 — \\명령{적용할 부분})\n"
    "  \\굵게{중요}          → 그 부분만 굵게\n"
    "  \\굵게\\기울임\\15{…}  → 명령을 원하는 만큼 쌓기 (숫자=크기 pt)\n"
    "  \\크기15 \\자간-5 \\색빨강 \\함초롬바탕 \\글꼴나눔고딕\n"
    "  \\내강조{…}           → 등록해 둔 서식도 명령처럼\n"
    "  { } 안에는 \\라벨\\ 도, 빈칸 \\ 도, 다른 서식도 넣을 수 있습니다\n"
    "  글자 그대로의 역슬래시가 필요하면 \\\\ 로 씁니다\n"
    "  템플릿은 단독 줄로 쓰고, 아랫줄들이\n"
    "  템플릿 속 빈칸 \\ 에 위에서부터 순서대로 채워집니다.\n"
    "  (비울 칸에는 '-' 한 줄)\n"
    "\n"
    "■ 단축키\n"
    "  Ctrl+T  마크다운 변환      Ctrl+K  찾기(블럭·라이브러리)\n"
    "  Ctrl+1~9  지금 탭의 1~9번째 블럭 실행 (위→아래, 왼→오 순서)\n"
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
        guide_toggle.config(text="마크다운 입력 형식 보기")
        _guide_open[0] = False
    else:
        guide_body.pack(fill="x", pady=(6, 0))
        guide_toggle.config(text="마크다운 입력 형식 숨기기")
        _guide_open[0] = True

guide_toggle = tk.Button(guide_wrap, text="마크다운 입력 형식 보기",
          command=_toggle_guide, font=_font(8), fg=ACCENT, bg=BG,
          activebackground=BG, activeforeground=ACCENT, bd=0,
          padx=2, pady=1, cursor="hand2", anchor="w")
guide_toggle.pack(fill="x")

# 문항 번호 — UI 는 없앴다(사용자 결정 2026-07-19). 시험문제 변환이 여전히
# 번호를 쓰므로 변수만 남겨 자동 증가한다. 초기화는 프로그램 재시작.
num_use = tk.BooleanVar(value=True)
num_var = tk.IntVar(value=1)

# 변환 버튼(1/4 폭, 두 줄 높이) + 오른쪽은 '메인' 탭 버튼칸
# — 사용자가 환경설정의 '메인' 탭에서 원하는 블럭을 채우는 영역.
btn_area = tk.Frame(root, bg=BG, padx=10, pady=4)
btn_area.pack(fill="x")
top_row = tk.Frame(btn_area, bg=BG)
top_row.pack(fill="x")
top_row.columnconfigure(1, weight=1)
convert_btn = tk.Button(top_row, text="마크다운 변환\n(Ctrl+T)",
                        command=fn_convert, width=12,
                        font=_font(9, "bold"), fg="white", bg=ACCENT,
                        activebackground="#0077ed", activeforeground="white",
                        bd=0, pady=6, cursor="hand2")
convert_btn.grid(row=0, column=0, sticky="ns")     # 옆 칸 높이에 맞춰 늘어난다
quick_area = tk.Frame(top_row, bg=BG)
quick_area.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
sub_btn = tk.Frame(btn_area, bg=BG)
sub_btn.pack(fill="x", pady=(4, 0))
tk.Button(sub_btn, text="기본 서식으로 변환", command=fn_reset_format,
          font=_font(8, "bold"), fg=TEXT, bg=YELLOW,
          activebackground=BORDER, bd=0, pady=4,
          cursor="hand2").pack(side="left", fill="x", expand=True, padx=(0, 4))
tk.Button(sub_btn, text="사진", command=fn_pick_photo,
          font=_font(8), fg=TEXT, bg=CARD, activebackground=BORDER,
          bd=1, padx=7, pady=4, cursor="hand2").pack(side="left")
tk.Button(sub_btn, text="양식 채우기", command=fn_open_form_fill,
          font=_font(8), fg=TEXT, bg=CARD, activebackground=BORDER,
          bd=1, padx=7, pady=4, cursor="hand2").pack(side="left", padx=(4, 0))

# ── 커스텀 팔레트 (탭 + 블럭) ──────────────────────────
tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=10, pady=(4, 0))

_pal_state = {"tab": 0}

pal_tabbar = tk.Frame(root, bg=BG, padx=10)
pal_tabbar.pack(fill="x", pady=(4, 0))

pal_area = tk.Frame(root, bg=BG, padx=10, pady=2)
pal_area.pack(fill="x", pady=(1, 3))


def _select_pal_tab(i):
    _pal_state["tab"] = i
    render_palette()


def _render_block_grid(parent, tab, avail_px):
    """탭의 블럭들을 정사각형 격자로 그린다 (팔레트·메인 버튼칸 공용)."""
    cols = max(1, int(tab.get("cols", palette.DEFAULT_COLS)))
    blocks = tab.get("blocks", [])
    cell_px = _adaptive_cell_px(avail_px, cols)
    grid = tk.Frame(parent, bg=BG)
    grid.pack(anchor="w")
    for i in range(cols):
        grid.columnconfigure(i, minsize=cell_px + _BLOCK_GAP_PX, weight=0)
    for blk in blocks:
        span = max(1, min(int(blk.get("span", 1)), cols))
        rows = max(1, int(blk.get("rows", 1)))
        r, c = int(blk.get("row", 0)), int(blk.get("col", 0))
        # 칸을 고정 크기 틀에 넣는다. 버튼을 그냥 grid 에 놓으면 글자 길이에 맞춰
        # 칸이 넓어져 블럭이 정사각형 격자에서 어긋난다.
        cell = tk.Frame(grid, bg=BG,
                        width=cell_px * span + _BLOCK_GAP_PX * (span - 1),
                        height=cell_px * rows + _BLOCK_GAP_PX * (rows - 1))
        cell.pack_propagate(False)
        cell.grid(row=r, column=c, columnspan=span, rowspan=rows,
                  padx=_BLOCK_GAP_PX // 2, pady=_BLOCK_GAP_PX // 2)
        _make_block_button(cell, blk, span).pack(fill="both", expand=True)


def render_palette():
    for w in pal_tabbar.winfo_children():
        w.destroy()
    for w in pal_area.winfo_children():
        w.destroy()
    for w in quick_area.winfo_children():
        w.destroy()

    all_tabs = palette.load_tabs()
    # '메인' 탭은 변환 버튼 옆 버튼칸으로 그려진다 — 탭 줄에는 안 나온다
    main_tab = next((t for t in all_tabs
                     if t.get("name") == palette.MAIN_TAB), None)
    tabs = [t for t in all_tabs if t.get("name") != palette.MAIN_TAB]

    # 창 폭 추정 (winfo_width 는 mainloop 전엔 1 — 요청 폭을 쓴다)
    win_w = max(root.winfo_width(), root.winfo_reqwidth(), _PAL_MIN_WIDTH_PX)

    if main_tab is not None:
        if main_tab.get("blocks"):
            # 버튼칸이 여러 줄이어도 변환 버튼이 같은 높이로 늘어난다 (UI 제안 19)
            # — top_row 를 grid 로 짜고 두 칸 모두 sticky="ns" 로 뒀기 때문에
            #   높이 계산 없이 Tk 가 맞춰 준다.
            _render_block_grid(quick_area, main_tab,
                               win_w - int(120 * SCALE))   # 변환 버튼 몫 제외
        else:
            tk.Label(quick_area,
                     text="환경설정의 '메인' 탭에서\n이 자리의 버튼을 채울 수 있습니다",
                     font=_font(8), fg=MUTED, bg=BG,
                     justify="left").pack(anchor="w", padx=4)

    if not tabs:
        tk.Label(pal_area, text="‘환경설정’에서 탭과 블럭을 만들어보세요.",
                 font=_font(8), fg=MUTED, bg=BG).pack(anchor="w")
        return
    cur = _pal_state["tab"]
    if cur >= len(tabs):
        cur = _pal_state["tab"] = 0

    # 탭 버튼들 + 설정
    for i, t in enumerate(tabs):
        active = i == cur
        tk.Button(pal_tabbar, text=t["name"], font=_font(8, "bold"),
                  bg=ACCENT if active else CARD, fg="white" if active else TEXT,
                  bd=0, padx=7, pady=2, cursor="hand2",
                  command=lambda idx=i: _select_pal_tab(idx)).pack(side="left", padx=(0, 3))
    tk.Button(pal_tabbar, text="설정", font=_font(9),
              command=lambda: fn_open_palette_settings(),
              bg=CARD, fg=MUTED, bd=0, padx=6, pady=2,
              cursor="hand2").pack(side="right")

    tab = tabs[cur]
    if not tab.get("blocks"):
        tk.Label(pal_area, text="이 탭에 블럭이 없습니다. ‘설정’으로 추가하세요.",
                 font=_font(8), fg=MUTED, bg=BG).pack(anchor="w")
    else:
        _render_block_grid(pal_area, tab, win_w - 2 * _PAL_PAD_PX)

    # 창 크기를 내용(격자 끝)에 맞춘다 — 칸 수를 바꾸면 창도 따라 변한다
    root.after_idle(lambda: root.geometry(""))


# 블럭 종류별 배경색·기호 — 환경설정 미리보기(palette_ui._make_tile/_tile_text)와
# 반드시 같아야 한다. 'form'이 여기에만 빠져 있어서, 양식 블럭이 환경설정에서는
# 📄+연녹색인데 메인 팔레트에서는 ƒ+흰 배경으로 보였다.
# type "function"은 UI에서 '서식 조합'으로 부른다 (개선안 10 — 저장 키는 그대로).
_BLOCK_COLOR = theme.block_colors()

# 팔레트 한 칸의 한 변(px). 칸은 정사각형이고, **칸 수에 맞춰 크기가 변한다** —
# 고정 크기로 두면 칸 수가 적을 때 오른쪽에 빈 공간이 크게 남는다.
_BLOCK_CELL_MAX_PX = 34   # SCALE 적용 전 기준값     # 칸 수가 적어도 이보다 크게는 안 키운다
_BLOCK_CELL_MIN_PX = 16     # 칸 수가 많아도 이보다 작아지면 못 누른다
_BLOCK_GAP_PX = 2
_PAL_PAD_PX = 10            # 팔레트 좌우 여백 (pal_area 의 padx 와 같아야 한다)
_PAL_MIN_WIDTH_PX = int(380 * SCALE)   # 폭을 아직 모를 때 쓸 하한


def _adaptive_cell_px(avail_px, cols):
    """쓸 수 있는 폭을 칸 수로 나눠 한 칸의 크기를 정한다 (정사각형)."""
    if cols <= 0:
        return _BLOCK_CELL_MAX_PX
    size = (avail_px - _BLOCK_GAP_PX * cols) // cols
    return max(int(_BLOCK_CELL_MIN_PX * SCALE),
               min(int(_BLOCK_CELL_MAX_PX * SCALE), size))


def _block_label_max(span):
    """칸 수에 맞는 글자 수 상한.

    칸을 정사각형으로 고정했으므로 긴 이름은 넣을 자리가 없다. 넘치면 잘라서
    보여주고 전체 이름은 툴팁으로 뜬다(_add_tooltip).

    26px 칸에 9pt 한글이 대략 1.7자 들어가므로 칸당 2자로 잡는다. 이름이 길면
    환경설정에서 그 블럭의 칸 수를 늘리는 게 정답이다.
    """
    return max(2, span * 2)


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


def _block_tooltip(blk):
    """블럭 툴팁 문구 — 이름뿐 아니라 **내용**까지 보여준다 (UI 제안 6).

    이름만으로는 서식 조합에 뭐가 들었는지, 템플릿에 빈칸이 몇 개인지 알 수 없어
    눌러 봐야 알았다. 툴팁에 미리 적어 두면 잘못 누르는 일이 준다.
    """
    btype = blk.get("type")
    name = _block_label(blk)
    if btype == "char":
        return f"문자 삽입\n{blk.get('value', '')}"
    if btype == "function":
        parts = []
        for a in blk.get("actions", []):
            v = a.get("value")
            parts.append(a["func"] if v is None else f"{a['func']} {v}")
        return f"서식 조합 · {name}\n" + (" + ".join(parts) or "(비어 있음)")
    if btype in ("template", "form"):
        cat = "양식" if btype == "form" else "템플릿"
        it = library.get_item(cat, item_id=blk.get("ref"),
                              name=blk.get("form" if btype == "form" else "template"))
        if not it:
            return f"{cat} · {name}\n라이브러리에서 삭제된 항목입니다"
        n = int(it.get("slot_count") or 0)
        where = "새 문서로 열기" if btype == "form" else "커서 자리에 삽입"
        blanks = f"빈칸 {n}개 — 변환 시 아랫줄 {n}줄이 채워집니다" if n else "빈칸 없음"
        tip = f"{cat} · {it['name']}\n{where} · {blanks}"
        # 저장할 때 뽑아둔 본문 몇 줄 (UI 제안 7) — 이름이 비슷한 템플릿을
        # 누르기 전에 구별할 수 있게. 예전에 등록한 것은 비어 있어 안 붙는다.
        prev = library.get_preview(it)
        if prev:
            tip += "\n───────────\n" + prev
        return tip
    return name


def _add_tooltip(widget, text, force=False):
    """마우스를 올리면 말풍선을 보여준다 (개선안 15, UI 제안 6).

    블럭 이름은 칸 폭 때문에 잘릴 수밖에 없는데, 잘린 채로는 비슷한 이름을
    구별할 수 없었다. 지금은 이름이 안 잘려도 '내용'을 보여주므로 늘 붙인다.
    force: 문구만 갈아끼우고 싶을 때(연결 표시등처럼 상태가 바뀌는 위젯).
    """
    tip = {"win": None, "text": text}
    if force:
        widget._tip_state = tip

    def show(_event=None):
        if tip["win"] is not None:
            return
        win = tk.Toplevel(widget)
        win.wm_overrideredirect(True)       # 제목표시줄 없는 말풍선
        win.wm_geometry(f"+{widget.winfo_rootx() + 10}"
                        f"+{widget.winfo_rooty() + widget.winfo_height() + 4}")
        # 메인 창이 topmost라 말풍선도 올려주지 않으면 뒤로 숨는다
        win.attributes("-topmost", True)
        tk.Label(win, text=tip["text"], font=_font(8), fg=TEXT, bg="#ffffe0",
                 bd=1, relief="solid", padx=6, pady=3,
                 justify="left").pack()
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


def _make_block_button(parent, blk, span=1):
    # 자동 아이콘(▦ ƒ 📄)은 넣지 않는다 — 사용자가 정한 이름 그대로.
    # 종류 구분은 배경색이 하고, 색은 사용자가 지정할 수도 있다(blk["color"]).
    full = _block_label(blk)
    limit = _block_label_max(span)
    label = full if len(full) <= limit else full[:limit] + "…"
    bg = blk.get("color") or _BLOCK_COLOR.get(blk.get("type"), CARD)
    btn = tk.Button(parent, text=label,
                    command=lambda b=blk: run_palette_block(b),
                    font=_font(9),
                    # 글자색을 TEXT 로 고정하면 사용자가 남색·빨강을 고르거나
                    # 어두운 모드로 바꿨을 때 글자가 배경에 묻힌다 (UI 제안 18)
                    fg=theme.text_on(bg), bg=bg,
                    activebackground=BORDER, bd=1, relief="solid", pady=0,
                    cursor="hand2",
                    # 키보드로 이동할 때 '지금 어디'인지 보이게 — 초점 테두리
                    highlightthickness=2, highlightbackground=bg,
                    highlightcolor=ACCENT)
    # 이름이 안 잘려도 '무엇이 들었는지'를 보여주므로 늘 붙인다 (UI 제안 6)
    _add_tooltip(btn, _block_tooltip(blk))
    return btn


render_palette()

# 상태 표시 + 버전/날짜 (CLAUDE.md 규칙: 하단 필수 표기)
status_var = tk.StringVar(value=f"양식: {settings.get_active_name()}")
status_lbl = tk.Label(root, textvariable=status_var, font=_font(8),
                      fg=MUTED, bg=BG, cursor="hand2")
status_lbl.pack(fill="x", padx=10, pady=(6, 0))
status_lbl.bind("<Button-1>", lambda e: _show_notice_log())
tk.Label(root, text=f"v{VERSION} · {RELEASE_DATE}",
         font=_font(7), fg=MUTED, bg=BG).pack(pady=(0, 2))
# 저작자 표기 — 자유 소프트웨어(AGPL-3.0). 전문은 저장소의 LICENSE 파일.
tk.Label(root, text="만든이 박승연 · © 2026 · 자유 소프트웨어 (AGPL-3.0)",
         font=_font(7), fg=MUTED, bg=BG).pack(pady=(0, 8))

def _pos_on_screen(x, y):
    """그 위치가 지금 화면 안인가 — 모니터를 뺐을 때 창이 사라지는 것 방지."""
    return (-50 <= x <= root.winfo_screenwidth() - 100
            and -20 <= y <= root.winfo_screenheight() - 80)


def _reading_order(blocks):
    """블럭을 눈으로 읽는 순서(위→아래, 왼→오)로 정렬. 단축키 번호의 기준."""
    return sorted(blocks, key=lambda b: (int(b.get("row", 0)),
                                         int(b.get("col", 0))))


# ── 통합 검색 (UI 제안 8) ───────────────────────────────
def _search_targets():
    """검색 대상 [(분류, 이름, 실행함수), ...] — 블럭·라이브러리·내장 문자."""
    out = []
    for tab in palette.load_tabs():
        for blk in tab.get("blocks", []):
            name = _block_label(blk)
            if name:
                out.append((f"블럭·{tab['name']}", name,
                            lambda b=blk: run_palette_block(b)))
    for label, (cat, item) in library.label_lookup().items():
        if cat == "문자":
            out.append(("문자", f"{label}  →  {item.get('text', '')}",
                        lambda t=item.get("text", ""): _insert_text(t)))
        elif cat == "사진":
            out.append(("사진", label, None))
        else:
            out.append((cat, label, None))
    return out


def _insert_text(text):
    if not ensure_hwp():
        return
    try:
        hwp_engine.insert_plain(text)
        notify("ok", f"삽입: {text[:20]}")
    except Exception as e:
        report_error("삽입 실패", e)


def _open_search():
    """Ctrl+K — 블럭·라이브러리를 한 창에서 찾아 Enter 로 실행."""
    win = tk.Toplevel(root)
    win.title("찾기")
    win.configure(bg=BG)
    win.attributes("-topmost", True)
    win.geometry(f"+{root.winfo_rootx() + 20}+{root.winfo_rooty() + 60}")

    targets = _search_targets()
    var = tk.StringVar()
    ent = tk.Entry(win, textvariable=var, font=_font(11), width=34,
                   relief="solid", bd=1)
    ent.pack(padx=12, pady=(12, 6))
    ent.focus_set()
    listbox = tk.Listbox(win, width=44, height=12, font=_font(9),
                         relief="solid", bd=1, activestyle="none",
                         selectbackground=ACCENT, selectforeground="white")
    listbox.pack(padx=12, pady=(0, 6))
    tk.Label(win, text="Enter 실행 · ↑↓ 이동 · Esc 닫기", font=_font(7),
             bg=BG, fg=MUTED).pack(pady=(0, 10))

    shown = []

    def refresh(*_a):
        q = var.get().strip().lower()
        listbox.delete(0, tk.END)
        shown.clear()
        for cat, name, run in targets:
            if q and q not in name.lower() and q not in cat.lower():
                continue
            shown.append((cat, name, run))
            listbox.insert(tk.END, f"[{cat}] {name}")
            if len(shown) >= 60:
                break
        if shown:
            listbox.selection_set(0)

    def run(_e=None):
        sel = listbox.curselection()
        if not sel:
            return
        cat, name, fn = shown[sel[0]]
        win.destroy()
        if fn is None:
            notify("info", f"{cat} '{name}' 은(는) 팔레트 블럭이나 "
                           "\\라벨\\ 변환으로 씁니다")
        else:
            fn()

    def move(delta):
        if not shown:
            return
        cur = listbox.curselection()
        i = (cur[0] if cur else 0) + delta
        i = max(0, min(i, len(shown) - 1))
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(i)
        listbox.see(i)

    var.trace_add("write", refresh)
    ent.bind("<Return>", run)
    ent.bind("<Down>", lambda e: move(1))
    ent.bind("<Up>", lambda e: move(-1))
    listbox.bind("<Double-Button-1>", run)
    win.bind("<Escape>", lambda e: win.destroy())
    refresh()
    return win


def _poll_connection():
    """연결 표시등 갱신 — 2초마다. 연결을 새로 만들지는 않는다."""
    try:
        ok = hwp_engine.is_connected()
        conn_dot.config(fg="#34c759" if ok else "#c7c7cc")
        _tip(conn_dot, "한글에 연결됨" if ok else
             "한글에 연결 안 됨 — 버튼을 누르면 연결을 시도합니다")
    except Exception:
        pass
    root.after(2000, _poll_connection)


def _tip(widget, text):
    """상태가 바뀌는 위젯의 툴팁 문구를 갈아끼운다 (바인딩은 한 번만)."""
    state = getattr(widget, "_tip_state", None)
    if state is None:
        _add_tooltip(widget, text, force=True)
    else:
        state["text"] = text


_poll_connection()

# ── 단축키 ──────────────────────────────────────────────
root.bind_all("<Control-t>", lambda e: fn_convert())
root.bind_all("<Control-T>", lambda e: fn_convert())
root.bind_all("<Control-k>", lambda e: _open_search())
root.bind_all("<Control-K>", lambda e: _open_search())


def _run_nth_block(n):
    """Ctrl+1~9 — 지금 탭의 n번째 블럭 실행 (UI 제안 9).

    같은 블럭을 수십 번 누르는 조판 작업에서 마우스 왕복을 없앤다.
    '지금 보는 탭' 기준이라, 탭을 바꾸면 같은 숫자가 다른 블럭이 된다.
    """
    tabs = [t for t in palette.load_tabs()
            if t.get("name") != palette.MAIN_TAB]
    if not tabs:
        return
    cur = min(_pal_state["tab"], len(tabs) - 1)
    blocks = _reading_order(tabs[cur].get("blocks", []))
    if n <= len(blocks):
        run_palette_block(blocks[n - 1])
    else:
        notify("info", f"이 탭에는 {n}번째 블럭이 없습니다")


for _i in range(1, 10):
    root.bind_all(f"<Control-Key-{_i}>", lambda e, n=_i: _run_nth_block(n))

# ── 창 위치 기억 (UI 제안 15) ───────────────────────────
root.update_idletasks()
_saved_pos = settings.get_window_pos()
if _saved_pos and _pos_on_screen(*_saved_pos):
    root.geometry(f"+{_saved_pos[0]}+{_saved_pos[1]}")
else:
    root.geometry(f"+{root.winfo_screenwidth() - root.winfo_width() - 20}+80")


def _remember_pos(quit_after=True):
    """창을 닫을 때 위치를 기억한다 — 멀티 모니터에서 매번 옮기지 않게.

    화면 모드·색 모드 전환(_restart)에서도 부른다. 그때는 창을 닫으면 안 되므로
    quit_after=False — 위치만 남기고 프로세스는 그대로 갈아탄다.
    """
    try:
        settings.set_window_pos(root.winfo_x(), root.winfo_y())
    except Exception as e:
        applog.exc("창 위치 저장 실패", e)
    if quit_after:
        root.destroy()


root.protocol("WM_DELETE_WINDOW", _remember_pos)

# 첫 실행 안내 (UI 제안 11) — exe 를 받은 사람은 여기서 쓰는 법을 배운다.
# mainloop 전에 부르면 창이 아직 안 그려져 위치 계산이 틀어지므로 after_idle.
root.after_idle(lambda: onboarding.maybe_show(root, _font))

root.mainloop()
