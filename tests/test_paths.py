# -*- coding: utf-8 -*-
"""저장 위치 규칙 (UI 제안 20 — exe 배포).

여기서 막으려는 사고: exe 로 만들었더니 껐다 켤 때마다 팔레트가 초기화되는 것.
원인은 __file__ 이 PyInstaller 의 임시 폴더를 가리키는 것인데, 임시 폴더는
프로그램이 끝나면 지워진다.
"""

import pathlib
import sys
import tempfile
import unittest
import unittest.mock as mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import paths   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


class SourceRunTest(unittest.TestCase):
    """소스로 실행할 때는 지금까지와 똑같아야 한다 — 기존 설정을 그대로 쓴다."""

    def test_frozen_이_아니다(self):
        self.assertFalse(paths.is_frozen())

    def test_데이터_폴더는_프로젝트_폴더(self):
        self.assertEqual(paths.data_dir(), ROOT)

    def test_자원_폴더도_프로젝트_폴더(self):
        self.assertEqual(paths.resource_dir(), ROOT)

    def test_기존_설정_경로가_안_바뀐다(self):
        import settings
        import library
        self.assertEqual(settings.CONFIG_PATH, ROOT / "config.json")
        self.assertEqual(library.LIBRARY_PATH, ROOT / "library.json")
        self.assertEqual(library.FRAGMENTS_DIR, ROOT / "fragments")


class FrozenTest(unittest.TestCase):
    """exe 로 묶였을 때 — 쓸 수 있는 곳을 찾아 데이터를 남긴다."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, True))

    def _frozen(self, exe_dir, meipass=None):
        exe = pathlib.Path(exe_dir) / "hwp_palette.exe"
        patches = [mock.patch.object(sys, "executable", str(exe)),
                   mock.patch.object(paths, "is_frozen", lambda: True)]
        if meipass is not None:
            patches.append(mock.patch.object(sys, "_MEIPASS", str(meipass),
                                             create=True))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_쓸_수_있으면_exe_옆에_둔다(self):
        beside = self.tmp / "portable"
        beside.mkdir()
        self._frozen(beside)
        self.assertEqual(paths.data_dir(), beside.resolve())

    def test_임시_폴더에_두지_않는다(self):
        # 이것이 이 파일의 핵심. _MEIPASS 는 프로그램이 끝나면 지워진다.
        beside = self.tmp / "app"
        beside.mkdir()
        meipass = self.tmp / "_MEI12345"
        meipass.mkdir()
        self._frozen(beside, meipass=meipass)
        self.assertNotEqual(paths.data_dir(), meipass)
        self.assertEqual(paths.data_dir(), beside.resolve())

    def test_자원은_임시_폴더에서_읽는다(self):
        # 아이콘처럼 딸려온 파일은 거기 풀리므로 여기서 읽는 게 맞다.
        meipass = self.tmp / "_MEI999"
        meipass.mkdir()
        self._frozen(self.tmp, meipass=meipass)
        self.assertEqual(paths.resource_dir(), meipass)

    def test_exe_옆이_막혔으면_AppData_로_물러선다(self):
        beside = self.tmp / "programfiles"
        beside.mkdir()
        appdata = self.tmp / "appdata"
        appdata.mkdir()
        self._frozen(beside)
        real = paths._writable
        # exe 옆만 못 쓰는 상황을 흉내낸다
        p = mock.patch.object(paths, "_writable",
                              lambda d: False if d == beside.resolve() else real(d))
        p.start()
        self.addCleanup(p.stop)
        p2 = mock.patch.dict("os.environ", {"LOCALAPPDATA": str(appdata)})
        p2.start()
        self.addCleanup(p2.stop)
        self.assertEqual(paths.data_dir(), appdata / paths.APP_NAME)

    def test_어디도_못_쓰면_예외_대신_exe_옆을_돌려준다(self):
        beside = self.tmp / "readonly"
        beside.mkdir()
        self._frozen(beside)
        p = mock.patch.object(paths, "_writable", lambda d: False)
        p.start()
        self.addCleanup(p.stop)
        p2 = mock.patch.dict("os.environ", {"LOCALAPPDATA": "", "APPDATA": ""})
        p2.start()
        self.addCleanup(p2.stop)
        self.assertEqual(paths.data_dir(), beside.resolve())   # 안 터진다


class WritableTest(unittest.TestCase):

    def test_없는_폴더는_만들어서_쓴다(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, True))
        target = tmp / "새폴더" / "안쪽"
        self.assertTrue(paths._writable(target))
        self.assertTrue(target.is_dir())

    def test_시험용_파일을_남기지_않는다(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, True))
        paths._writable(tmp)
        self.assertEqual(list(tmp.iterdir()), [])


class SpecTest(unittest.TestCase):
    """빌드 설정이 개인 데이터를 exe 에 넣지 않는지."""

    def test_개인_데이터가_datas_에_없다(self):
        spec = (ROOT / "hwp_palette.spec").read_text(encoding="utf-8")
        datas = spec.split("datas=")[1].split("]")[0]
        for name in ("config.json", "library.json", "fragments", "app.log"):
            self.assertNotIn(name, datas, f"{name} 이 exe 에 들어갑니다")

    def test_아이콘은_넣는다(self):
        spec = (ROOT / "hwp_palette.spec").read_text(encoding="utf-8")
        self.assertIn("icon-96.png", spec)

    def test_한글_COM_모듈을_명시했다(self):
        # 빠지면 exe 에서만 '한글을 찾을 수 없습니다'가 난다 (소스로는 잘 됨)
        spec = (ROOT / "hwp_palette.spec").read_text(encoding="utf-8")
        for mod in ("win32com.client", "pythoncom", "pyhwpx"):
            self.assertIn(mod, spec)


if __name__ == "__main__":
    unittest.main()
