# -*- coding: utf-8 -*-
"""한컴 자동화(pyhwpx) 엔진 — Tkinter/UI에 의존하지 않는다.

표/박스의 모든 치수·글꼴·테두리는 활성 스펙(S)에서 읽는다. S는 settings.py의
프리셋에서 온다. 실패는 예외로 올라간다. 메시지박스/상태표시는 호출부의 책임.
"""

from pyhwpx import Hwp
import settings

# ── 라이브러리(서식/문자/템플릿) 캡처·적용 필드 스펙 ─────
# 친화적 이름 : (읽을 때 CharShape 딕셔너리 키, 값 변환 함수 쌍)
CHARSHAPE_FIELD_LABELS = ["굵게", "기울임", "밑줄", "글자색", "자간", "글꼴", "크기"]

hwp = None

# 활성 스펙(프리셋). main.py가 시작 시 set_active_spec()으로 주입한다.
S = settings.default_spec()


def set_active_spec(spec):
    """설정 창에서 프리셋을 바꾸거나 저장하면 호출된다."""
    global S
    S = spec


def _hwp_window_handles():
    """현재 떠 있는 한글 창 핸들 목록."""
    try:
        import win32gui
    except ImportError:
        return []
    found = []

    def _cb(hwnd, _):
        try:
            if win32gui.IsWindowVisible(hwnd) and "hwp.exe" in win32gui.GetClassName(hwnd):
                found.append(hwnd)
        except Exception:
            pass
    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
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
        return hwp
    except Exception:
        pass

    try:
        import win32gui
        saved = [(h, win32gui.GetWindowPlacement(h)) for h in _hwp_window_handles()]
    except Exception:
        saved = []

    hwp = Hwp()

    for handle, placement in saved:
        try:
            win32gui.SetWindowPlacement(handle, placement)
        except Exception:
            pass
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
    except Exception:
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
        except Exception:
            pass
        time.sleep(delay)
    return ""


def delete_selection():
    hwp.HAction.Run("Delete")


def run_action(action):
    hwp.HAction.Run(action)


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


def insert_marked_choice(ch, selected_text):
    """[드래그 후 클릭] 원문자+공백 삽입, 선택 텍스트에는 밑줄"""
    act = hwp.HAction
    delete_selection()
    insert_plain(ch + " ")
    act.Run("CharShapeUnderline")
    insert_plain(selected_text)
    act.Run("CharShapeUnderline")


def set_markpen(on):
    act = hwp.HAction
    ps = hwp.HParameterSet
    if on:
        act.GetDefault("MarkPenShape", ps.HMarkpenShape.HSet)
        ps.HMarkpenShape.Color = 0x00FFFF00
        act.Execute("MarkPenShape", ps.HMarkpenShape.HSet)
    else:
        act.Run("MarkPenDelete")


def apply_reset_format(cleaned_text):
    """선택 영역 삭제 후 글자모양/문단모양을 기본값으로, 정제된 텍스트 삽입"""
    act = hwp.HAction
    ps = hwp.HParameterSet

    delete_selection()
    act.Run("StyleClearCharShape")

    act.GetDefault("ParagraphShape", ps.HParaShape.HSet)
    ps.HParaShape.LineSpacing     = 160
    ps.HParaShape.LineSpacingType = 0
    ps.HParaShape.Indentation     = 0
    ps.HParaShape.LeftMargin      = 0
    ps.HParaShape.RightMargin     = 0
    ps.HParaShape.PrevSpacing     = 0
    ps.HParaShape.NextSpacing     = 0
    ps.HParaShape.AlignType       = 0
    act.Execute("ParagraphShape", ps.HParaShape.HSet)

    insert_plain(cleaned_text)


def insert_picture_to_cell(img_path):
    """현재 커서가 있는 셀에 사진 삽입 — 셀 너비 맞춤(비율 유지) + 중앙 정렬"""
    act = hwp.HAction
    try:
        act.Run("ParagraphShapeAlignCenter")
    except Exception:
        pass
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


def _exit_table(act):
    """표 편집 상태에서 확실히 본문으로 빠져나온다.

    주의: 셀 병합(TableMergeCell) 직후처럼 '셀 선택' 상태에서 CloseEx는 표 밖으로
    나가지 않고 선택만 해제한다(실측 2026-07-05 — 이때 다음 표가 셀 안에 중첩되던
    버그의 원인). Cancel로 선택을 먼저 풀고, 본문(list 0)에 도달할 때까지 CloseEx.
    """
    act.Run("Cancel")               # 셀 선택 상태 해제
    for _ in range(8):              # 중첩 깊이 안전 한도
        try:
            if hwp.GetPos()[0] == 0:   # list 0 = 본문
                break
        except Exception:
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


# ── 자료박스 ───────────────────────────────────────────
def insert_material_box(text):
    """자료: - 단 폭, 2행2열, 각 셀 테두리는 설정값(기본 투명)"""
    act = hwp.HAction
    ps  = hwp.HParameterSet
    box = S["material_box"]
    bt  = S["border"]["material_type"]
    _create_table(2, 2, _col_width_mm(),
                  [box["row1_height_mm"], box["row2_height_mm"]])

    def _cell():
        act.Run("TableCellBlock")
        _set_cell_border(act, ps, bt, bt, bt, bt)
        act.Run("Cancel")

    _cell()                     # 1행1열 (현재 위치)
    act.Run("TableRightCell"); _cell()   # 1행2열
    act.Run("TableRightCell"); _cell()   # 2행1열
    act.Run("TableRightCell"); _cell()   # 2행2열
    act.Run("TableLeftCell")             # 1행1열로 복귀
    act.Run("TableLeftCell")
    act.Run("TableLeftCell")
    _text(text)
    _exit_table(act)


def insert_photo_box():
    """사진자료: - 단 폭, 2행2열, 전체 투명 + 중앙정렬"""
    act = hwp.HAction
    ps  = hwp.HParameterSet
    box = S["photo_box"]
    _create_table(2, 2, _col_width_mm(),
                  [box["row1_height_mm"], box["row2_height_mm"]])

    def _cell_center():
        act.Run("TableCellBlock")
        _set_cell_border(act, ps, "None", "None", "None", "None")
        act.Run("Cancel")
        act.Run("ParagraphShapeAlignCenter")

    _cell_center()
    act.Run("TableRightCell"); _cell_center()
    act.Run("TableRightCell"); _cell_center()
    act.Run("TableRightCell"); _cell_center()
    _exit_table(act)


def insert_experiment_box():
    """실험자료: - 단 폭 1칸, 설정 높이, 설정 테두리, 안내 문구"""
    act = hwp.HAction
    ps  = hwp.HParameterSet
    box = S["experiment_box"]
    bt  = S["border"]["experiment_type"]
    _create_table(1, 1, _col_width_mm(), [box["height_mm"]])
    act.Run("TableCellBlock")
    _set_cell_border(act, ps, bt, bt, bt, bt)
    act.Run("Cancel")
    _text(box["label"])
    _exit_table(act)


# ── 보기박스 ───────────────────────────────────────────
def insert_bogi_box(items=None):
    """〈보 기〉 박스 — 3행 5열 표를 병합해 만든다. 치수·테두리·여백·줄간격은 설정값."""
    act = hwp.HAction
    ps  = hwp.HParameterSet
    box = S["bogi_box"]
    bt  = S["border"]["bogi_type"]

    _create_table(3, 5, _col_width_mm(),
                  [box["title_height_mm"], box["gap_height_mm"],
                   box["content_height_mm"]])

    # 전체 테두리 삭제
    act.Run("TableCellBlock")
    act.Run("TableCellBlockExtend")
    act.Run("TableCellBlockExtend")
    _set_cell_border(act, ps, "None", "None", "None", "None")
    act.GetDefault("CellBorderFill", ps.HCellBorderFill.HSet)
    ps.HCellBorderFill.TypeVert = hwp.HwpLineType("None")
    ps.HCellBorderFill.TypeHorz = hwp.HwpLineType("None")
    act.Execute("CellBorderFill", ps.HCellBorderFill.HSet)
    act.Run("Cancel")

    # 2~3행 바깥 테두리 (설정 테두리 종류)
    act.Run("TableCellBlock")
    act.Run("TableCellBlockExtend")
    act.Run("TableUpperCell")
    act.Run("TableLeftCell")
    act.Run("TableLeftCell")
    act.Run("TableLeftCell")
    act.Run("TableLeftCell")
    _set_cell_border(act, ps, bt, bt, bt, bt)
    act.Run("Cancel")

    # 3열 병합 후 〈보 기〉
    act.Run("TableRightCell")
    act.Run("TableRightCell")
    act.Run("TableCellBlock")
    act.Run("TableCellBlockExtend")
    act.Run("TableMergeCell")
    act.Run("ParagraphShapeAlignCenter")
    _text(box["title"])

    # 3행 전체 병합 후 ㄱㄴㄷ
    act.Run("TableLowerCell")
    act.Run("TableLeftCell")
    act.Run("TableLeftCell")
    act.Run("TableCellBlock")
    act.Run("TableCellBlockExtend")
    act.Run("TableRightCell")
    act.Run("TableRightCell")
    act.Run("TableRightCell")
    act.Run("TableRightCell")
    act.Run("TableMergeCell")

    # ㄱㄴㄷ 입력 — 셀 여백/줄간격 설정
    hwp.set_cell_margin(
        left=box["cell_margin_left_mm"], right=box["cell_margin_right_mm"],
        top=box["cell_margin_top_mm"], bottom=box["cell_margin_bottom_mm"],
        as_="mm")
    act.Run("ParagraphShapeAlignJustify")
    act.GetDefault("ParagraphShape", ps.HParaShape.HSet)
    ps.HParaShape.LineSpacing     = box["line_spacing"]
    ps.HParaShape.LineSpacingType = 0
    act.Execute("ParagraphShape", ps.HParaShape.HSet)

    if items:
        labels = ["ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ"]
        real = [it for it in items if it.strip()]
        for i, item in enumerate(real[:5]):
            if i > 0:
                act.Run("BreakPara")
            _text(f"{labels[i]}. ")
            act.Run("Indent")   # Alt+Shift+Tab 들여쓰기
            _text(item)
    else:
        for i, label in enumerate(["ㄱ", "ㄴ", "ㄷ"]):
            if i > 0:
                act.Run("BreakPara")
            _text(f"{label}. ")
            act.Run("Indent")

    # 1행3열+2행3열 병합 → 〈보기〉 위치 확정
    act.Run("TableColPageUp")
    act.Run("TableColBegin")
    act.Run("TableRightCell")
    act.Run("TableRightCell")
    act.Run("TableCellBlock")
    act.Run("TableCellBlockExtend")
    act.Run("TableLowerCell")
    act.Run("TableMergeCell")

    _exit_table(act)


# ── 발문/자료/질문/보기/선지 통합 삽입 ─────────────────
def insert_question(data, num=1, use_num=True):
    """반환값: 문항번호 자동증가가 필요하면 True (data['num']이 비어있고 use_num=True)"""
    act = hwp.HAction
    stem_cfg = S["stem"]

    if data['stem']:
        ps_s = hwp.HParameterSet
        display_num = data['num'] or str(num)
        act.GetDefault("ParagraphShape", ps_s.HParaShape.HSet)
        ps_s.HParaShape.LeftMargin    = 0
        ps_s.HParaShape.RightMargin   = 0
        ps_s.HParaShape.Indentation   = stem_cfg["indentation"]
        ps_s.HParaShape.LineSpacing   = stem_cfg["line_spacing"]
        ps_s.HParaShape.AlignType     = 0
        act.Execute("ParagraphShape", ps_s.HParaShape.HSet)
        if use_num:
            _text(f"{display_num}. {data['stem']}")
        else:
            _text(data['stem'])
        act.Run("BreakPara")
        act.GetDefault("ParagraphShape", ps_s.HParaShape.HSet)
        ps_s.HParaShape.Indentation   = 0
        act.Execute("ParagraphShape", ps_s.HParaShape.HSet)

    # 자료박스
    mtype = data.get('material_type', 'basic')
    if mtype == 'photo':
        insert_photo_box()
    elif mtype == 'experiment':
        insert_experiment_box()
    elif mtype == 'basic' and data.get('material_flag'):
        insert_material_box(data['material'])

    # 질문
    if data['question']:
        q_cfg = S["question"]
        ps2 = hwp.HParameterSet
        act.GetDefault("ParagraphShape", ps2.HParaShape.HSet)
        ps2.HParaShape.Indentation = 0
        ps2.HParaShape.PrevSpacing = q_cfg["prev_spacing"]
        ps2.HParaShape.NextSpacing = q_cfg["next_spacing"]
        act.Execute("ParagraphShape", ps2.HParaShape.HSet)
        _text("  " + data['question'])
        act.GetDefault("ParagraphShape", ps2.HParaShape.HSet)
        ps2.HParaShape.Indentation = 0
        ps2.HParaShape.PrevSpacing = 0
        ps2.HParaShape.NextSpacing = 0
        act.Execute("ParagraphShape", ps2.HParaShape.HSet)
        act.Run("BreakPara")

    # 보기박스 - 글자 수 짧은 순서 정렬
    if data['bogi']:
        sorted_bogi = sorted(data['bogi'], key=lambda x: len(x))
        insert_bogi_box(sorted_bogi)

    # 선지
    if data['choices']:
        _insert_choices(data)

    return use_num and not data['num']


def _insert_choices(data):
    """선지 - 표 기반 배치 (단 폭 균등 분할, 줄바꿈 방지)"""
    act = hwp.HAction
    ps  = hwp.HParameterSet
    circles = ["①", "②", "③", "④", "⑤"]
    ctype = data.get('choices_type', '5')
    row_h = S["choices"]["row_height_mm"]
    total_mm = _col_width_mm()
    jamo_order = ['ㄱ','ㄴ','ㄷ','ㄹ','ㅁ','ㅂ','ㅅ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']

    def fmt_choice(c):
        chars = list(c.strip())
        result = [ch2 for ch2 in chars if ch2 in jamo_order]
        return ', '.join(result) if result else c.strip()

    ch = [fmt_choice(c) for c in data['choices'][:5]]
    parts = [f"{circles[i]} {c}" for i, c in enumerate(ch)]

    def _draw_choice_table(rows, cols, layout):
        """rows×cols 투명 표. layout: {(행,열): part}. 칸은 cols 균등 분할."""
        _create_table(rows, cols, total_mm, [row_h] * rows)

        def _trans_and_text(txt):
            act.Run("TableCellBlock")
            _set_cell_border(act, ps, "None", "None", "None", "None")
            act.Run("Cancel")
            act.Run("ParagraphShapeAlignLeft")
            if txt:
                _text(txt)

        for r in range(rows):
            for c in range(cols):
                _trans_and_text(layout.get((r, c), ""))
                if not (r == rows - 1 and c == cols - 1):
                    act.Run("TableRightCell")
        _exit_table(act)

    if ctype == '1':
        act.GetDefault("ParagraphShape", ps.HParaShape.HSet)
        ps.HParaShape.Indentation = 0
        ps.HParaShape.PrevSpacing = 0
        ps.HParaShape.NextSpacing = 0
        ps.HParaShape.LeftMargin  = 0
        ps.HParaShape.AlignType   = 0
        act.Execute("ParagraphShape", ps.HParaShape.HSet)
        for i, p in enumerate(parts):
            if i > 0:
                act.Run("BreakPara")
            _text(p)
        act.Run("BreakPara")
    elif ctype == '3':
        layout = {(0, 0): parts[0], (0, 1): parts[1], (0, 2): parts[2]}
        if len(parts) > 3:
            layout[(1, 0)] = parts[3]
        if len(parts) > 4:
            layout[(1, 1)] = parts[4]
        _draw_choice_table(2, 3, layout)
        act.Run("BreakPara")
    else:  # '5'
        layout = {(0, i): parts[i] for i in range(len(parts))}
        _draw_choice_table(1, 5, layout)
        act.Run("BreakPara")


# ── 라이브러리: 서식(부분 델타) 캡처/적용 ───────────────
# CharShape 딕셔너리 키 ↔ 친화적 이름 매핑. 값 단위는 저장소(library.py)에도
# 그대로 노출되므로, 여기 바뀌면 저장된 항목의 의미도 바뀐다는 점 주의.
def _charshape_get(cs, label):
    if label == "굵게":
        return bool(cs.get("Bold"))
    if label == "기울임":
        return bool(cs.get("Italic"))
    if label == "밑줄":
        return int(cs.get("UnderlineType") or 0) != 0
    if label == "글자색":
        return cs.get("TextColor")
    if label == "자간":
        return cs.get("SpacingHangul")
    if label == "글꼴":
        return cs.get("FaceNameHangul")
    if label == "크기":
        h = cs.get("Height") or 0
        return round(h / 100, 1)
    return None


def capture_charshape(selected_labels):
    """현재 커서/선택 위치의 글자 서식에서, 체크된 항목만 델타로 캡처한다."""
    act = hwp.HAction
    ps = hwp.HParameterSet
    act.GetDefault("CharShape", ps.HCharShape.HSet)
    cs = hwp.get_charshape_as_dict()
    delta = {}
    for label in selected_labels:
        v = _charshape_get(cs, label)
        if v is not None:
            delta[label] = v
    return delta


def apply_charshape_delta(delta):
    """델타에 있는 항목만 현재 선택/커서 위치에 적용한다(그 외 서식은 그대로 유지).

    GetDefault로 대상의 '현재' 서식을 먼저 불러온 뒤, 델타에 있는 필드만
    덮어써서 Execute 한다 — 이 방식이라야 부분 적용(굵기만 바꾸고 글꼴은
    유지 등)이 보장된다.
    """
    act = hwp.HAction
    ps = hwp.HParameterSet
    act.GetDefault("CharShape", ps.HCharShape.HSet)
    if "굵게" in delta:
        ps.HCharShape.Bold = 1 if delta["굵게"] else 0
    if "기울임" in delta:
        ps.HCharShape.Italic = 1 if delta["기울임"] else 0
    if "밑줄" in delta:
        ps.HCharShape.UnderlineType = 1 if delta["밑줄"] else 0
    if "글자색" in delta:
        ps.HCharShape.TextColor = delta["글자색"]
    if "자간" in delta:
        ps.HCharShape.SpacingHangul = delta["자간"]
        ps.HCharShape.SpacingLatin = delta["자간"]
    if "글꼴" in delta:
        ps.HCharShape.FaceNameHangul = delta["글꼴"]
        ps.HCharShape.FaceNameLatin = delta["글꼴"]
    if "크기" in delta:
        ps.HCharShape.Height = hwp.PointToHwpUnit(delta["크기"])
    act.Execute("CharShape", ps.HCharShape.HSet)


# ── 라이브러리: 템플릿(통째 캡처) ───────────────────────
def auto_select_table_if_inside():
    """커서가 표 안이면(선택 없이 클릭만 한 상태) 표 전체를 선택한다.

    탈출(Cancel+CloseEx)로 본문의 표 앵커 앞에 도달한 뒤 MoveSelRight로
    앵커(글자 취급되는 표 1개)를 선택 — 실측 2026-07-15, 병합 표 재생 확인.
    반환: 선택 성공 여부.
    """
    act = hwp.HAction
    try:
        if hwp.GetPos()[0] == 0:
            return False        # 본문에 있음 — 표 안이 아님
    except Exception:
        return False
    act.Run("Cancel")
    for _ in range(8):
        try:
            if hwp.GetPos()[0] == 0:
                break
        except Exception:
            return False
        act.Run("CloseEx")
    act.Run("MoveSelRight")
    return has_selection()


def capture_fragment(dest_path):
    """현재 선택 영역을 통째로 조각 .hwp 파일로 저장한다(병합·서식 그대로)."""
    hwp.save_block_as(str(dest_path))


def insert_fragment(path):
    """조각 .hwp 파일을 커서 위치에 그대로 삽입한다.

    keep_section=0 필수 — 조각에는 저장 당시의 구역(secd) 정의가 같이 담기는데,
    이를 유지(1)하면 구역 나눔이 일어나 표가 '다음 페이지'에 생성된다(실측 2026-07-15).
    """
    hwp.insert_file(str(path), keep_section=0)


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
    return bool(act.Execute("RepeatFind", pset.HSet))


def strip_slot_markers(anchor_pos):
    r"""anchor_pos부터 문서 끝까지의 빈칸 표시(\)를 제거한다.

    빈칸 표시는 '여기에 내용이 들어간다'는 안내일 뿐이라, 채워지지 않고 남으면
    출력물에 그대로 보인다 → 삽입/변환 후 이 함수로 청소한다.
    """
    act = hwp.HAction
    hwp.SetPos(*anchor_pos)
    for _ in range(200):
        if not find_text("\\"):
            break
        act.Run("Delete")


# ── 팔레트: 기능 블럭 실행 (여러 기능 병렬) ─────────────
_TOGGLE_ACTION = {
    "굵게": "CharShapeBold",
    "기울임": "CharShapeItalic",
    "밑줄": "CharShapeUnderline",
}
_PARA_ACTION = {
    "가운데정렬": "ParagraphShapeAlignCenter",
    "왼쪽정렬": "ParagraphShapeAlignLeft",
    "양쪽정렬": "ParagraphShapeAlignJustify",
}


def execute_function_block(actions):
    """기능 블럭 실행 — actions: [{"func":이름, "value":값}, ...] 를 병렬 적용.

    값 있는 글자서식(글씨체·크기·자간·색)은 한 번의 CharShape로 묶어 적용하고,
    토글(굵게 등)과 문단정렬은 개별 Run, 줄간격은 ParagraphShape로 적용한다.
    선택 영역이 있어야 의미가 있다(호출부에서 보장).
    """
    act = hwp.HAction
    ps = hwp.HParameterSet

    char_fields = {}   # CharShape에 묶어 넣을 값들
    para_fields = {}   # ParagraphShape에 묶어 넣을 값들
    toggles = []       # Run 액션들
    para_aligns = []

    for a in actions:
        func = a.get("func")
        val = a.get("value")
        if func in _TOGGLE_ACTION:
            toggles.append(_TOGGLE_ACTION[func])
        elif func in _PARA_ACTION:
            para_aligns.append(_PARA_ACTION[func])
        elif func == "글씨체":
            char_fields["face"] = val
        elif func == "글씨크기":
            char_fields["height"] = float(val)
        elif func == "자간":
            char_fields["spacing"] = int(val)
        elif func == "글자색":
            char_fields["color"] = val
        elif func == "줄간격":
            para_fields["line_spacing"] = int(val)
        # 들여쓰기/내어쓰기는 같은 필드(Indentation)의 부호 차이 (실측 2026-07-15)
        #   양수 = 첫 줄을 안으로, 음수 = 첫 줄을 밖으로. 단위는 pt(=100 HwpUnit).
        elif func == "들여쓰기":
            para_fields["indent_pt"] = abs(float(val))
        elif func == "내어쓰기":
            para_fields["indent_pt"] = -abs(float(val))
        elif func == "왼쪽여백":
            para_fields["left_mm"] = float(val)
        elif func == "오른쪽여백":
            para_fields["right_mm"] = float(val)

    # 1) 값 있는 글자서식 묶어서 한 번에
    if char_fields:
        act.GetDefault("CharShape", ps.HCharShape.HSet)
        if "face" in char_fields:
            ps.HCharShape.FaceNameHangul = char_fields["face"]
            ps.HCharShape.FaceNameLatin = char_fields["face"]
        if "height" in char_fields:
            ps.HCharShape.Height = hwp.PointToHwpUnit(char_fields["height"])
        if "spacing" in char_fields:
            ps.HCharShape.SpacingHangul = char_fields["spacing"]
            ps.HCharShape.SpacingLatin = char_fields["spacing"]
        if "color" in char_fields:
            ps.HCharShape.TextColor = char_fields["color"]
        act.Execute("CharShape", ps.HCharShape.HSet)

    # 2) 토글 기능
    for action_id in toggles:
        act.Run(action_id)

    # 3) 문단 정렬
    for action_id in para_aligns:
        act.Run(action_id)

    # 4) 값 있는 문단서식(줄간격·들여쓰기/내어쓰기·좌우여백) 묶어서 한 번에
    if para_fields:
        act.GetDefault("ParagraphShape", ps.HParaShape.HSet)
        if "line_spacing" in para_fields:
            ps.HParaShape.LineSpacing = para_fields["line_spacing"]
            ps.HParaShape.LineSpacingType = 0
        if "indent_pt" in para_fields:
            ps.HParaShape.Indentation = hwp.PointToHwpUnit(para_fields["indent_pt"])
        if "left_mm" in para_fields:
            ps.HParaShape.LeftMargin = hwp.MiliToHwpUnit(para_fields["left_mm"])
        if "right_mm" in para_fields:
            ps.HParaShape.RightMargin = hwp.MiliToHwpUnit(para_fields["right_mm"])
        act.Execute("ParagraphShape", ps.HParaShape.HSet)


def run_block(block, template_path_fn=None):
    """팔레트 블럭 하나를 실행한다. 종류에 따라 삽입/적용 분기.

    template_path_fn: 템플릿 이름 → 조각 파일 경로 (library.template_path 등).
    반환: (성공여부, 상태메시지)
    """
    btype = block.get("type")
    if btype == "char":
        insert_plain(block.get("value", ""))
        return True, "삽입"
    if btype == "function":
        if not has_selection():
            return False, "기능은 글자를 선택한 뒤 눌러주세요"
        execute_function_block(block.get("actions", []))
        return True, "기능 적용"
    if btype == "template":
        if template_path_fn is None:
            return False, "템플릿 경로를 찾을 수 없습니다"
        name = block.get("template", "")
        path = template_path_fn(name)
        if not path:
            return False, f"템플릿을 찾을 수 없습니다: {name}"
        anchor = hwp.GetPos()
        insert_fragment(path)
        # 팔레트로 넣을 땐 채울 내용이 없으므로 빈칸 표시(\)를 모두 청소
        strip_slot_markers(anchor)
        return True, "템플릿 삽입"
    return False, f"알 수 없는 블럭: {btype}"


def apply_default_format(fmt, text=None):
    """선택 영역을 기본 서식으로 초기화(글자모양+문단모양). text 주면 교체 삽입.

    fmt: palette.get_default_format() 결과.
    """
    act = hwp.HAction
    ps = hwp.HParameterSet
    if text is not None:
        delete_selection()
    act.Run("StyleClearCharShape")

    act.GetDefault("CharShape", ps.HCharShape.HSet)
    ps.HCharShape.FaceNameHangul = fmt.get("font", "함초롬바탕")
    ps.HCharShape.FaceNameLatin = fmt.get("font", "함초롬바탕")
    ps.HCharShape.Height = hwp.PointToHwpUnit(fmt.get("size_pt", 10.0))
    ps.HCharShape.SpacingHangul = fmt.get("spacing", 0)
    ps.HCharShape.SpacingLatin = fmt.get("spacing", 0)
    # StyleClearCharShape만으로는 굵게/기울임/밑줄이 남을 수 있어 명시적으로 끔
    ps.HCharShape.Bold = 0
    ps.HCharShape.Italic = 0
    ps.HCharShape.UnderlineType = 0
    ps.HCharShape.TextColor = hwp.rgb_color(0, 0, 0)
    act.Execute("CharShape", ps.HCharShape.HSet)

    act.GetDefault("ParagraphShape", ps.HParaShape.HSet)
    ps.HParaShape.LineSpacing = fmt.get("line_spacing", 160)
    ps.HParaShape.LineSpacingType = 0
    ps.HParaShape.Indentation = 0
    ps.HParaShape.LeftMargin = 0
    ps.HParaShape.RightMargin = 0
    ps.HParaShape.PrevSpacing = 0
    ps.HParaShape.NextSpacing = 0
    ps.HParaShape.AlignType = fmt.get("align", 0)
    act.Execute("ParagraphShape", ps.HParaShape.HSet)

    if text is not None:
        insert_plain(text)


# ── 라이브러리: 마크다운(\라벨\) 변환 실행 ───────────────
def execute_library_plan(ops, template_path_fn):
    """parser.build_library_plan()의 실행 계획을 문서에 반영한다.

    호출 전에 선택 영역은 삭제돼 있어야 한다(커서 = 삽입 지점).

    2단계 방식: ① 텍스트 줄과 '템플릿 자리표시 마커'를 순서대로 삽입 →
    ② 마커를 찾아 조각으로 바꾸고, 이어서 빈칸(\\)을 아랫줄 내용으로 채움.
    한 번에 삽입하지 않는 이유: insert_file 직후 커서가 조각 뒤로 이동하지
    않아(실측) 순차 삽입 순서가 꼬이기 때문 — 마커 방식이 순서를 보장한다.
    """
    import time as _time
    act = hwp.HAction
    marker_base = "◈LIB%d_" % (int(_time.time() * 1000) % 10**9)

    # ① 텍스트/마커 순차 삽입
    templates = []
    first = True
    for op in ops:
        if not first:
            act.Run("BreakPara")
        first = False
        if op[0] == "line":
            if op[1]:
                insert_plain(op[1])
        else:                               # ('template', item, fills)
            insert_plain(marker_base + str(len(templates)) + "◈")
            templates.append(op)

    # ② 마커 → 조각 치환 + 빈칸(\) 순서대로 채움
    filled = 0
    for idx, (_, item, fills) in enumerate(templates):
        marker = marker_base + str(idx) + "◈"
        hwp.MoveDocBegin()
        if not find_text(marker):
            continue                        # 마커 유실 — 이 템플릿은 건너뜀
        delete_selection()
        anchor = hwp.GetPos()
        insert_fragment(template_path_fn(item))
        # 빈칸 \ 를 위에서부터 차례로. 값이 None('-')이면 그 칸은 비워둔다.
        hwp.SetPos(*anchor)
        for value in fills:
            if not find_text("\\"):
                break
            if value is None:
                act.Run("Delete")           # 건너뛰기 — 빈칸만 지움
            else:
                insert_plain(value)
                filled += 1
        # 채우지 않고 남은 빈칸 표시(\) 청소 — 출력물에 남으면 안 됨
        strip_slot_markers(anchor)
    return {"templates": len(templates), "slots_filled": filled}
