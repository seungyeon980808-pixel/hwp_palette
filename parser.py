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
