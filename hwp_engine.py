# -*- coding: utf-8 -*-
"""한컴 자동화(pyhwpx) 코어 — 연결·문서·선택·글꼴·표 생성·찾기.

Tkinter/UI에 의존하지 않는다. 표/박스의 모든 치수·글꼴·테두리는 활성 스펙(S)에서
읽는다. S는 settings.py의 프리셋에서 온다. 실패는 예외로 올라간다.
메시지박스/상태표시는 호출부의 책임.

모듈 경계 (개선안 19 — 2026-07-18 분할):
  hwp_engine     (이 파일) 한글을 다루는 원시 동작. 다른 엔진이 공유하는 토대.
  exam_engine    시험문제 조판 (발문·자료박스·보기박스·선지 표).
  engine_library 라이브러리(서식/템플릿/양식) 캡처·적용, 팔레트 블럭 실행,
                 \\라벨\\ 마크다운 변환 실행.
연결 인스턴스(hwp)는 이 모듈이 소유하고, 나머지는 `hwp_engine.hwp` 로 참조한다
— `from hwp_engine import hwp` 로 가져오면 재연결 시 낡은 객체를 붙들게 된다.
"""

from pyhwpx import Hwp
import applog
import settings

hwp = None

# 활성 스펙(프리셋). main.py가 시작 시 set_active_spec()으로 주입한다.
S = settings.default_spec()


def set_active_spec(spec):
    """설정 창에서 프리셋을 바꾸거나 저장하면 호출된다."""
    global S
    S = spec


# ── 진단 로거 (창 상태 추적용. 평소엔 꺼둠 — 문제 재현이 필요할 때만 True) ──
DIAG = False
_DIAG_PATH = None


def _diag(tag):
    """현재 한글 창 상태를 파일에 기록. 창을 바꾸는 범인을 찾기 위한 임시 도구."""
    if not DIAG:
        return
    global _DIAG_PATH
    try:
        import os
        import win32gui
        if _DIAG_PATH is None:
            _DIAG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "window_diag.log")
            with open(_DIAG_PATH, "w", encoding="utf-8") as f:
                f.write("=== 창 상태 추적 시작 ===\n")
        lines = []
        for h in _hwp_window_handles():
            pl = win32gui.GetWindowPlacement(h)
            rc = win32gui.GetWindowRect(h)
            state = {1: "보통", 2: "최소", 3: "최대"}.get(pl[1], pl[1])
            lines.append(f"{state} {rc[2]-rc[0]}x{rc[3]-rc[1]}")
        with open(_DIAG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{tag}] {' | '.join(lines) if lines else '(창 없음)'}\n")
    except Exception as e:
        applog.exc("진단 로그 기록 실패", e)


def _hwp_window_handles():
    """현재 떠 있는 한글 창 핸들 목록."""
    try:
        import win32gui
    except ImportError:
        return []
    found = []

    def _cb(hwnd, _):
        try:
            # 클래스명은 'HwndWrapper[Hwp.exe;;...]' — 대소문자가 환경마다 다르므로
            # 반드시 소문자로 비교한다 (실측: Hwp.exe 로 나와 매칭 실패했던 버그)
            if (win32gui.IsWindowVisible(hwnd)
                    and "hwp.exe" in win32gui.GetClassName(hwnd).lower()):
                found.append(hwnd)
        except Exception as e:
            applog.exc(f"창 정보 조회 실패 (hwnd={hwnd})", e)
    try:
        win32gui.EnumWindows(_cb, None)
    except Exception as e:
        applog.exc("창 목록 열거 실패", e)
        return []
    return found


def connect():
    """이미 연결돼 있으면 재사용, 아니면 새로 연결. 실패 시 예외 발생.

    창 상태 보존 (실측 2026-07-16):
      pyhwpx의 Hwp() 생성자는 무조건
        XHwpWindows.Active_XHwpWindow.Visible = visible
      을 실행하는데, 이 대입이 '이미 최대화된 창'을 보통 크기로 되돌린다
      (최대화 1550x878 -> 보통 1080x799 재현). 사용자가 한글을 최대화해 두고
      변환을 누르면 창이 줄어드는 증상의 원인.
      → 새로 연결하기 전에 창 배치를 저장했다가 그대로 복원한다.
    """
    global hwp
    try:
        _ = hwp.Version
        _diag("connect: 기존 연결 재사용")
        return hwp
    except Exception:
        pass

    _diag("connect: 재연결 직전")
    try:
        import win32gui
        saved = [(h, win32gui.GetWindowPlacement(h)) for h in _hwp_window_handles()]
    except Exception as e:
        applog.exc("창 배치 저장 실패 — 최대화가 풀릴 수 있음", e)
        saved = []

    hwp = Hwp()
    _diag("connect: Hwp() 생성 직후")

    for handle, placement in saved:
        try:
            win32gui.SetWindowPlacement(handle, placement)
        except Exception as e:
            applog.exc(f"창 배치 복원 실패 (handle={handle})", e)
    if not saved:
        # 실제로 겪은 버그: 클래스명 대소문자 오타로 창을 0개로 봐서
        # 복원 로직이 통째로 무동작이었는데 아무 소리도 안 났었다.
        applog.warn("connect: 복원할 한글 창을 찾지 못함 "
                    "(한글이 새로 실행된 경우면 정상)")
    _diag(f"connect: 복원 시도 후 (저장했던 창 {len(saved)}개)")
    return hwp


# ── 문서/선택 ─────────────────────────────────────────
def new_document():
    hwp.HAction.Run("FileNew")


def open_document(path):
    hwp.open(path)


def save_document():
    hwp.save()


def has_selection():
    try:
        return hwp.SelectionMode != 0
    except Exception as e:
        applog.exc("선택 상태 조회 실패", e)
        return False


def copy_selection():
    hwp.HAction.Run("Copy")


def read_selection_text(retries=10, delay=0.08):
    """선택 영역을 Copy 후 윈도우 클립보드에서 직접 읽는다.

    Tk 클립보드(clipboard_get)는 한글의 Copy 완료와 타이밍이 어긋나
    빈 값을 돌려주는 일이 잦다(실측 2026-07-15) — win32clipboard가 안정적.
    """
    import time
    import win32clipboard
    copy_selection()
    last_error = None
    for _ in range(retries):
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(
                        win32clipboard.CF_UNICODETEXT):
                    text = win32clipboard.GetClipboardData(
                        win32clipboard.CF_UNICODETEXT)
                    if text:
                        return text
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            last_error = e          # 클립보드는 다른 앱이 잠깐 점유하면 실패한다
        time.sleep(delay)
    if last_error is not None:
        applog.exc(f"클립보드 읽기 {retries}회 모두 실패", last_error)
    return ""


def delete_selection():
    hwp.HAction.Run("Delete")


def doc_end_para():
    """문서 마지막 문단 번호.

    주의: 커서를 문서 끝으로 옮긴다. 호출부가 위치를 복원해야 한다.
    """
    hwp.MoveDocEnd()
    return hwp.GetPos()[1]


# ── 텍스트/글꼴 ───────────────────────────────────────
def set_char_shape(font, size_pt):
    act = hwp.HAction
    ps = hwp.HParameterSet
    act.GetDefault("CharShape", ps.HCharShape.HSet)
    ps.HCharShape.FaceNameHangul = font
    ps.HCharShape.FaceNameLatin  = font
    ps.HCharShape.Height = hwp.PointToHwpUnit(size_pt)
    act.Execute("CharShape", ps.HCharShape.HSet)


def _maybe_apply_font():
    f = S.get("font", {})
    if f.get("apply"):
        set_char_shape(f.get("name", "함초롬바탕"), f.get("size_pt", 10))


def _text(s):
    """생성 문항용 텍스트 삽입 — 글꼴 강제 적용 옵션을 반영한다."""
    _maybe_apply_font()
    hwp.insert_text(s)


def insert_plain(text):
    """서식/원문자 버튼용 단순 삽입 — 글꼴 강제 적용 안 함(현재 문서 서식 유지)."""
    act = hwp.HAction
    ps = hwp.HParameterSet
    act.GetDefault("InsertText", ps.HInsertText.HSet)
    ps.HInsertText.Text = text
    act.Execute("InsertText", ps.HInsertText.HSet)


def insert_picture_to_cell(img_path):
    """현재 커서가 있는 셀에 사진 삽입 — 셀 너비 맞춤(비율 유지) + 중앙 정렬"""
    act = hwp.HAction
    try:
        act.Run("ParagraphShapeAlignCenter")
    except Exception as e:
        applog.exc("사진 삽입 전 가운데 정렬 실패 — 정렬 없이 계속 진행", e)
    hwp.insert_picture(str(img_path))


# ── 표/박스 공통 헬퍼 ─────────────────────────────────
def _mm(v):
    return hwp.MiliToHwpUnit(v)


def _col_width_mm():
    return S["layout"]["column_width_mm"]


def _set_cell_border(act, ps, top, bottom, left, right):
    act.GetDefault("CellBorderFill", ps.HCellBorderFill.HSet)
    ps.HCellBorderFill.BorderTypeTop    = hwp.HwpLineType(top)
    ps.HCellBorderFill.BorderTypeBottom = hwp.HwpLineType(bottom)
    ps.HCellBorderFill.BorderTypeLeft   = hwp.HwpLineType(left)
    ps.HCellBorderFill.BorderTypeRight  = hwp.HwpLineType(right)
    act.Execute("CellBorderFill", ps.HCellBorderFill.HSet)


# 표/구역 탈출 시 반복 한도 — 표가 이만큼 깊게 중첩되는 문서는 없다고 본다
_MAX_NEST_DEPTH = 8


def _exit_table(act):
    """표 편집 상태에서 확실히 본문으로 빠져나온다.

    주의: 셀 병합(TableMergeCell) 직후처럼 '셀 선택' 상태에서 CloseEx는 표 밖으로
    나가지 않고 선택만 해제한다(실측 2026-07-05 — 이때 다음 표가 셀 안에 중첩되던
    버그의 원인). Cancel로 선택을 먼저 풀고, 본문(list 0)에 도달할 때까지 CloseEx.
    """
    act.Run("Cancel")               # 셀 선택 상태 해제
    for _ in range(_MAX_NEST_DEPTH):
        try:
            if hwp.GetPos()[0] == 0:   # list 0 = 본문
                break
        except Exception as e:
            applog.exc("표 탈출 중 위치 조회 실패 — 탈출 중단", e)
            break
        act.Run("CloseEx")
    # 본문 도달 시 커서는 표 앵커 앞 — MoveDown은 표 '첫 셀로 들어가는' 키라
    # 쓰면 안 되고(실측), MoveRight로 앵커 글자를 건너뛰어 표 뒤로 나온다.
    act.Run("MoveRight")


# 표 생성 시 열마다 붙는 셀 좌우 안여백(1.8mm×2) — 실측 보정값(2026-07-05)
_CELL_SIDE_MARGIN_MM = 3.6


def _create_table(rows, cols, total_mm, row_heights_mm):
    """rows×cols 표 생성. 완성된 표의 전체 폭이 total_mm가 되도록 열을 균등 분할.

    실측(2026-07-05):
    - WidthType: 0=단에 맞춤, 1=문단에 맞춤 → 지정 너비 무시. 2=임의 값이어야 반영.
    - ColWidth는 셀 '내용' 폭 기준이라, 완성 폭 = Σ(ColWidth + 3.6mm). 열마다
      셀 좌우 안여백만큼 빼서 지정해야 전체 폭이 total_mm에 맞는다.
    - RowHeight는 '최소 높이' — 내용·줄간격·셀 여백이 크면 그만큼 늘어난다.
    """
    act = hwp.HAction
    ps  = hwp.HParameterSet
    act.GetDefault("TableCreate", ps.HTableCreation.HSet)
    ps.HTableCreation.Rows       = rows
    ps.HTableCreation.Cols       = cols
    ps.HTableCreation.WidthType  = 2
    ps.HTableCreation.HeightType = 1
    ps.HTableCreation.WidthValue = _mm(total_mm)
    ps.HTableCreation.CreateItemArray("ColWidth", cols)
    # 열 내용 폭 = 전체 폭/열 수 - 셀 좌우 여백 (반올림 오차는 마지막 칸에서 흡수)
    content_total = total_mm - cols * _CELL_SIDE_MARGIN_MM
    each = max(content_total / cols, 1.0)
    acc = 0.0
    for i in range(cols):
        w = max(content_total - acc, 1.0) if i == cols - 1 else each
        ps.HTableCreation.ColWidth.SetItem(i, _mm(w))
        acc += each
    ps.HTableCreation.CreateItemArray("RowHeight", rows)
    for i in range(rows):
        ps.HTableCreation.RowHeight.SetItem(i, _mm(row_heights_mm[i]))
    act.Execute("TableCreate", ps.HTableCreation.HSet)


# ── 찾기 ──────────────────────────────────────────────
def find_text(query, direction="Forward"):
    r"""문서에서 문자열을 찾아 선택한다. 없으면 False.

    pyhwpx의 hwp.find()를 쓰지 않는 이유 (실측 2026-07-16):
      1) 내부에서 HAction.Execute("FindDlg", ...) 로 '찾기 대화상자'를 실제 실행함.
      2) SetMessageBoxMode(0x2FFF1) 로 바꾼 뒤 finally에서 원래값이 아니라
         0xFFFFF 를 강제 세팅해, 한글의 대화상자 처리 모드가 0x0 → 0xFFFFF 로
         영구히 바뀜 (변환할 때 '창 모드가 변하는' 증상의 원인).
    RepeatFind 만 쓰면 대화상자도 안 뜨고 모드도 그대로다(0x0 유지 실측 확인).
    """
    act = hwp.HAction
    pset = hwp.HParameterSet.HFindReplace
    act.GetDefault("RepeatFind", pset.HSet)
    pset.MatchCase = 1
    pset.SeveralWords = 0
    pset.UseWildCards = 0
    pset.WholeWordOnly = 0
    pset.AutoSpell = 1
    pset.Direction = hwp.FindDir(direction)
    pset.FindString = query
    pset.IgnoreMessage = 1
    pset.HanjaFromHangul = 1
    pset.AllWordForms = 0
    pset.FindJaso = 0
    pset.FindRegExp = 0
    pset.FindType = 1
    r = bool(act.Execute("RepeatFind", pset.HSet))
    _diag("find_text 후")
    return r
