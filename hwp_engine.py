# -*- coding: utf-8 -*-
"""한컴 자동화(pyhwpx) 엔진 — Tkinter/UI에 의존하지 않는다.

표/박스의 모든 치수·글꼴·테두리는 활성 스펙(S)에서 읽는다. S는 settings.py의
프리셋에서 온다. 실패는 예외로 올라간다. 메시지박스/상태표시는 호출부의 책임.
"""

from pyhwpx import Hwp
import settings

hwp = None

# 활성 스펙(프리셋). main.py가 시작 시 set_active_spec()으로 주입한다.
S = settings.default_spec()


def set_active_spec(spec):
    """설정 창에서 프리셋을 바꾸거나 저장하면 호출된다."""
    global S
    S = spec


def connect():
    """이미 연결돼 있으면 재사용, 아니면 새로 연결. 실패 시 예외 발생."""
    global hwp
    try:
        _ = hwp.Version
        return hwp
    except Exception:
        hwp = Hwp()
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
    act.Run("CloseEx")
    act.Run("MoveDown")
    act.Run("MoveLineEnd")


def _create_table(rows, cols, total_mm, row_heights_mm):
    """rows×cols 표 생성. 열은 total_mm를 균등 분할(단 폭 하나에서 자동 계산)."""
    act = hwp.HAction
    ps  = hwp.HParameterSet
    act.GetDefault("TableCreate", ps.HTableCreation.HSet)
    ps.HTableCreation.Rows       = rows
    ps.HTableCreation.Cols       = cols
    ps.HTableCreation.WidthType  = 0
    ps.HTableCreation.HeightType = 1
    ps.HTableCreation.WidthValue = _mm(total_mm)
    ps.HTableCreation.CreateItemArray("ColWidth", cols)
    # 균등 분할하되 반올림 오차를 마지막 칸에서 흡수
    each = total_mm / cols
    acc = 0.0
    for i in range(cols):
        w = (total_mm - acc) if i == cols - 1 else each
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
