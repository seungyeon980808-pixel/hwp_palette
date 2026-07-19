# -*- coding: utf-8 -*-
r"""library.py 순수 로직 테스트 (개선안 22).

library.load()는 사용자의 개인 library.json을 읽으므로, 여기서는 가짜 데이터로
갈아끼워 파일과 무관하게 검증한다.
"""

import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import library        # noqa: E402


def _fake_data(**by_category):
    data = {cat: [] for cat in library.CATEGORIES}
    data.update(by_category)
    return data


class NormalizeLabelTest(unittest.TestCase):
    r"""사용자가 \라벨\ 통째로 입력해도 알맹이로 저장돼야 조회가 된다."""

    def test_감싼_역슬래시를_벗긴다(self):
        self.assertEqual(library.normalize_label(r"\계획서표지\ "), "계획서표지")

    def test_이미_알맹이면_그대로(self):
        self.assertEqual(library.normalize_label("계획서표지"), "계획서표지")

    def test_빈_값은_빈_문자열(self):
        self.assertEqual(library.normalize_label(None), "")
        self.assertEqual(library.normalize_label("   "), "")


class UniqueNameTest(unittest.TestCase):
    """이름은 분류 안에서 유일해야 한다 (개선안 3의 전제)."""

    def test_겹치지_않으면_그대로(self):
        self.assertEqual(library._unique_name([{"name": "가"}], "나"), "나")

    def test_겹치면_번호를_붙인다(self):
        self.assertEqual(library._unique_name([{"name": "결재란"}], "결재란"),
                         "결재란 (2)")

    def test_번호도_겹치면_다음_번호로(self):
        items = [{"name": "결재란"}, {"name": "결재란 (2)"}]
        self.assertEqual(library._unique_name(items, "결재란"), "결재란 (3)")


class FindLabelOwnerTest(unittest.TestCase):
    r"""라벨 중복 검사 — 이름과 달리 분류를 가로질러 겹칠 수 있다."""

    def setUp(self):
        self.data = _fake_data(
            서식=[{"id": "A", "name": "강조", "label": "강조"}],
            문자=[{"id": "B", "name": "인사말", "label": "인사말"}],
        )
        patcher = mock.patch.object(library, "load", return_value=self.data)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_안_쓰이는_라벨이면_None(self):
        self.assertIsNone(library.find_label_owner("처음보는라벨"))

    def test_다른_분류의_같은_라벨을_찾아낸다(self):
        cat, item = library.find_label_owner("강조")
        self.assertEqual(cat, "서식")
        self.assertEqual(item["id"], "A")

    def test_자기_자신은_충돌로_보지_않는다(self):
        # 수정 화면에서 라벨을 그대로 두고 이름만 바꾸는 흔한 경우
        self.assertIsNone(library.find_label_owner("강조", exclude_id="A"))

    def test_감싼_역슬래시를_넣어도_같은_라벨로_본다(self):
        self.assertIsNotNone(library.find_label_owner("\\강조\\"))

    def test_빈_라벨은_충돌_없음(self):
        self.assertIsNone(library.find_label_owner(""))


class MoveWhenFreeTest(unittest.TestCase):
    r"""한글이 방금 저장한 조각 파일을 놓을 때까지 기다렸다 옮기는지.

    증상: 템플릿 캡처 시
      [WinError 32] 다른 프로세스가 파일을 사용 중이기 때문에 …
    save_block_as 는 한글에게 저장을 '시키는' 것이라, 파이썬으로 제어가 돌아온
    뒤에도 한글이 잠깐 핸들을 쥐고 있다.
    """

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = pathlib.Path(self.tmp.name) / "_tmp_123.hwp"
        self.src.write_bytes(b"FRAGMENT")
        self.dst = pathlib.Path(self.tmp.name) / "final.hwp"
        # 테스트가 느려지지 않게 대기 간격을 줄인다
        patcher = mock.patch.object(library, "_MOVE_DELAY", 0)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_잠겨_있지_않으면_바로_옮긴다(self):
        library._move_when_free(self.src, self.dst)
        self.assertTrue(self.dst.exists())
        self.assertFalse(self.src.exists())
        self.assertEqual(self.dst.read_bytes(), b"FRAGMENT")

    def test_잠깐_잠겨_있으면_기다렸다_옮긴다(self):
        real = pathlib.Path.replace
        calls = {"n": 0}

        def flaky(self_, target):
            calls["n"] += 1
            if calls["n"] <= 3:            # 처음 세 번은 한글이 물고 있는 상황
                raise PermissionError(32, "다른 프로세스가 파일을 사용 중")
            return real(self_, target)

        with mock.patch.object(pathlib.Path, "replace", flaky):
            library._move_when_free(self.src, self.dst)
        self.assertTrue(self.dst.exists())
        self.assertEqual(calls["n"], 4)

    def test_끝내_안_놓으면_복사로_물러선다(self):
        """이름 바꾸기가 막혀도 읽기는 대개 열려 있다 → 등록은 성공해야 한다."""
        def always_locked(self_, target):
            raise PermissionError(32, "다른 프로세스가 파일을 사용 중")

        with mock.patch.object(pathlib.Path, "replace", always_locked):
            library._move_when_free(self.src, self.dst)
        self.assertTrue(self.dst.exists())
        self.assertEqual(self.dst.read_bytes(), b"FRAGMENT")
        self.assertTrue(self.src.exists())      # 복사라 원본은 남는다(호출부가 지움)


class LabelLookupTest(unittest.TestCase):
    r"""\라벨\ → 항목 조회. 중복 시 먼저 만난 것이 이긴다."""

    def test_중복_라벨은_먼저_만난_것이_이긴다(self):
        data = _fake_data(
            서식=[{"id": "A", "name": "먼저", "label": "겹침"}],
            문자=[{"id": "B", "name": "나중", "label": "겹침"}],
        )
        with mock.patch.object(library, "load", return_value=data):
            out = library.label_lookup()
        self.assertEqual(out["겹침"][0], "서식")
        self.assertEqual(out["겹침"][1]["id"], "A")

    def test_내장_문자가_병합된다(self):
        with mock.patch.object(library, "load", return_value=_fake_data()):
            out = library.label_lookup()
        self.assertIn("원1", out)
        self.assertEqual(out["원1"][0], "문자")

    def test_사용자_항목이_내장_문자를_이긴다(self):
        data = _fake_data(문자=[{"id": "A", "name": "내것", "label": "원1",
                                 "text": "내가정한값"}])
        with mock.patch.object(library, "load", return_value=data):
            out = library.label_lookup()
        self.assertEqual(out["원1"][1]["text"], "내가정한값")


if __name__ == "__main__":
    unittest.main()
