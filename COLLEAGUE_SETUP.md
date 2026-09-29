# 동료용 설치 안내 — Windows, GPU 불필요

WeKnora 원래 화면과 기능을 Docker에서 실행합니다. ParadeDB·Redis·문서 파서가 포함되어 Supabase와 Cloudflare는 필요 없습니다. 답변은 MiniMax API, 임베딩은 NVIDIA API, 리랭커는 CPU 모델을 사용합니다. NVIDIA GPU는 필요 없습니다.

## 1. 준비

- Docker Desktop이 지원하는 Windows x64와 WSL2 환경. Windows 11을 권장합니다.
- RAM 16GB 이상, 여유 디스크 40GB 이상 권장. 문서량에 따라 더 필요합니다.
- 인터넷이 필요합니다. 이미지·모델 다운로드와 MiniMax/NVIDIA API 접속을 확인하세요.
- 이 공개 저장소를 복제하거나 GitHub의 Code → Download ZIP으로 받으세요.
- MiniMax·NVIDIA API 키는 소유자가 별도로 전달합니다. GitHub에는 들어 있지 않습니다.

## 2. Docker·Python 설치

관리자 PowerShell에서 WSL을 준비합니다. 이미 WSL2를 사용한다면 필요한 업데이트만 수행하세요.

```powershell
wsl --install --no-distribution
wsl --update
```

재시작 요청이 있으면 Windows를 재시작하세요. BIOS/UEFI 가상화가 활성화되어 있어야 합니다.

공식 설치 프로그램으로 다음을 설치합니다.

- [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/): WSL2 백엔드, Linux containers 사용
- [Python 3.12 Windows x64](https://www.python.org/downloads/windows/): Python launcher 포함
- [Git for Windows](https://git-scm.com/downloads/win): 소스 ZIP 이용 시 생략 가능

Docker Desktop을 직접 열어 초기 설정을 완료하고 엔진이 실행될 때까지 기다립니다. 기관 PC에서는 설치 권한과 Docker Desktop 라이선스 적용 여부를 확인하세요.

새 PowerShell에서:

```powershell
wsl --version
docker version
docker compose version
py -3.12 --version
```

Docker는 Client뿐 아니라 Server 정보도 나와야 합니다. 명령을 못 찾으면 설치 후 새 터미널을 열거나 설치 경로를 확인하세요.

## 3. 저장소 받기·설치

```powershell
git clone https://github.com/SEOUL-raphael/gov-manual-weknora-public.git
cd gov-manual-weknora-public
$taskPython = py -3.12 -c "import sys; print(sys.executable)"
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -Python $taskPython
```

GitHub 인증에는 본인 계정을 사용하세요. ZIP이라면 압축을 푼 후 compose.yaml이 있는 폴더에서 마지막 두 줄을 실행합니다.

설치 스크립트는 가상환경, 새 PC 전용 비밀번호, CPU 리랭커 모델을 준비합니다. 모델은 약 2.3GB이며 첫 실행에 Docker 이미지도 다운로드합니다. 실패 원인을 해결한 뒤 같은 명령으로 재시도할 수 있습니다. 기존 .env는 보존됩니다.

## 4. 별도로 전달받은 API 키 입력

```powershell
notepad .env
```

아래 두 항목에 실제 값을 입력합니다. 아래는 예시이며 실제 키가 아닙니다.

```dotenv
MINIMAX_API_KEY='전달받은 MiniMax 키'
NVIDIA_API_KEY='전달받은 NVIDIA 키'
```

MiniMax-M3 모델명과 API 주소는 기본값을 유지합니다. DB·Redis·JWT 비밀번호는 자동 생성되므로 다른 PC의 .env 전체를 복사하지 마세요. 로그인 정보는 ADMIN_EMAIL과 ADMIN_PASSWORD입니다. 키나 비밀번호가 보이는 화면을 공유하지 마세요.

## 5. 실행과 확인

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

첫 기동과 모델 로딩에는 수 분이 걸립니다. 완료되면 **http://localhost:18765** 에 접속하고 .env의 관리자 계정으로 로그인하세요.

```powershell
docker compose ps
.\.venv\Scripts\python.exe scripts/verify_reranker.py
```

리랭커 검증은 한국어 예문을 CPU로 처리합니다. 외부 API 검증은 UI에서 작은 문서 1개를 업로드하고 처리 완료 후 그 내용에 관해 질문하여 답변과 근거를 확인하세요. 사용할 권한이 있는 자료로 시험하며 API 사용량은 해당 키 계정에 청구됩니다.

**GitHub에는 기존 문서·DB·계정이 없습니다.** 같은 자료로 시연하려면 소유자가 승인한 문서를 별도로 받아 UI에서 업로드합니다. 새 PC에서는 다시 청킹·임베딩하므로 API 사용량이 발생합니다. 원본 D:\gov-manual-rag 경로를 사용하는 이관 스크립트는 동료의 일반 설치에 필요 없습니다.

## 6. 종료·재실행

```powershell
# 데이터는 유지하고 서비스만 정지
docker compose stop
# 다음에 Docker Desktop을 연 뒤 실행
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

**docker compose down -v는 DB·문서가 있는 볼륨을 삭제하므로 실행하지 마세요.** 실행 중 명령은 Ctrl+C로 중단할 수 있지만, 이미 백그라운드로 실행된 서비스는 docker compose stop으로 정지합니다. UI는 설치한 PC에서만 접속하도록 설정되어 있습니다.

## 문제 해결

| 증상 | 확인 |
|---|---|
| Docker Server 연결 실패 | Desktop 실행, WSL2 업데이트, 재시작 |
| 포트 충돌 | .env의 UI_PORT·API_PORT·필요 시 RERANK_PORT 변경 후 재실행 |
| 모델 로딩 지연/메모리 부족 | 여유 RAM 확보, Docker 리소스 확인, 초기 로딩 대기 |
| API 401/403·쿼터 오류 | 전달받은 키의 모델 접근 권한과 잔여 사용량 확인 |
| GitHub 404 | 복제 주소와 저장소 이름 확인 |
| 다운로드 차단 | 기관의 승인된 다운로드·파일 반입 절차 이용 |

오류 확인: `docker compose logs --tail 100 app reranker docreader`. 공유 전에 키·문서 내용·개인정보를 확인하세요.

## 오프라인 설치 파일을 전달받는 경우

소유자가 만든 이동 설치 폴더 전체를 복사합니다. Docker·WSL2·Python은 별도 설치해야 합니다. 이동 폴더에서:

```powershell
$taskPython = py -3.12 -c "import sys; print(sys.executable)"
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -Offline -Python $taskPython
```

이후 API 키 입력과 실행은 같습니다. 이동 묶음도 기존 문서·계정·DB·키는 포함하지 않습니다. **오프라인 설치 후에도 MiniMax·NVIDIA API에는 인터넷이 필요합니다.**

검증 범위: 기존 Windows PC의 별도 설치 폴더에서 로컬 wheel 설치, Docker 이미지 7개 가져오기, 새 계정 생성, 서비스 기동, CPU 리랭킹을 확인했습니다. 동료의 새 PC에 Docker/WSL을 설치하는 과정과 전달받은 키의 실제 API 호출은 해당 PC에서 확인해야 합니다.
