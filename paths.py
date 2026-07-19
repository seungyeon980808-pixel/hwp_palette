# -*- coding: utf-8 -*-
"""파일이 어디 놓이는지 한 곳에서 정한다 (UI 제안 20 — exe 배포).

**왜 필요한가.** 여태 설정·라이브러리·로그는 모두

    pathlib.Path(__file__).parent / "config.json"

이었다. 소스로 실행할 때는 프로젝트 폴더라 맞다. 그런데 PyInstaller 로 exe 를
만들면 __file__ 은 실행할 때마다 새로 풀리는 **임시 폴더**(sys._MEIPASS)를
가리키고, 그 폴더는 프로그램이 끝나면 지워진다. 즉 exe 로 배포하면 팔레트를
아무리 꾸며도 껐다 켜면 전부 사라진다.

그래서 두 가지를 나눈다.
  data_dir()     — 사용자가 만든 것 (설정·라이브러리·조각·로그). 써야 하므로
                   exe 옆(또는 못 쓰면 AppData)에 둔다. 껐다 켜도 남는다.
  resource_dir() — 프로그램에 딸려온 것 (아이콘 등). 읽기만 하므로 임시 폴더로
                   충분하다.

소스로 실행할 때는 둘 다 지금까지와 똑같이 프로젝트 폴더다 — 기존 설정 파일을
그대로 쓴다.
"""

import os
import pathlib
import sys

APP_NAME = "hwp_palette"
_HERE = pathlib.Path(__file__).resolve().parent


def is_frozen():
    """PyInstaller 로 묶인 exe 로 돌고 있는가."""
    return bool(getattr(sys, "frozen", False))


def resource_dir():
    """딸려온 읽기 전용 자원(assets 등)이 있는 폴더."""
    if is_frozen():
        # onefile 이면 _MEIPASS(임시), onedir 이면 exe 옆
        return pathlib.Path(getattr(sys, "_MEIPASS", _HERE))
    return _HERE


def _writable(d):
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def data_dir():
    """사용자 데이터를 두는 폴더. 없으면 만든다.

    exe 는 **옆에** 두는 것을 먼저 시도한다 — USB 에 넣어 다니거나 통째로
    복사해 옮길 수 있고, 설정이 어디 있는지 눈에 보인다.
    Program Files 처럼 쓰기가 막힌 곳에 설치했으면 AppData 로 물러선다
    (거기서도 실패하면 예외 대신 exe 옆 경로를 돌려준다 — 저장할 때
    나는 오류가 여기서 나는 오류보다 다루기 쉽다).
    """
    if not is_frozen():
        return _HERE                       # 소스 실행 — 지금까지와 동일

    beside = pathlib.Path(sys.executable).resolve().parent
    if _writable(beside):
        return beside

    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if base:
        appdata = pathlib.Path(base) / APP_NAME
        if _writable(appdata):
            return appdata
    return beside


DATA_DIR = data_dir()
RESOURCE_DIR = resource_dir()
