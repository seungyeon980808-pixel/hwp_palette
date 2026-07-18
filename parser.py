# -*- coding: utf-8 -*-
"""마크다운 텍스트 → 시험문제 데이터 파싱"""

import re

CIRCLED_MARKER_PATTERN = r'[①-⑳㉠-㉭ⓐ-ⓩ㈀-㈎⒜-⒵Ⓐ-Ⓩ] ?'


def parse(text):
    data = {
        'num': '', 'stem': '', 'material': '',
        'material_type': 'basic',   # basic / photo / experiment
        'material_flag': False,     # 자료: 키워드 감지 여부
        'question': '', 'bogi': [], 'choices': [],
        'choices_type': '5',        # '1' / '3' / '5'
    }
    lines = text.splitlines()
    mode = None

    def starts(s, *keywords):
        for k in keywords:
            if s.startswith(k):
                return k
        return None

    for line in lines:
        s = line.strip()
        if not s:
            continue

        k = starts(s, '번호:', '번 호:')
        if k:
            data['num'] = s[len(k):].strip(); mode = None; continue

        k = starts(s, '발문:', '문:', '발 문:')
        if k:
            data['stem'] = s[len(k):].strip(); mode = 'stem'; continue

        k = starts(s, '실험자료:')
        if k:
            data['material_type'] = 'experiment'
            data['material'] = ''; mode = 'material'; continue

        k = starts(s, '사진자료:')
        if k:
            data['material_type'] = 'photo'
            data['material'] = ''; mode = 'material'; continue

        k = starts(s, '자료:', '자 료:')
        if k:
            data['material'] = s[len(k):].strip()
            data['material_type'] = 'basic'
            data['material_flag'] = True; mode = 'material'; continue

        k = starts(s, '질문:', '질 문:')
        if k:
            data['question'] = s[len(k):].strip(); mode = 'question'; continue

        if starts(s, '보기:', '보 기:') or s == '보기':
            mode = 'bogi'; continue

        k = starts(s, '선지1:', '선지3:', '선지5:', '1선지:', '3선지:', '5선지:', '선지:', '선 지:')
        if k:
            if k in ('선지1:', '1선지:'):
                data['choices_type'] = '1'
            elif k in ('선지3:', '3선지:'):
                data['choices_type'] = '3'
            elif k in ('선지5:', '5선지:'):
                data['choices_type'] = '5'
            else:
                data['choices_type'] = '5'
            mode = 'choices'; continue

        if mode == 'bogi':
            if len(s) >= 2 and s[1] == ':':
                data['bogi'].append(s[2:].strip())
            else:
                data['bogi'].append(s)
        elif mode == 'choices' and s:
            if s[0] in '①②③④⑤':
                s = s[1:].strip()
            data['choices'].append(s)
        elif mode == 'stem' and s:
            data['stem'] += (' ' + s if data['stem'] else s)
        elif mode == 'material' and s:
            data['material'] += ('\n' + s if data['material'] else s)
        elif mode == 'question' and s:
            data['question'] += (' ' + s if data['question'] else s)

    return data


def has_recognized_content(data):
    """발문/자료/질문/보기/선지 중 하나라도 인식됐으면 True (부분 변환 지원)"""
    return bool(
        data['stem'] or data['material_flag']
        or data['material_type'] in ('photo', 'experiment')
        or data['question'] or data['bogi'] or data['choices']
    )


def strip_circled_markers(text):
    """원문자(①②…㉠㉡…ⓐⓑ…) + 뒤 공백 1칸 제거 — 기본 서식 되돌리기용"""
    return re.sub(CIRCLED_MARKER_PATTERN, '', text)


# ── 라이브러리 마크다운 (\라벨\ 문법) ─────────────────────
# \인사말\ → 문자 치환(줄 안 어디서든), \보기\ 단독 줄 → 템플릿 삽입 +
# 아랫줄들이 템플릿 속 빈칸(\)에 순서대로 들어간다.
LIB_TOKEN_RE = re.compile(r'\\([^\\\r\n]+?)\\')


def has_library_tokens(text):
    return bool(LIB_TOKEN_RE.search(text or ''))


def _replace_char_tokens(line, lookup, warnings):
    r"""줄 안의 \라벨\ 중 '문자' 항목만 내용으로 치환. 나머지는 원문 유지 + 경고."""
    def repl(m):
        label = m.group(1).strip()
        entry = lookup.get(label)
        if entry and entry[0] == '문자':
            return entry[1]['text']
        # 템플릿·양식은 줄 단위로만 처리된다(빈칸을 아랫줄들로 채우는 구조라
        # 줄 중간에서는 의미가 없다). 등록은 돼 있으니 '없는 라벨'로 말하면 안 된다.
        if entry and entry[0] in ('템플릿', '양식'):
            warnings.append(
                f"{entry[0]} 라벨은 한 줄에 단독으로 써주세요: \\{label}\\")
        elif entry and entry[0] == '서식':
            warnings.append(
                f"서식은 감쌀 내용이 필요합니다: \\{label}\\내용\\/ 형태로 써주세요")
        else:
            warnings.append(f"등록되지 않은 라벨: \\{label}\\")
        return m.group(0)
    return LIB_TOKEN_RE.sub(repl, line)


SKIP_MARK = '-'      # 이 줄은 해당 빈칸을 비워둔다


# ── 서식 감싸기 문법 (개선안 27) ────────────────────────
# \굵게\감쌀 내용\/  →  '굵게' 서식을 '감쌀 내용'에만 입힌다.
#
# 닫는 표시로 `\/` 를 고른 이유: 역슬래시는 이미 두 가지 뜻으로 쓰이는데
#   \ 하나  = 템플릿 빈칸 표시
#   \라벨\  = 라이브러리 호출
# `\/` 는 그 어느 쪽과도 겹치지 않아, 기존 문서를 다시 해석하게 만들지 않는다.
# 내용 안에 다시 감싸기를 넣는 것(중첩)은 지원하지 않는다 — 비단조롭게 복잡해지고
# 실제로 쓸 일이 거의 없다.
STYLE_SPAN_RE = re.compile(r'\\([^\\\r\n]+?)\\(.*?)\\/')


def has_style_spans(text):
    return bool(STYLE_SPAN_RE.search(text or ''))


def build_segments(line, lookup, warnings):
    """서식 구간이 섞인 줄을 조각으로 나눈다.

    반환: [{'text': str, 'style': 델타dict 또는 None}, ...]
          서식 감싸기가 하나도 없으면 None (호출부는 기존 방식으로 처리).

    라벨이 '서식' 분류가 아니면 감싸기로 보지 않고 원문 그대로 둔다 — 문자
    라벨 뒤에 우연히 `\\/` 가 오는 경우까지 서식으로 오해하면 안 되기 때문.
    """
    spans = []
    for m in STYLE_SPAN_RE.finditer(line):
        entry = lookup.get(m.group(1).strip())
        if entry and entry[0] == '서식':
            spans.append((m, entry[1]))
    if not spans:
        return None

    segs, last = [], 0
    for m, item in spans:
        if m.start() > last:
            segs.append({"text": _replace_char_tokens(line[last:m.start()],
                                                      lookup, warnings),
                         "style": None})
        segs.append({"text": _replace_char_tokens(m.group(2), lookup, warnings),
                     "style": item.get("fields") or {}})
        last = m.end()
    if last < len(line):
        segs.append({"text": _replace_char_tokens(line[last:], lookup, warnings),
                     "style": None})
    return [s for s in segs if s["text"]]


def build_library_plan(text, lookup):
    r"""선택 텍스트 → 실행 계획.

    lookup: {라벨: (분류명, 항목dict)} — library.label_lookup() 결과.
    반환: (ops, warnings)
      ops: ('line', 텍스트) — 그대로 삽입할 한 줄
           ('rich_line', [조각들]) — 서식 감싸기(\서식\내용\/)가 섞인 한 줄
           ('template', 항목, [줄들]) — 템플릿을 커서에 삽입 + 빈칸(\) 순서대로 채움
           ('form', 항목, [줄들])     — 양식을 새 문서로 열고 + 빈칸 채움
             줄이 '-' 하나면 그 빈칸은 건너뛴다(비워둠).
    """
    ops, warnings = [], []
    lines = (text or '').replace('\r\n', '\n').replace('\r', '\n').split('\n')
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        m = LIB_TOKEN_RE.fullmatch(stripped)
        if m:
            label = m.group(1).strip()
            entry = lookup.get(label)
            # 템플릿(삽입)과 양식(새 문서로 열기) — 빈칸 채우는 방식은 같다
            if entry and entry[0] in ('템플릿', '양식'):
                kind = 'form' if entry[0] == '양식' else 'template'
                item = entry[1]
                slot_count = int(item.get('slot_count') or 0)
                fills = []
                j = i + 1
                while len(fills) < slot_count and j < len(lines):
                    cand = lines[j].strip()
                    if not cand:
                        j += 1
                        continue
                    if LIB_TOKEN_RE.fullmatch(cand):
                        break          # 다음 라벨 시작 — 여기까지가 이 템플릿 몫
                    if cand == SKIP_MARK:
                        fills.append(None)     # 이 빈칸은 비움
                    else:
                        fills.append(_replace_char_tokens(lines[j], lookup, warnings))
                    j += 1
                ops.append((kind, item, fills))
                i = j
                continue
        segs = build_segments(lines[i], lookup, warnings)
        if segs is not None:
            ops.append(('rich_line', segs))
        else:
            ops.append(('line', _replace_char_tokens(lines[i], lookup, warnings)))
        i += 1
    return ops, warnings
