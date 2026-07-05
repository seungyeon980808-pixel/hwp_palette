# -*- coding: utf-8 -*-
"""한컴 자동화(pyhwpx) 엔진 — Tkinter/UI에 의존하지 않는다.
실패는 예외로 올라간다. 메시지박스/상태표시는 호출부(main.py)의 책임."""

from pyhwpx import Hwp

hwp = None


def connect():
    """이미 연결돼 있으면 재사용, 아니면 새로 연결. 실패 시 예외 발생."""
    global hwp
    try:
        _ = hwp.Version
        return hwp
    except Exception:
        hwp = Hwp()
        return hwp


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


def insert_plain(text):
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


# ── 표/박스 내부 공통 헬퍼 ─────────────────────────────
def _make_transparent_border(act, ps):
    act.GetDefault("CellBorderFill", ps.HCellBorderFill.HSet)
    ps.HCellBorderFill.BorderTypeBottom = hwp.HwpLineType("None")
    ps.HCellBorderFill.BorderTypeTop    = hwp.HwpLineType("None")
    ps.HCellBorderFill.BorderTypeRight  = hwp.HwpLineType("None")
    ps.HCellBorderFill.BorderTypeLeft   = hwp.HwpLineType("None")
    act.Execute("CellBorderFill", ps.HCellBorderFill.HSet)


def _make_solid_border(act, ps):
    act.GetDefault("CellBorderFill", ps.HCellBorderFill.HSet)
    ps.HCellBorderFill.BorderTypeBottom = hwp.HwpLineType("Solid")
    ps.HCellBorderFill.BorderTypeTop    = hwp.HwpLineType("Solid")
    ps.HCellBorderFill.BorderTypeRight  = hwp.HwpLineType("Solid")
    ps.HCellBorderFill.BorderTypeLeft   = hwp.HwpLineType("Solid")
    act.Execute("CellBorderFill", ps.HCellBorderFill.HSet)


def _exit_table(act):
    act.Run("CloseEx")
    act.Run("MoveDown")
    act.Run("MoveLineEnd")


# ── 자료박스 ───────────────────────────────────────────
def insert_material_box(text):
    # 자료: - 93.99mm, 2행2열 투명, 1행 높이 45mm / 2행 높이 5mm
    act = hwp.HAction
    ps  = hwp.HParameterSet
    act.GetDefault("TableCreate", ps.HTableCreation.HSet)
    ps.HTableCreation.Rows       = 2
    ps.HTableCreation.Cols       = 2
    ps.HTableCreation.WidthType  = 0
    ps.HTableCreation.HeightType = 1
    ps.HTableCreation.WidthValue = hwp.MiliToHwpUnit(93.99)
    ps.HTableCreation.CreateItemArray("ColWidth", 2)
    ps.HTableCreation.ColWidth.SetItem(0, hwp.MiliToHwpUnit(46.99))
    ps.HTableCreation.ColWidth.SetItem(1, hwp.MiliToHwpUnit(47.0))
    ps.HTableCreation.CreateItemArray("RowHeight", 2)
    ps.HTableCreation.RowHeight.SetItem(0, hwp.MiliToHwpUnit(45.0))
    ps.HTableCreation.RowHeight.SetItem(1, hwp.MiliToHwpUnit(5.0))
    act.Execute("TableCreate", ps.HTableCreation.HSet)

    def _trans():
        act.Run("TableCellBlock")
        _make_transparent_border(act, ps)
        act.Run("Cancel")

    _trans()                    # 1행1열 (현재 위치)
    act.Run("TableRightCell")   # 1행2열
    _trans()
    act.Run("TableRightCell")   # 2행1열로 이동
    _trans()
    act.Run("TableRightCell")   # 2행2열
    _trans()
    act.Run("TableLeftCell")    # 1행1열로 복귀
    act.Run("TableLeftCell")
    act.Run("TableLeftCell")
    hwp.insert_text(text)
    _exit_table(act)


def insert_photo_box():
    # 사진자료: - 2행2열, 93.99mm, 전체 투명, 1행 높이 50mm / 2행 높이 10mm
    act = hwp.HAction
    ps  = hwp.HParameterSet
    act.GetDefault("TableCreate", ps.HTableCreation.HSet)
    ps.HTableCreation.Rows       = 2
    ps.HTableCreation.Cols       = 2
    ps.HTableCreation.WidthType  = 0
    ps.HTableCreation.HeightType = 1
    ps.HTableCreation.WidthValue = hwp.MiliToHwpUnit(93.99)
    ps.HTableCreation.CreateItemArray("ColWidth", 2)
    ps.HTableCreation.ColWidth.SetItem(0, hwp.MiliToHwpUnit(46.99))
    ps.HTableCreation.ColWidth.SetItem(1, hwp.MiliToHwpUnit(47.0))
    ps.HTableCreation.CreateItemArray("RowHeight", 2)
    ps.HTableCreation.RowHeight.SetItem(0, hwp.MiliToHwpUnit(45.0))
    ps.HTableCreation.RowHeight.SetItem(1, hwp.MiliToHwpUnit(7.0))
    act.Execute("TableCreate", ps.HTableCreation.HSet)

    def _trans_center():
        act.Run("TableCellBlock")
        _make_transparent_border(act, ps)
        act.Run("Cancel")
        act.Run("ParagraphShapeAlignCenter")

    _trans_center()
    act.Run("TableRightCell"); _trans_center()
    act.Run("TableRightCell"); _trans_center()
    act.Run("TableRightCell"); _trans_center()
    _exit_table(act)


def insert_experiment_box():
    # 실험자료: - 93.99mm 실선 1칸, 높이 80mm, [실험 과정] 텍스트
    act = hwp.HAction
    ps  = hwp.HParameterSet
    act.GetDefault("TableCreate", ps.HTableCreation.HSet)
    ps.HTableCreation.Rows       = 1
    ps.HTableCreation.Cols       = 1
    ps.HTableCreation.WidthType  = 0
    ps.HTableCreation.HeightType = 1
    ps.HTableCreation.WidthValue = hwp.MiliToHwpUnit(93.99)
    ps.HTableCreation.CreateItemArray("RowHeight", 1)
    ps.HTableCreation.RowHeight.SetItem(0, hwp.MiliToHwpUnit(80.0))
    act.Execute("TableCreate", ps.HTableCreation.HSet)
    act.Run("TableCellBlock")
    _make_solid_border(act, ps)
    act.Run("Cancel")
    hwp.insert_text("[실험 과정]")
    _exit_table(act)


# ── 보기박스 ───────────────────────────────────────────
def insert_bogi_box(items=None):
    """〈보 기〉 박스 — 박승연 선생님 키로그 기반 구조

    키로그:
        표생성
        에에에전테엔       → 전체 테두리 삭제
        에에상좌좌좌좌바테엔 → 2~3행 바깥 테두리
        우우에에병합<보기>  → 3열 병합 후 〈보기〉
        아좌좌에에우우우우병합 → 3행 전체 병합 후 ㄱㄴㄷ
        1행3열+2행3열 병합  → 〈보기〉 위치 확정
    """
    act = hwp.HAction
    ps  = hwp.HParameterSet

    # 표 생성 (3행 5열, 너비 93.99mm)
    act.GetDefault("TableCreate", ps.HTableCreation.HSet)
    ps.HTableCreation.Rows       = 3
    ps.HTableCreation.Cols       = 5
    ps.HTableCreation.WidthType  = 0
    ps.HTableCreation.HeightType = 1
    ps.HTableCreation.WidthValue = hwp.MiliToHwpUnit(93.99)
    ps.HTableCreation.CreateItemArray("ColWidth", 5)
    ps.HTableCreation.ColWidth.SetItem(0, hwp.MiliToHwpUnit(19.2))
    ps.HTableCreation.ColWidth.SetItem(1, hwp.MiliToHwpUnit(19.2))
    ps.HTableCreation.ColWidth.SetItem(2, hwp.MiliToHwpUnit(19.2))
    ps.HTableCreation.ColWidth.SetItem(3, hwp.MiliToHwpUnit(19.2))
    ps.HTableCreation.ColWidth.SetItem(4, hwp.MiliToHwpUnit(19.2))
    ps.HTableCreation.CreateItemArray("RowHeight", 3)
    ps.HTableCreation.RowHeight.SetItem(0, hwp.MiliToHwpUnit(3.0))
    ps.HTableCreation.RowHeight.SetItem(1, hwp.MiliToHwpUnit(3.0))
    ps.HTableCreation.RowHeight.SetItem(2, hwp.MiliToHwpUnit(20.0))
    act.Execute("TableCreate", ps.HTableCreation.HSet)

    # 전체 테두리 삭제
    act.Run("TableCellBlock")
    act.Run("TableCellBlockExtend")
    act.Run("TableCellBlockExtend")
    act.GetDefault("CellBorderFill", ps.HCellBorderFill.HSet)
    ps.HCellBorderFill.BorderTypeBottom = hwp.HwpLineType("None")
    ps.HCellBorderFill.BorderTypeTop    = hwp.HwpLineType("None")
    ps.HCellBorderFill.BorderTypeRight  = hwp.HwpLineType("None")
    ps.HCellBorderFill.BorderTypeLeft   = hwp.HwpLineType("None")
    act.Execute("CellBorderFill", ps.HCellBorderFill.HSet)
    act.GetDefault("CellBorderFill", ps.HCellBorderFill.HSet)
    ps.HCellBorderFill.TypeVert = hwp.HwpLineType("None")
    ps.HCellBorderFill.TypeHorz = hwp.HwpLineType("None")
    act.Execute("CellBorderFill", ps.HCellBorderFill.HSet)
    act.Run("Cancel")

    # 2~3행 바깥 테두리
    act.Run("TableCellBlock")
    act.Run("TableCellBlockExtend")
    act.Run("TableUpperCell")
    act.Run("TableLeftCell")
    act.Run("TableLeftCell")
    act.Run("TableLeftCell")
    act.Run("TableLeftCell")
    act.GetDefault("CellBorderFill", ps.HCellBorderFill.HSet)
    ps.HCellBorderFill.BorderTypeTop    = hwp.HwpLineType("Solid")
    ps.HCellBorderFill.BorderTypeBottom = hwp.HwpLineType("Solid")
    ps.HCellBorderFill.BorderTypeLeft   = hwp.HwpLineType("Solid")
    ps.HCellBorderFill.BorderTypeRight  = hwp.HwpLineType("Solid")
    act.Execute("CellBorderFill", ps.HCellBorderFill.HSet)
    act.Run("Cancel")

    # 3열 병합 후 〈보기〉
    act.Run("TableRightCell")
    act.Run("TableRightCell")
    act.Run("TableCellBlock")
    act.Run("TableCellBlockExtend")
    act.Run("TableMergeCell")
    act.Run("ParagraphShapeAlignCenter")
    hwp.insert_text("〈보 기〉")

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

    # ㄱㄴㄷ 입력
    hwp.set_cell_margin(left=2.0, right=2.0, top=0.5, bottom=4.0, as_="mm")
    act.Run("ParagraphShapeAlignJustify")
    act.GetDefault("ParagraphShape", ps.HParaShape.HSet)
    ps.HParaShape.LineSpacing     = 130
    ps.HParaShape.LineSpacingType = 0
    act.Execute("ParagraphShape", ps.HParaShape.HSet)
    if items:
        labels = ["ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ"]
        real = [it for it in items if it.strip()]
        for i, item in enumerate(real[:5]):
            if i > 0:
                act.Run("BreakPara")
            hwp.insert_text(f"{labels[i]}. ")
            act.Run("Indent")   # Alt+Shift+Tab 들여쓰기
            hwp.insert_text(item)
    else:
        for i, label in enumerate(["ㄱ", "ㄴ", "ㄷ"]):
            if i > 0:
                act.Run("BreakPara")
            hwp.insert_text(f"{label}. ")
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

    if data['stem']:
        ps_s = hwp.HParameterSet
        display_num = data['num'] or str(num)
        act.GetDefault("ParagraphShape", ps_s.HParaShape.HSet)
        ps_s.HParaShape.LeftMargin    = 0
        ps_s.HParaShape.RightMargin   = 0
        ps_s.HParaShape.Indentation   = -399
        ps_s.HParaShape.LineSpacing   = 150
        ps_s.HParaShape.AlignType     = 0
        act.Execute("ParagraphShape", ps_s.HParaShape.HSet)
        if use_num:
            hwp.insert_text(f"{display_num}. {data['stem']}")
        else:
            hwp.insert_text(data['stem'])
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
        ps2 = hwp.HParameterSet
        act.GetDefault("ParagraphShape", ps2.HParaShape.HSet)
        ps2.HParaShape.Indentation = 0
        ps2.HParaShape.PrevSpacing = 800   # 위 간격 약 4pt
        ps2.HParaShape.NextSpacing = 400   # 아래 간격 약 2pt
        act.Execute("ParagraphShape", ps2.HParaShape.HSet)
        hwp.insert_text("  " + data['question'])
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
    """선지 - 표 기반 배치 (길이 비례 칸폭, 줄바꿈 방지)"""
    act = hwp.HAction
    circles = ["①", "②", "③", "④", "⑤"]
    ctype = data.get('choices_type', '5')
    jamo_order = ['ㄱ','ㄴ','ㄷ','ㄹ','ㅁ','ㅂ','ㅅ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']

    def fmt_choice(c):
        chars = list(c.strip())
        result = [ch2 for ch2 in chars if ch2 in jamo_order]
        return ', '.join(result) if result else c.strip()

    ch = [fmt_choice(c) for c in data['choices'][:5]]
    parts = [f"{circles[i]} {c}" for i, c in enumerate(ch)]

    TOTAL_MM = 93.99

    def _draw_choice_table(rows, cols, layout):
        """rows×cols 투명 표를 만들어 layout대로 선지 텍스트 입력.
        layout: {(행,열): part문자열} — 없는 칸은 빈칸.
        칸은 cols 균등 분할(위아래 같은 열이 정확히 정렬됨)."""
        col_w = TOTAL_MM / cols
        ps_c = hwp.HParameterSet
        act.GetDefault("TableCreate", ps_c.HTableCreation.HSet)
        ps_c.HTableCreation.Rows       = rows
        ps_c.HTableCreation.Cols       = cols
        ps_c.HTableCreation.WidthType  = 0
        ps_c.HTableCreation.HeightType = 1
        ps_c.HTableCreation.WidthValue = hwp.MiliToHwpUnit(TOTAL_MM)
        ps_c.HTableCreation.CreateItemArray("ColWidth", cols)
        for i in range(cols):
            ps_c.HTableCreation.ColWidth.SetItem(i, hwp.MiliToHwpUnit(col_w))
        ps_c.HTableCreation.CreateItemArray("RowHeight", rows)
        for i in range(rows):
            ps_c.HTableCreation.RowHeight.SetItem(i, hwp.MiliToHwpUnit(6.0))
        act.Execute("TableCreate", ps_c.HTableCreation.HSet)

        def _trans_and_text(txt):
            act.Run("TableCellBlock")
            act.GetDefault("CellBorderFill", ps_c.HCellBorderFill.HSet)
            ps_c.HCellBorderFill.BorderTypeBottom = hwp.HwpLineType("None")
            ps_c.HCellBorderFill.BorderTypeTop    = hwp.HwpLineType("None")
            ps_c.HCellBorderFill.BorderTypeRight  = hwp.HwpLineType("None")
            ps_c.HCellBorderFill.BorderTypeLeft   = hwp.HwpLineType("None")
            act.Execute("CellBorderFill", ps_c.HCellBorderFill.HSet)
            act.Run("Cancel")
            act.Run("ParagraphShapeAlignLeft")
            if txt:
                hwp.insert_text(txt)

        for r in range(rows):
            for c in range(cols):
                _trans_and_text(layout.get((r, c), ""))
                if not (r == rows - 1 and c == cols - 1):
                    act.Run("TableRightCell")
        _exit_table(act)

    if ctype == '1':
        ps_c = hwp.HParameterSet
        act.GetDefault("ParagraphShape", ps_c.HParaShape.HSet)
        ps_c.HParaShape.Indentation = 0
        ps_c.HParaShape.PrevSpacing = 0
        ps_c.HParaShape.NextSpacing = 0
        ps_c.HParaShape.LeftMargin  = 0
        ps_c.HParaShape.AlignType   = 0
        act.Execute("ParagraphShape", ps_c.HParaShape.HSet)
        for i, p in enumerate(parts):
            if i > 0:
                act.Run("BreakPara")
            hwp.insert_text(p)
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
