# 정부 문서 WeKnora 설치 환경

Tencent WeKnora v0.8.0의 화면과 기능을 Docker로 실행하는 독립 설치 구성입니다. 한국어 UI, MiniMax 답변, NVIDIA API 임베딩, CPU 리랭커를 설정합니다.

**GPU는 필요 없습니다.** 설치와 실행에 인터넷이 필요하며, 문서와 API 키는 저장소에 포함하지 않습니다.

## 처음 설치하기

**[동료용 설치 안내](COLLEAGUE_SETUP.md)** 에서 Docker Desktop·WSL2·Python 설치부터 로그인까지 따라 할 수 있습니다.

- Windows x64, WSL2 기반 Docker Desktop의 Linux 컨테이너, Python **3.12**
- RAM 16GB 이상, 여유 디스크 40GB 이상 권장. 문서량에 따라 추가 자원이 필요합니다.
- MiniMax·NVIDIA API 키는 각자 준비하거나 소유자에게 별도로 전달받습니다.
- Supabase와 Cloudflare 계정은 로컬 설치에 필요하지 않습니다.

## 구성

| 구성 | 역할 |
|---|---|
| WeKnora 웹·API | 한국어 UI, 지식베이스·문서·질의 관리 |
| ParadeDB / Redis | 검색 데이터와 작업 처리 |
| Docreader | 문서 파싱 |
| NVIDIA API | nvidia/nemotron-3-embed-1b, 2048차원 임베딩 |
| MiniMax API | MiniMax-M3 답변 생성 |
| BAAI/bge-reranker-v2-m3 | CPU 기반 리랭킹 |

리랭커는 CPU 4개와 RAM 상한 8GB로 설정되어 있습니다. 입력은 최대 4096토큰까지 절삭될 수 있습니다. 외부 모델 API 사용량은 해당 키 계정에 청구됩니다.

## 설치·키 입력·실행

아래 명령은 Docker 엔진, Git, Python 3.12 설치 후 새 PowerShell에서 실행합니다.

```powershell
git clone https://github.com/SEOUL-raphael/gov-manual-weknora-public.git
cd gov-manual-weknora-public
$taskPython = py -3.12 -c "import sys; print(sys.executable)"
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -Python $taskPython
notepad .env
```

생성된 .env의 MINIMAX_API_KEY와 NVIDIA_API_KEY에 전달받은 값을 입력합니다. DB·Redis·관리자 비밀번호는 자동 생성됩니다. 다른 PC의 .env 전체를 복사하지 마세요. 모델명과 API 주소는 기본값을 유지합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

첫 실행에는 이미지 다운로드와 모델 로딩으로 시간이 걸립니다. 완료 후 **http://localhost:18765** 에 접속하여 .env의 ADMIN_EMAIL / ADMIN_PASSWORD로 로그인합니다.

UI·API·리랭커의 호스트 포트는 로컬 접속만 허용합니다. 기본 포트는 각각 18765, 18766, 18768입니다. 저장소 공개 여부와 실행 서비스의 외부 공개 여부는 별개입니다.

## 문서 넣기와 확인

**기존 문서, 계정, DB, 임베딩 캐시는 포함하지 않습니다.** 같은 자료로 시연하려면 사용 권한이 있는 문서를 별도로 받아 UI에서 업로드하세요. 새 설치에서는 문서를 다시 청킹·임베딩하므로 API 사용량이 발생합니다.

작은 문서 1개로 처리 완료를 확인한 뒤 내용에 관해 질문하고 근거를 확인하세요. 외부 모델 API로 문서 내용이 전송될 수 있습니다.

```powershell
docker compose ps
.\.venv\Scripts\python.exe scripts/verify_reranker.py
```

리랭커 검사는 CPU에서 한국어 예문을 처리하며, MiniMax·NVIDIA 호출 성공이나 전체 문서 검색 품질을 대신 검증하지 않습니다.

## 종료와 재실행

```powershell
docker compose stop
# Docker Desktop 실행 후 다시 시작
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

데이터는 프로젝트 전용 Docker 볼륨에 저장합니다. **docker compose down -v는 DB·문서 볼륨을 삭제하므로 일반 종료에 사용하지 마세요.**

## 기존 자료 이관 (선택)

원본 gov-manual-rag 프로젝트의 SQLite와 추출 Markdown을 가지고 있는 관리자만 export_corpus.py와 import_corpus.py를 사용합니다. 일반 설치에는 원본 프로젝트나 upstream 소스 복제가 필요하지 않습니다.

```powershell
.\.venv\Scripts\python.exe scripts/export_corpus.py --help
.\.venv\Scripts\python.exe scripts/import_corpus.py --help
```

이관 도구는 원본 DB를 읽기 전용으로 열고 별도 사본을 생성합니다. 내보낸 자료를 확인한 뒤 소량으로 이관을 검증하세요. verify_live.py는 이 코퍼스 전체의 적재와 검색을 검사하는 관리자용 도구입니다.

## 이동 설치와 온라인 접속

[배포·이동 설치 안내](DEPLOYMENT.md)를 참고하세요.

```powershell
.\.venv\Scripts\python.exe scripts/build_bundle.py --output D:/weknora-offline-install
```

이동 설치 묶음에는 Docker 이미지와 리랭커 모델이 포함되지만 기존 계정·문서·DB·키는 없습니다. Docker·WSL2·Python은 대상 PC에 별도 설치해야 합니다. **오프라인 설치 이후에도 MiniMax·NVIDIA 호출에는 인터넷이 필요합니다.**

Cloudflare Tunnel 연결은 실행 PC가 계속 켜져 있어야 합니다. Cloudflare Containers와 Supabase 조합의 배포는 이 저장소에서 검증된 설치 방식이 아닙니다.

## 검증 범위

2026-09-29 기준 기존 Windows PC의 별도 설치 폴더에서 Python 의존성 오프라인 설치, Docker 이미지 7개 로드, 서비스 기동, 새 계정·지식베이스와 2048차원 인덱스 생성, CPU 한국어 리랭킹을 확인했습니다. 당시 단위 테스트는 12개 통과했습니다.

개발 환경에서 원본 문서 1,209개를 별도 Markdown으로 내보내고 체크섬을 검사했습니다. 이 문서들은 저장소에 포함되지 않으며, 전체 코퍼스의 검색·답변 품질 검증이 완료됐다는 의미는 아닙니다. 동료의 새 PC와 API 키는 해당 환경에서 별도로 검증해야 합니다.

## 출처와 라이선스

- [Tencent/WeKnora](https://github.com/Tencent/WeKnora/tree/v0.8.0)
- [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- 버전과 설정 체크섬: [UPSTREAM.lock.json](UPSTREAM.lock.json)
- 포함된 WeKnora 설정 및 원본 고지: [licenses/WeKnora-LICENSE.txt](licenses/WeKnora-LICENSE.txt)

자체 설치 스크립트의 별도 배포 라이선스는 아직 지정하지 않았습니다. WeKnora의 라이선스가 모든 자체 코드에 자동 적용되는 것으로 해석하지 마세요. Docker 이미지와 모델은 각 배포자의 라이선스를 따릅니다.
