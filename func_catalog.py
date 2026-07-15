# -*- coding: utf-8 -*-
"""기능 카탈로그 — '기능' 블럭에 병렬로 담을 수 있는 한글 조작 목록.

각 기능의 실제 실행은 hwp_engine.execute_function_block()이 한다. 여기서는
UI가 "어떤 기능이 있고, 값을 어떻게 입력받는지"만 정의한다.

kind:
  toggle   값 없음. 켜기/끄기 토글 (굵게 등) — 선택 영역에 Run 액션
  number   숫자 입력 (자간, 크기, 줄간격)
  font     글꼴 이름 (드롭다운 + 직접 입력)
  color    색상 (팔레트)
  para     문단 정렬 등 값 없는 문단 액션
"""

FUNCTIONS = [
    {"key": "굵게",     "kind": "toggle", "hint": "선택 글자를 굵게 (토글)"},
    {"key": "기울임",   "kind": "toggle", "hint": "선택 글자를 기울임 (토글)"},
    {"key": "밑줄",     "kind": "toggle", "hint": "선택 글자에 밑줄 (토글)"},
    {"key": "글씨체",   "kind": "font",   "hint": "글꼴 변경"},
    {"key": "글씨크기", "kind": "number", "unit": "pt", "hint": "글자 크기(pt)"},
    {"key": "자간",     "kind": "number", "unit": "",   "hint": "글자 간격(음수=좁게)"},
    {"key": "글자색",   "kind": "color",  "hint": "글자 색"},
    {"key": "가운데정렬", "kind": "para", "hint": "문단 가운데 정렬"},
    {"key": "왼쪽정렬",   "kind": "para", "hint": "문단 왼쪽 정렬"},
    {"key": "양쪽정렬",   "kind": "para", "hint": "문단 양쪽 정렬"},
    {"key": "줄간격",   "kind": "number", "unit": "%",  "hint": "문단 줄간격(%)"},
]

FUNC_BY_KEY = {f["key"]: f for f in FUNCTIONS}

# 글꼴 드롭다운 후보 (직접 입력도 허용). 실측 fontsUsed 기반.
COMMON_FONTS = [
    "함초롬바탕", "함초롬돋움", "맑은 고딕", "굴림", "굴림체", "바탕", "돋움",
    "HY견고딕", "HY견명조", "HY신명조", "HY중고딕", "휴먼명조",
]
