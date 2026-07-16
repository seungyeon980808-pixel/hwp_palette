# -*- coding: utf-8 -*-
"""개인 라이브러리 저장소 — 서식 / 문자 / 템플릿 3종.

- 서식: 굵기·색상·자간 등 글자 서식 일부만 저장해 아무 글자에나 입히는 "델타"
- 문자: 특수문자·상용구 등 텍스트 그대로 저장해 삽입
- 템플릿: 표·결재란처럼 완성된 덩어리를 통째로 조각 파일(.hwp)로 저장해 삽입

library.json에 목록/이름/값을 저장한다(개인 파일, git 추적 제외).
템플릿의 실제 내용은 fragments/ 폴더에 개별 .hwp 조각으로 저장하고,
library.json에는 그 파일명만 참조로 남긴다.
"""

import copy
import json
import pathlib
import uuid

LIBRARY_PATH = pathlib.Path(__file__).parent / "library.json"
FRAGMENTS_DIR = pathlib.Path(__file__).parent / "fragments"

CATEGORIES = ("서식", "문자", "템플릿")

_EMPTY = {"서식": [], "문자": [], "템플릿": []}


def _ensure_dirs():
    FRAGMENTS_DIR.mkdir(exist_ok=True)


DEFAULT_GROUP = "기본"


def load():
    try:
        data = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    out = copy.deepcopy(_EMPTY)
    migrated = False
    for cat in CATEGORIES:
        if isinstance(data.get(cat), list):
            out[cat] = data[cat]
        # 하위호환: 예전 항목에 id/라벨/분류(/슬롯수) 기본값 채움
        for it in out[cat]:
            # 고유 id — 팔레트 블럭이 이걸로 참조한다. 이름을 바꿔도 연결이 유지됨.
            if not it.get("id"):
                it["id"] = uuid.uuid4().hex
                migrated = True
            it.setdefault("label", it.get("name", ""))
            it.setdefault("group", DEFAULT_GROUP)
            # 이미 \라벨\ 로 저장돼 있던 항목도 알맹이로 교정 (조회 실패 방지)
            it["label"] = normalize_label(it.get("label")) or it.get("name", "")
            if cat == "템플릿":
                it.setdefault("slot_count", 0)
                it.pop("slot_names", None)   # 이름 빈칸 기능 폐지 (2026-07-16)
    if migrated:
        save(out)          # id를 새로 부여했으면 즉시 영속화
    return out


def find_by_id(category, item_id):
    for it in load().get(category, []):
        if it.get("id") == item_id:
            return it
    return None


def get_item(category, item_id=None, name=None):
    """id 우선, 없으면 이름으로 조회 (구 데이터 하위호환)."""
    items = load().get(category, [])
    if item_id:
        for it in items:
            if it.get("id") == item_id:
                return it
    if name:
        for it in items:
            if it.get("name") == name:
                return it
    return None


def save(data):
    _ensure_dirs()
    LIBRARY_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_items(category):
    return load().get(category, [])


def _unique_name(items, name):
    existing = {it["name"] for it in items}
    if name not in existing:
        return name
    n = 2
    while f"{name} ({n})" in existing:
        n += 1
    return f"{name} ({n})"


def normalize_label(label):
    r"""라벨에서 감싼 역슬래시를 벗겨낸다.

    사용자는 문서에 쓰는 그대로 `\계획서표지\` 라고 입력하기 쉬운데, 저장은
    알맹이(`계획서표지`)여야 조회가 된다(안 그러면 영원히 매칭 실패).
    """
    return (label or "").strip().strip("\\").strip()


def _meta(name, label, group):
    lab = normalize_label(label) or normalize_label(name) or name.strip()
    return {"id": uuid.uuid4().hex,
            "name": name,
            "label": lab,
            "group": (group or DEFAULT_GROUP).strip() or DEFAULT_GROUP}


def add_style(name, fields, label=None, group=None):
    """fields: {친화적필드명: 값} — 캡처 시 선택된 항목만 들어있는 델타.
    반환: 등록된 항목의 고유 id."""
    data = load()
    item = _meta(_unique_name(data["서식"], name), label, group)
    item["fields"] = fields
    data["서식"].append(item)
    save(data)
    return item["id"]


def add_char(name, text, label=None, group=None):
    """반환: 등록된 항목의 고유 id."""
    data = load()
    item = _meta(_unique_name(data["문자"], name), label, group)
    item["text"] = text
    data["문자"].append(item)
    save(data)
    return item["id"]


def add_template_from_capture(name, fragment_src_path, label=None, group=None,
                              slot_count=0):
    r"""fragment_src_path의 조각 파일을 fragments/ 아래 고유 파일명으로 옮겨 등록.

    slot_count: 빈칸(\) 개수 — 변환 시 아랫줄들이 위에서부터 순서대로 들어간다.
    반환: 등록된 항목의 고유 id.
    """
    _ensure_dirs()
    data = load()
    item = _meta(_unique_name(data["템플릿"], name), label, group)
    fname = f"{uuid.uuid4().hex}.hwp"
    pathlib.Path(fragment_src_path).replace(FRAGMENTS_DIR / fname)
    item["file"] = fname
    item["slot_count"] = int(slot_count or 0)
    data["템플릿"].append(item)
    save(data)
    return item["id"]


def update_item(category, item_id, name=None, label=None, group=None):
    """등록된 항목의 이름·라벨·분류를 수정한다 (id는 유지 → 팔레트 연결 안 깨짐)."""
    data = load()
    items = data.get(category, [])
    target = next((it for it in items if it.get("id") == item_id), None)
    if target is None:
        return False
    if name and name.strip() and name.strip() != target["name"]:
        others = [it for it in items if it.get("id") != item_id]
        target["name"] = _unique_name(others, name.strip())
    if label is not None:
        target["label"] = normalize_label(label) or target["name"]
    if group is not None and group.strip():
        target["group"] = group.strip()
    save(data)
    return True


def replace_template_fragment(item_id, fragment_src_path, slot_count=None):
    """템플릿의 조각 파일만 새로 캡처한 것으로 교체 (id·이름·라벨 유지)."""
    data = load()
    target = next((it for it in data["템플릿"] if it.get("id") == item_id), None)
    if target is None:
        return False
    old = FRAGMENTS_DIR / target["file"]
    fname = f"{uuid.uuid4().hex}.hwp"
    pathlib.Path(fragment_src_path).replace(FRAGMENTS_DIR / fname)
    target["file"] = fname
    if slot_count is not None:
        target["slot_count"] = int(slot_count)
    save(data)
    try:
        old.unlink(missing_ok=True)
    except OSError:
        pass
    return True


def label_lookup():
    """{라벨: (분류명, 항목)} — 마크다운 변환용.

    사용자 등록 항목이 내장 문자보다 우선(같은 라벨이면 사용자 것이 이김).
    """
    data = load()
    out = {}
    for cat in CATEGORIES:
        for it in data[cat]:
            lab = (it.get("label") or "").strip()
            if lab and lab not in out:
                out[lab] = (cat, it)
    # 내장 문자 병합 (사용자가 이미 쓴 라벨은 건드리지 않음)
    try:
        import builtin_chars
        for lab, text, _ in builtin_chars.BUILTINS:
            if lab not in out:
                out[lab] = ("문자", {"name": lab, "text": text, "label": lab})
    except Exception:
        pass
    return out


def list_groups():
    """등록된 분류 이름 목록 (기본 분류 포함, 등록 순서 유지)."""
    data = load()
    seen = []
    for cat in CATEGORIES:
        for it in data[cat]:
            g = it.get("group") or DEFAULT_GROUP
            if g not in seen:
                seen.append(g)
    if DEFAULT_GROUP not in seen:
        seen.insert(0, DEFAULT_GROUP)
    return seen


def template_path(item):
    return FRAGMENTS_DIR / item["file"]


def delete_item(category, item_id):
    """id로 항목 삭제. 팔레트에 남은 참조(고아 블럭)도 함께 정리한다."""
    data = load()
    items = data.get(category, [])
    target = next((it for it in items if it.get("id") == item_id), None)
    if target is None:
        return False
    if category == "템플릿":
        try:
            (FRAGMENTS_DIR / target["file"]).unlink(missing_ok=True)
        except OSError:
            pass
    data[category] = [it for it in items if it.get("id") != item_id]
    save(data)
    _purge_palette_refs(category, item_id)
    return True


def _purge_palette_refs(category, item_id):
    """삭제된 라이브러리 항목을 가리키던 팔레트 블럭을 제거 (고아 블럭 방지).

    palette 를 최상위에서 import 하면 순환 참조가 되므로 여기서 지역 import.
    """
    try:
        import palette
    except ImportError:
        return
    btype = {"템플릿": "template", "서식": "style", "문자": "char"}.get(category)
    if btype is None:
        return
    try:
        tabs = palette.load_tabs()
    except Exception:
        return
    changed = False
    for tab in tabs:
        keep = [b for b in tab.get("blocks", [])
                if not (b.get("type") == btype and b.get("ref") == item_id)]
        if len(keep) != len(tab.get("blocks", [])):
            tab["blocks"] = keep
            changed = True
    if changed:
        palette.save_tabs(tabs)


def count_palette_refs(category, item_id):
    """이 항목을 쓰는 팔레트 블럭 수 (삭제 전 경고용)."""
    try:
        import palette
        tabs = palette.load_tabs()
    except Exception:
        return 0
    btype = {"템플릿": "template", "서식": "style", "문자": "char"}.get(category)
    if btype is None:
        return 0
    return sum(1 for tab in tabs for b in tab.get("blocks", [])
               if b.get("type") == btype and b.get("ref") == item_id)
