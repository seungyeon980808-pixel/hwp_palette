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
    for cat in CATEGORIES:
        if isinstance(data.get(cat), list):
            out[cat] = data[cat]
        # 하위호환: 예전 항목에 라벨/분류(/슬롯수) 기본값 채움
        for it in out[cat]:
            it.setdefault("label", it.get("name", ""))
            it.setdefault("group", DEFAULT_GROUP)
            # 이미 \라벨\ 로 저장돼 있던 항목도 알맹이로 교정 (조회 실패 방지)
            it["label"] = normalize_label(it.get("label")) or it.get("name", "")
            if cat == "템플릿":
                it.setdefault("slot_count", 0)
                it.pop("slot_names", None)   # 이름 빈칸 기능 폐지 (2026-07-16)
    return out


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
    return {"name": name,
            "label": lab,
            "group": (group or DEFAULT_GROUP).strip() or DEFAULT_GROUP}


def add_style(name, fields, label=None, group=None):
    """fields: {친화적필드명: 값} — 캡처 시 선택된 항목만 들어있는 델타."""
    data = load()
    name = _unique_name(data["서식"], name)
    item = _meta(name, label, group)
    item["fields"] = fields
    data["서식"].append(item)
    save(data)
    return name


def add_char(name, text, label=None, group=None):
    data = load()
    name = _unique_name(data["문자"], name)
    item = _meta(name, label, group)
    item["text"] = text
    data["문자"].append(item)
    save(data)
    return name


def add_template_from_capture(name, fragment_src_path, label=None, group=None,
                              slot_count=0):
    r"""fragment_src_path의 조각 파일을 fragments/ 아래 고유 파일명으로 옮겨 등록.

    slot_count: 빈칸(\) 개수 — 변환 시 아랫줄들이 위에서부터 순서대로 들어간다.
    """
    _ensure_dirs()
    data = load()
    name = _unique_name(data["템플릿"], name)
    fname = f"{uuid.uuid4().hex}.hwp"
    dest = FRAGMENTS_DIR / fname
    pathlib.Path(fragment_src_path).replace(dest)
    item = _meta(name, label, group)
    item["file"] = fname
    item["slot_count"] = int(slot_count or 0)
    data["템플릿"].append(item)
    save(data)
    return name


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


def delete_item(category, name):
    data = load()
    items = data.get(category, [])
    target = next((it for it in items if it["name"] == name), None)
    if target is None:
        return
    if category == "템플릿":
        try:
            (FRAGMENTS_DIR / target["file"]).unlink(missing_ok=True)
        except Exception:
            pass
    data[category] = [it for it in items if it["name"] != name]
    save(data)
