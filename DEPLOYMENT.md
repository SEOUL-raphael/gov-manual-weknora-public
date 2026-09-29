# 다른 PC 설치와 Cloudflare 공개 접속

Cloudflare Tunnel로 HTTPS 접속 주소를 붙일 수 있다. WeKnora·DB·리랭커는 현재 PC나 별도 Docker 서버에서 실행해야 한다. Pages/Workers에 이 구성을 그대로 올리는 방식은 아니다. PC가 꺼지면 사이트도 중단된다.

## 새 PC에 설치

대상: Windows x64, Python 3.12 x64, Docker Desktop의 WSL2 Linux 컨테이너. RAM 16GB 이상과 여유 디스크 40GB 이상을 권장하며 문서 규모에 따라 추가 공간이 필요하다.

1. 저장소를 복제한다. 실행에 upstream 소스 복제는 필요하지 않다.
2. `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1` 실행.
3. 생성된 .env에 본인의 MiniMax·NVIDIA API 키를 입력.
4. `powershell -ExecutionPolicy Bypass -File scripts/start.ps1` 실행.
5. http://localhost:18765 접속. .env의 ADMIN_EMAIL/ADMIN_PASSWORD로 로그인.

## 오프라인 설치 묶음

인터넷이 되는 준비 PC에서:
```powershell
.\.venv\Scripts\python.exe scripts/build_bundle.py --output D:/weknora-offline-install
```

완성된 폴더 전체를 대상 PC로 복사한다. 전체 용량이 약 5GB이므로 여유 공간을 확인하고 NTFS/exFAT 저장장치를 권장한다.
**Docker Desktop/WSL2와 Python 3.12 x64는 대상 PC에 미리 설치해야 한다.** 운영체제 선행 프로그램 설치 파일은 포함하지 않는다.

```powershell
Set-Location D:/weknora-offline-install
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -Offline
# .env에 본인의 API 키를 넣은 후
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

오프라인 설치는 체크섬 검사, 로컬 wheel 설치(--no-index), Docker 이미지 로드로 진행한다.
이 패키지는 **새 설치용**이다. 기존 계정·DB·문서·API 키는 포함하지 않으며, 기존 상태를 옮기는 백업/복원은 별도 작업이다.

**완전 폐쇄망 RAG가 아니다.** UI·DB·리랭커는 로컬이지만 MiniMax 답변과 NVIDIA 임베딩은 인터넷이 필요하다.
폐쇄망 운영을 위해서는 답변/임베딩 모델을 로컬 모델로 대체하고 새 지식베이스를 만들어 재색인해야 한다.

## Cloudflare Tunnel

먼저 로컬 관리자 계정 생성까지 완료한다.

1. Cloudflare Zero Trust에서 named tunnel을 생성한다.
2. Docker 커넥터 토큰만 .secrets/tunnel-token에 저장한다. 이 파일은 Git 제외 대상이다.
3. Public hostname을 weknora.<내 도메인>으로 지정하고 서비스는 http://frontend:80으로 연결한다.
4. .env에 PUBLIC_URL=https://weknora.<내 도메인>을 추가한다.
5. 공개 전 관리자 설정의 신규 가입을 비활성화한다. 기존 DB 정책은 환경변수보다 우선할 수 있다.
6. 개인용이면 Cloudflare Access에 본인 이메일 허용 정책을 설정한다.
7. 다음 명령을 실행한다.

```powershell
docker compose -f compose.yaml -f deploy/compose.tunnel.yaml up -d
```

실제 계정 인증과 호스트명이 제공되기 전에는 공개 주소가 생성되지 않는다.
DB·Redis·리랭커는 공개하지 않는다. 브라우저는 frontend를 통해 API에 접근한다.
Cloudflare의 업로드 크기·요청 제한이 적용되므로 큰 PDF와 긴 요청은 공개 후 별도 검증한다.
공식 문서: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/

## 출처와 배포 범위

GitHub에는 설치 코드와 설정 예제만 올린다. 모델과 Docker 이미지는 로컬 이동 설치 폴더에만 포함한다.
Tencent/WeKnora v0.8.0의 커밋과 기본 설정 체크섬은 UPSTREAM.lock.json에 고정했다.
복사한 기본 설정의 라이선스는 licenses/WeKnora-LICENSE.txt이며, Docker 이미지와 BGE 모델의 라이선스는 각 배포자의 조건을 따른다.

## 2026-09-29 검증

- 단위 테스트 12개 통과, 비밀키 제외 검사 및 upstream 설정 체크섬 통과.
- 별도 폴더/Compose 프로젝트/포트에서 새 관리자와 지식베이스 생성, 서비스 7개 정상 기동, 2048차원 인덱스 생성 확인.
- 새 설치본의 한국어 리랭킹 실측 통과(관련 문서 1위, 점수 0.8888).
- 모델의 첫 로딩에 약 4분 30초가 걸려 초기 상태 검사 유예 시간을 늘렸다.
- Python 의존성은 로컬 wheel만으로 설치했고, Docker 이미지 7개를 images.tar에서 성공적으로 가져왔다. 이 PC에서는 이미지 가져오기에 약 15분이 걸렸다.
- 위 실행 검증은 같은 PC의 별도 설치본에서 수행했으며, 새 PC/물리적 네트워크 차단/외부 LLM 호출/Cloudflare 공개 도메인 검증은 포함하지 않는다.
