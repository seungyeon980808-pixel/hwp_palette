# -*- coding: utf-8 -*-
r"""커스텀 팔레트 — 사용자가 만드는 탭 + 블럭.

메인 창의 고정 도구(원문자·보기박스·빠른입력 등)를 없애고, 대신 사용자가
탭을 만들어 원하는 블럭을 배치한다. 블럭은 클릭하면 실행되는 최소 단위:

  블럭 = {type, span, ...}
    문자    {"type":"char",     "value":"√",        "span":1}
    템플릿  {"type":"template",  "template":"결재란", "span":2}
    기능    {"type":"function",  "name":"내 강조",
             "actions":[{"func":"글씨체","value":"굴림"}, ...], "span":1}

  탭   = {"name":..., "cols":5, "blocks":[블럭, ...]}

저장은 settings.config(config.json)의 "palette_tabs" 키. 개인 로컬 데이터.
기본 서식(‘기본 서식으로 변환’ 대상)은 "default_format" 키.

이 두 키의 **소유자는 이 모듈**이다 (개선안 21). settings.py 는 같은 파일의
"profiles"/"active_profile" 을 소유한다. 전체 소유권 표는
settings.CONFIG_KEY_OWNERS 에 있다. 파일 입출력은 settings 의
get_config_value/set_config_value 만 거친다 — 읽고 쓰는 코드를 두 벌 두지 않기 위함.
"""

import copy
import applog
import settings

TABS_KEY = "palette_tabs"
DEFAULT_FORMAT_KEY = "default_format"
DEFAULT_COLS = 15       # 격자 가로 칸 수. 칸 크기는 폭에 맞춰 정해진다(정사각형).

# 블럭은 격자 위의 사각형이다: (row, col) 에서 span×rows 칸을 차지한다.
#   span = 가로 칸 수, rows = 세로 줄 수
# 예전에는 좌표 없이 목록 순서대로 흘려 배치했는데, 그러면 '세로로 큰 블럭'을
# 만들 수 없었다(줄을 건너뛰는 개념이 없으므로). 2026-07-19 좌표 방식으로 전환.
BLOCK_POS_KEYS = ("row", "col", "span", "rows")

DEFAULT_FORMAT = {
    "font": "함초롬바탕",
    "size_pt": 10.0,
    "line_spacing": 160,   # %
    "align": 0,            # 0=왼쪽/양쪽 기본
    "spacing": 0,          # 자간
}


# ── 탭 ─────────────────────────────────────────────────
def _seed_tabs():
    """새 설치: 기존 빠른입력 기호를 '빠른입력' 탭의 문자 블럭으로 이관."""
    blocks = []
    for sym in settings.get_quick_buttons():
        if sym and sym.strip():
            blocks.append({"type": "char", "value": sym, "span": 1})
    return [{"name": "빠른입력", "cols": DEFAULT_COLS, "blocks": blocks}]


def load_tabs():
    tabs = settings.get_config_value(TABS_KEY, None)
    if not isinstance(tabs, list) or not tabs:
        tabs = _seed_tabs()
        save_tabs(tabs)
    # 하위호환 기본값
    migrated = False
    for t in tabs:
        t.setdefault("cols", DEFAULT_COLS)
        t.setdefault("blocks", [])
        if _migrate_positions(t):
            migrated = True
        for b in t["blocks"]:
            b.setdefault("span", 2 if b.get("type") == "template" else 1)
            # 구 데이터: 템플릿을 '이름'으로 참조 → 고유 id(ref)로 이전.
            # 이름으로 참조하면 이름 변경/중복 시 연결이 끊긴다.
            if (b.get("type") == "template" and not b.get("ref")
                    and b.get("template") and _migrate_template_ref(b)):
                migrated = True
    if migrated:
        save_tabs(tabs)
    return tabs


def _migrate_positions(tab):
    """구 데이터(좌표 없음)를 흐름 배치 순서 그대로 (row, col) 로 굳힌다.

    예전에는 블럭 목록 순서대로 왼→오, 넘치면 다음 줄로 흘려 배치했다. 그 결과와
    똑같이 보이도록 좌표를 매겨 두면, 사용자가 보던 배치가 그대로 유지된다.
    반환: 바뀐 게 있으면 True.
    """
    blocks = tab.get("blocks", [])
    if all("row" in b and "col" in b for b in blocks):
        return False
    cols = max(1, int(tab.get("cols", DEFAULT_COLS)))
    r = c = 0
    for b in blocks:
        span = max(1, min(int(b.get("span", 1)), cols))
        if c + span > cols:
            r += 1
            c = 0
        b["row"], b["col"] = r, c
        b["span"], b["rows"] = span, max(1, int(b.get("rows", 1)))
        c += span
        if c >= cols:
            r += 1
            c = 0
    return True


def occupied_cells(blocks, skip_index=None):
    """블럭들이 차지한 칸 집합 {(row, col), ...}."""
    used = set()
    for i, b in enumerate(blocks):
        if i == skip_index:
            continue
        r0, c0 = int(b.get("row", 0)), int(b.get("col", 0))
        for dr in range(max(1, int(b.get("rows", 1)))):
            for dc in range(max(1, int(b.get("span", 1)))):
                used.add((r0 + dr, c0 + dc))
    return used


def area_is_free(blocks, row, col, span, rows, skip_index=None):
    """그 사각형이 비어 있는가 (다른 블럭과 안 겹치는가)."""
    used = occupied_cells(blocks, skip_index)
    return all((row + dr, col + dc) not in used
               for dr in range(rows) for dc in range(span))


def find_free_spot(blocks, cols, span=1, rows=1, max_rows=200):
    """span×rows 가 들어갈 첫 빈자리 (row, col). 못 찾으면 맨 아래 새 줄."""
    used = occupied_cells(blocks)
    for r in range(max_rows):
        for c in range(cols - span + 1):
            if all((r + dr, c + dc) not in used
                   for dr in range(rows) for dc in range(span)):
                return r, c
    bottom = max((int(b.get("row", 0)) + int(b.get("rows", 1))
                  for b in blocks), default=0)
    return bottom, 0


def _migrate_template_ref(block):
    """{'template': '결재란'} → {'ref': <id>} 로 이전. 성공 시 True.

    library 를 최상위에서 import 하면 순환 참조라 지역 import.
    """
    try:
        import library         # 순환 참조 회피 (library → palette → library)
        for it in library.load().get("템플릿", []):
            if it.get("name") == block.get("template"):
                block["ref"] = it["id"]
                return True
        applog.warn(f"팔레트 블럭이 가리키는 템플릿을 못 찾음: "
                    f"{block.get('template')!r} (삭제된 것 같음)")
    except Exception as e:
        applog.exc("팔레트 블럭 ref 마이그레이션 실패", e)
    return False


def save_tabs(tabs):
    settings.set_config_value(TABS_KEY, tabs)


def add_tab(name, cols=DEFAULT_COLS):
    tabs = load_tabs()
    name = _unique_tab_name(tabs, name or "새 탭")
    tabs.append({"name": name, "cols": cols, "blocks": []})
    save_tabs(tabs)
    return name


def _unique_tab_name(tabs, name):
    existing = {t["name"] for t in tabs}
    if name not in existing:
        return name
    n = 2
    while f"{name} ({n})" in existing:
        n += 1
    return f"{name} ({n})"


def rename_tab(index, new_name):
    tabs = load_tabs()
    if 0 <= index < len(tabs):
        others = [t["name"] for i, t in enumerate(tabs) if i != index]
        if new_name in others:
            raise ValueError(f"이미 있는 탭 이름입니다: {new_name}")
        tabs[index]["name"] = new_name
        save_tabs(tabs)


def delete_tab(index):
    tabs = load_tabs()
    if 0 <= index < len(tabs):
        del tabs[index]
        save_tabs(tabs)


def move_tab(index, delta):
    tabs = load_tabs()
    j = index + delta
    if 0 <= index < len(tabs) and 0 <= j < len(tabs):
        tabs[index], tabs[j] = tabs[j], tabs[index]
        save_tabs(tabs)


def set_tab_cols(index, cols):
    tabs = load_tabs()
    if 0 <= index < len(tabs):
        tabs[index]["cols"] = max(1, int(cols))
        save_tabs(tabs)


# ── 블럭 ───────────────────────────────────────────────
def add_block(tab_index, block, row=None, col=None):
    """블럭을 추가한다. 자리를 안 주면 첫 빈자리를 찾아 넣는다."""
    tabs = load_tabs()
    if not (0 <= tab_index < len(tabs)):
        return
    tab = tabs[tab_index]
    blocks = tab["blocks"]
    b = copy.deepcopy(block)
    b["span"] = max(1, int(b.get("span", 1)))
    b["rows"] = max(1, int(b.get("rows", 1)))
    if row is None or col is None:
        row, col = find_free_spot(blocks, tab.get("cols", DEFAULT_COLS),
                                  b["span"], b["rows"])
    b["row"], b["col"] = int(row), int(col)
    blocks.append(b)
    save_tabs(tabs)


def set_block_area(tab_index, block_index, row, col, span, rows):
    """블럭의 자리·크기를 한 번에 정한다. 겹치면 아무것도 하지 않고 False."""
    tabs = load_tabs()
    if not (0 <= tab_index < len(tabs)):
        return False
    blocks = tabs[tab_index]["blocks"]
    if not (0 <= block_index < len(blocks)):
        return False
    cols = tabs[tab_index].get("cols", DEFAULT_COLS)
    span, rows = max(1, min(int(span), cols)), max(1, int(rows))
    col = max(0, min(int(col), cols - span))
    row = max(0, int(row))
    if not area_is_free(blocks, row, col, span, rows, skip_index=block_index):
        return False
    b = blocks[block_index]
    b["row"], b["col"], b["span"], b["rows"] = row, col, span, rows
    save_tabs(tabs)
    return True


def grid_extent(blocks):
    """블럭들이 쓰는 줄 수 (맨 아래 줄 + 1)."""
    return max((int(b.get("row", 0)) + max(1, int(b.get("rows", 1)))
                for b in blocks), default=0)


def update_block(tab_index, block_index, block):
    tabs = load_tabs()
    if 0 <= tab_index < len(tabs) and 0 <= block_index < len(tabs[tab_index]["blocks"]):
        tabs[tab_index]["blocks"][block_index] = copy.deepcopy(block)
        save_tabs(tabs)


def delete_block(tab_index, block_index):
    tabs = load_tabs()
    if 0 <= tab_index < len(tabs) and 0 <= block_index < len(tabs[tab_index]["blocks"]):
        del tabs[tab_index]["blocks"][block_index]
        save_tabs(tabs)


def move_block(tab_index, block_index, delta):
    tabs = load_tabs()
    if not (0 <= tab_index < len(tabs)):
        return
    blocks = tabs[tab_index]["blocks"]
    j = block_index + delta
    if 0 <= block_index < len(blocks) and 0 <= j < len(blocks):
        blocks[block_index], blocks[j] = blocks[j], blocks[block_index]
        save_tabs(tabs)


def move_block_to(tab_index, block_index, new_index):
    """드래그 재배치 — block_index 블럭을 new_index 위치로 이동."""
    tabs = load_tabs()
    if not (0 <= tab_index < len(tabs)):
        return
    blocks = tabs[tab_index]["blocks"]
    if not (0 <= block_index < len(blocks)):
        return
    new_index = max(0, min(new_index, len(blocks) - 1))
    b = blocks.pop(block_index)
    blocks.insert(new_index, b)
    save_tabs(tabs)


# ── 기본 서식 ───────────────────────────────────────────
def get_default_format():
    saved = settings.get_config_value(DEFAULT_FORMAT_KEY, None) or {}
    fmt = copy.deepcopy(DEFAULT_FORMAT)
    fmt.update({k: v for k, v in saved.items() if k in DEFAULT_FORMAT})
    return fmt


def save_default_format(fmt):
    settings.set_config_value(DEFAULT_FORMAT_KEY, fmt)
