# -*- coding: utf-8 -*-
"""변환 미리보기 요약 (UI 제안 5) — 한글 없이 검증.

main.py 는 임포트하면 창을 띄우므로, 요약 함수만 떼어 같은 규칙으로 검증한다.
(규칙이 바뀌면 여기서 먼저 깨지도록 실제 구현을 읽어와 비교한다)
"""

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

MAIN = pathlib.Path(__file__).resolve().parent.parent / "main.py"


def _load_plan_summary():
    """main.py 에서 _plan_summary 정의만 떼어 실행한다 (창을 안 띄우려고)."""
    src = MAIN.read_text(encoding="utf-8")
    m = re.search(r"def _plan_summary\(ops, warns\):.*?\n(?=\n\ndef )", src, re.S)
    if not m:
        raise AssertionError("main.py 에서 _plan_summary 를 못 찾았습니다")
    ns = {}
    exec(m.group(0), ns)
    return ns["_plan_summary"]


plan_summary = _load_plan_summary()


class PlanSummaryTest(unittest.TestCase):

    def test_빈_계획(self):
        self.assertEqual(plan_summary([], []), "바꿀 내용 없음")

    def test_글자_줄만(self):
        self.assertEqual(plan_summary([("line", "가"), ("line", "나")], []),
                         "글자 줄 2개")

    def test_템플릿의_빈칸을_센다(self):
        ops = [("template", {"name": "결재란"}, ["담당", "부장"])]
        self.assertEqual(plan_summary(ops, []), "템플릿 1개 · 빈칸 2개 채움")

    def test_양식도_빈칸을_센다(self):
        ops = [("form", {"name": "표지"}, ["제목"])]
        self.assertEqual(plan_summary(ops, []), "양식 1개 · 빈칸 1개 채움")

    def test_서식_적용_줄(self):
        self.assertEqual(plan_summary([("rich_line", [{}])], []),
                         "서식 적용 줄 1개")

    def test_주의_건수가_붙는다(self):
        out = plan_summary([("line", "가")], ["없는 라벨", "또 없음"])
        self.assertIn("주의 2건", out)

    def test_여러_종류가_섞인_계획(self):
        ops = [("line", "가"),
               ("template", {"name": "t"}, ["a", "b"]),
               ("rich_line", [{}])]
        out = plan_summary(ops, [])
        for expect in ("글자 줄 1개", "템플릿 1개", "서식 적용 줄 1개",
                       "빈칸 2개 채움"):
            self.assertIn(expect, out)


if __name__ == "__main__":
    unittest.main()
