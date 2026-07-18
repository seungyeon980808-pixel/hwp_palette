# -*- coding: utf-8 -*-
r"""양식 채우기 — HWPX에서 채울 자리를 뽑고, 채운 내용을 다시 넣는다.

왜 HWPX인가 (실측 2026-07-19):
  .hwp(바이너리 5.x)는 문단 레코드를 직접 고치기 어렵다. 반면 **HWPX 는
  zip 안에 XML** 이고, 글자는 `<hp:t>` 태그 하나하나에 들어 있다.
  그 태그의 내용만 바꿔서 zip 을 다시 쓰면 **나머지 바이트는 손대지 않으므로
  표·병합·글꼴·이미지가 그대로 살아남는다** (셀 10개·병합 유지 확인).

이 모듈은 한글(pyhwpx)에 의존하지 않는다 — 순수 zip/XML 조작이라 한글 없이
테스트할 수 있다. .hwp → .hwpx 변환만 호출부(엔진)가 맡는다.

주고받는 단위가 '빈칸'이 아니라 '글자 조각(run)'인 이유:
  한 조각 안에 빈칸이 여러 개 있을 수 있다(실측: `\. \.`).
  빈칸 단위로 쪼개면 그 경우가 지저분해지므로, **조각 통째로 보여주고
  조각 통째로 돌려받는다**. 사람이 읽기에도 이쪽이 자연스럽다.
"""

import re
import xml.sax.saxutils as saxutils
import zipfile

# HWPX 안에서 본문이 들어 있는 파일들 (구역이 여러 개면 section1, 2 … 로 늘어난다)
SECTION_RE = re.compile(r"Contents/section\d+\.xml$")

# 글자 한 조각. HWPX 는 서식이 바뀌는 지점마다 이 태그를 나눈다.
RUN_RE = re.compile(r"<hp:t>([^<]*)</hp:t>")

SLOT_MARK = "\\"        # 템플릿 빈칸 표시 — 이게 든 조각을 '채울 자리'로 본다

# 주고받는 줄 형식:  [3] 내용
LINE_RE = re.compile(r"^\s*\[(\d+)\]\s?(.*)$")


def _section_names(zf):
    return [n for n in zf.namelist() if SECTION_RE.search(n)]


def read_runs(hwpx_path):
    """(번호, 글자) 목록. 번호는 문서 전체에서 조각이 나오는 순서다."""
    runs = []
    with zipfile.ZipFile(hwpx_path) as zf:
        for name in _section_names(zf):
            xml = zf.read(name).decode("utf-8")
            for m in RUN_RE.finditer(xml):
                runs.append((len(runs), saxutils.unescape(m.group(1))))
    return runs


def slots(hwpx_path):
    r"""채울 자리만 골라낸다 — 빈칸 표시(\)가 든 조각.

    빈칸이 하나도 없으면 빈 목록이 아니라 **글자가 있는 조각 전부**를 돌려준다.
    빈칸을 미리 심어두지 않은 양식도 "이 중에 골라 고치세요"로 쓸 수 있게 하기 위함.
    """
    runs = read_runs(hwpx_path)
    marked = [(i, t) for i, t in runs if SLOT_MARK in t]
    if marked:
        return marked
    return [(i, t) for i, t in runs if t.strip()]


def to_worksheet(hwpx_path, title="양식"):
    """AI(사람)에게 붙여넣을 주고받기 문서를 만든다."""
    runs = read_runs(hwpx_path)
    targets = slots(hwpx_path)
    preview = "\n".join(t for _, t in runs if t.strip()) or "(글자 없음)"
    lines = [
        f"# 양식: {title}",
        "#",
        "# 아래 [번호] 뒤의 내용을 채워서 **그대로 돌려주세요**.",
        "# - 번호는 바꾸지 마세요. 번호로 원래 자리를 찾습니다.",
        "# - 줄 순서는 바뀌어도 되고, 안 채울 줄은 빼도 됩니다.",
        r"# - \ 는 채워야 할 빈칸입니다.",
        "",
        "# ── 문서 미리보기 (어떤 양식인지 파악용) ──",
        *[f"#   {line}" for line in preview.splitlines()],
        "",
        "# ── 채울 자리 ──",
    ]
    lines += [f"[{i}] {t}" for i, t in targets]
    return "\n".join(lines)


def parse_worksheet(text):
    """채워서 돌려받은 문서 → {번호: 글자}. 주석(#)과 빈 줄은 무시."""
    out = {}
    for raw in (text or "").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = LINE_RE.match(raw)
        if m:
            out[int(m.group(1))] = m.group(2).rstrip()
    return out


def fill(src_hwpx, dst_hwpx, replacements):
    """replacements({번호: 글자})를 넣어 새 HWPX 로 저장. 반환: 실제로 바꾼 개수.

    바꾸지 않는 파일은 **읽은 그대로 다시 쓴다** — 압축 방식과 순서까지 유지해야
    한글이 군말 없이 연다.
    """
    changed = 0
    with zipfile.ZipFile(src_hwpx) as zf:
        sections = set(_section_names(zf))
        counter = [-1]

        def _sub(m):
            counter[0] += 1
            if counter[0] not in replacements:
                return m.group(0)
            return "<hp:t>%s</hp:t>" % saxutils.escape(replacements[counter[0]])

        rewritten = {}
        for name in _section_names(zf):
            xml = zf.read(name).decode("utf-8")
            before = counter[0]
            new_xml = RUN_RE.sub(_sub, xml)
            if new_xml != xml:
                rewritten[name] = new_xml.encode("utf-8")
            del before

        changed = sum(1 for i in replacements
                      if 0 <= i <= counter[0])

        with zipfile.ZipFile(dst_hwpx, "w") as out:
            for item in zf.infolist():
                data = rewritten.get(item.filename)
                if data is None:
                    data = zf.read(item.filename)
                info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                info.compress_type = item.compress_type
                info.external_attr = item.external_attr
                out.writestr(info, data)
        del sections
    return changed


def unfilled_marks(hwpx_path):
    r"""아직 빈칸(\)이 남아 있는 조각 — 채우고 나서 확인용."""
    return [(i, t) for i, t in read_runs(hwpx_path) if SLOT_MARK in t]
