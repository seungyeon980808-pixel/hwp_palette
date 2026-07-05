# exam_scribe

시험문제 이미지(PNG)를 읽어 한글(HWP) 문서에 자동으로 타이핑해주는 도구.

## 목표
시험문제를 편하게 출제하는 것. [5E(phy_draw)](https://github.com/seungyeon980808-pixel/phy_draw)가 그림을 담당한다면, 이 도구는 텍스트·표·수식을 담당한다.

## 구조 (확정, 2026-07-04)
- 순수 로컬 데스크톱 프로그램. 서버/웹 없음.
- 이미지 → Claude API(비전) → 구조화 마크다운(`발문:/자료:/질문:/보기:/선지:`) → pyhwpx(COM)로 한글에 직접 타이핑
- 비전 모델: `claude-sonnet-5` 기본, 파싱 실패 시 `claude-opus-4-8`로 승격

## 파일 구성
- `parser.py` — 마크다운 텍스트 파싱 (순수 함수, 외부 의존성 없음)
- `hwp_engine.py` — 한컴 자동화(pyhwpx) 엔진. Tkinter/UI에 의존하지 않음
- `main.py` — Tkinter UI, 실행 진입점 (`python main.py` 또는 `run.bat`)
- `config.json` — 사진 폴더 경로 등 사용자 설정 (git 추적 제외)

## 실행
```
pip install -r requirements.txt
python main.py
```
한글(HWP) 프로그램을 먼저 실행해둘 필요는 없음 — 버튼을 누르면 자동 연결/실행됨.

## 상태
`30_exam_edit`의 기존 변환기(`exam_convert_v4_8_1`)를 3파일 구조로 이관 완료. 문항번호·자료박스·보기박스·선지 배치·서식 도구·사진 삽입 기능 그대로 동작. 클립보드 읽기 안정성 버그(마크다운 변환·원문자 삽입 시 간헐적 실패)를 이관 과정에서 함께 수정.

다음 단계: 이미지 → 마크다운 비전 API 연동 (이 프로젝트의 핵심 목표).

버전: v1.0.0 (2026-07-05)
