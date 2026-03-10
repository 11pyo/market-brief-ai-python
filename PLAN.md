# market-brief-ai-python — 빌드 계획

> 현재 Node.js 버전의 기능을 Python으로 재구축. CSS/UI 디자인은 그대로 유지.
> 전략: 기존 로직을 복사하지 않고, Python 생태계에 맞게 최적화.

---

## 1. 기술 스택 선택

| 역할 | Node.js (현재) | Python (신규) | 선택 이유 |
|------|--------------|--------------|----------|
| 웹 프레임워크 | Express 5 | **FastAPI** | async 네이티브, SSE 내장, 자동 docs |
| HTTP 클라이언트 | axios | **httpx** (async) | async/await 지원, Finnhub 직접 호출 |
| 시장 데이터 | 직접 Yahoo Finance API 호출 (폴백 3단계) | **yfinance** 라이브러리 | 이미 폴백 내장, 코드 1/5로 감소 |
| 뉴스 수집 | Finnhub REST 직접 호출 | **httpx** 직접 호출 | SDK 없이 완전 async, 패키지 1개 감소 |
| 설정 관리 | dotenv | **pydantic-settings** | 타입 검증, 기본값, IDE 자동완성 |
| LLM - OpenAI | openai npm | **openai** Python SDK | 동일 기능 |
| LLM - Gemini | @google/generative-ai | **google-genai** | 신 SDK (구버전 deprecated) |
| LLM - Claude | 없음 | **anthropic** | 선택적 3번째 옵션 |
| 스케줄러 | node-cron | **APScheduler** (AsyncIOScheduler) | FastAPI async 루프와 통합 |
| 마크다운 파싱 | 프론트엔드에서 직접 파싱 | 프론트엔드에서 직접 파싱 | 변경 없음 |

---

## 2. 프로젝트 구조

```
market-brief-ai-python/
├── main.py                      # FastAPI 앱 진입점 (서버 초기화, 라우트, CORS)
├── config.py                    # [신규] pydantic-settings 기반 설정 관리
├── schemas.py                   # [신규] 공유 Pydantic 모델 (API 응답/요청 타입)
├── scheduler.py                 # APScheduler 기반 자동 생성 스케줄러
├── services/
│   ├── market_data.py           # yfinance로 시장 데이터 (asyncio.timeout 적용)
│   ├── news_collector.py        # httpx 직접 Finnhub 호출 (완전 async)
│   ├── news_filter.py           # 키워드 점수 기반 필터링
│   ├── llm_engine.py            # OpenAI/Gemini/Claude LLM 엔진
│   ├── portfolio_manager.py     # 포트폴리오 저장/로드
│   └── briefing_store.py        # [신규] 브리핑 저장/조회/자동 정리
├── data/
│   ├── briefings/               # 생성된 브리핑 JSON
│   ├── portfolio.json           # 사용자 포트폴리오
│   └── settings.json            # 앱 설정
├── public/                      # 프론트엔드 (현재 프로젝트에서 복사)
│   ├── index.html
│   ├── css/style.css            # 그대로 유지
│   └── js/app.js                # API 경로만 확인 후 그대로 유지
├── .env                         # API 키 및 설정
├── .env.example
├── requirements.txt
└── .gitignore
```

**Node.js 대비 구조 변화:**
- `src/server.js` + `src/scheduler.js` → `main.py` + `scheduler.py` (최상위로)
- `config.py`, `schemas.py`, `briefing_store.py` 신규 추가 (구조 명확화)
- `analyticsManager.js` 제거 → 방문자 통계 기능 삭제 (불필요한 복잡성)
- `services/` 구조 동일하되 Python 컨벤션(snake_case)으로

---

## 3. 각 모듈 설계

### 3-1. config.py (신규)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    finnhub_api_key: str
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""       # 선택적

    llm_provider: str = "openai"      # openai | gemini | anthropic
    llm_model: str = "gpt-4o"
    llm_fallback_model: str = "gemini-2.0-flash"

    port: int = 3000
    tz: str = "Asia/Seoul"
    briefing_cron: str = "0 7 * * *"
    max_briefings: int = 30           # 보관할 최대 브리핑 수

settings = Settings()  # 싱글턴: 모든 서비스에서 from config import settings
```

`os.getenv()` 패턴 완전 제거. 타입 오류는 앱 시작 시 즉시 발견.

### 3-2. schemas.py (신규)

```
공유 Pydantic 모델:
- NewsItem         : 뉴스 항목 (id, headline, source, url, datetime, score)
- MarketSnapshot   : 시장 데이터 (symbol, price, change, change_percent)
- BriefingRecord   : 브리핑 전체 (id, date, content, market_data, news_count, model_used)
- SSEEvent         : SSE 이벤트 (type, step, message, data)

FastAPI 라우트의 response_model= 에 직접 사용.
```

### 3-3. main.py (FastAPI 서버)

```
역할: 라우팅, 정적 파일 서빙, 앱 생명주기 관리

엔드포인트:
GET  /api/briefing/latest           → 최신 브리핑
GET  /api/briefing/history          → 브리핑 목록 (limit 파라미터)
GET  /api/briefing/{id}             → 특정 브리핑
GET  /api/briefing/generate/stream  → SSE 스트리밍 생성
GET  /api/market/snapshot           → 시장 데이터
GET  /api/portfolio                 → 포트폴리오 조회
POST /api/portfolio                 → 포트폴리오 저장
GET  /api/settings                  → 설정 조회
POST /api/settings                  → 설정 저장
GET  /api/status                    → 서버 상태
GET  /*                             → index.html (SPA 폴백)

주요 구현:
- lifespan 이벤트로 스케줄러 시작/종료 관리
- CORS 미들웨어 (CORSMiddleware, allow_origins=["*"])
- SSE 연결 해제 처리: request.is_disconnected() 체크
- 정적 파일: StaticFiles 마운트 (/static → public/)
```

SSE 연결 해제 처리:
```python
@app.get("/api/briefing/generate/stream")
async def briefing_stream(request: Request):
    async def generate():
        async for event in scheduler.run_with_progress():
            if await request.is_disconnected():
                break
            yield f"data: {event.model_dump_json()}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

### 3-4. services/market_data.py

```
현재 문제: Node.js에서 Yahoo Finance API를 직접 호출 + 3단계 폴백 구현
신규 접근: yfinance 라이브러리 사용

핵심 개선:
- 3단계 수동 폴백 로직 → yfinance.Ticker().fast_info 단 1줄
- 비동기: asyncio.run_in_executor로 yfinance (동기 라이브러리) 래핑
- asyncio.timeout(30) 으로 hang 방지
- 코드량: 약 200줄 → 약 60줄

추적 심볼 (동일):
^GSPC, ^IXIC, ^DJI, ^TNX, DX-Y.NYB, CL=F,
^VIX, GC=F, EURUSD=X, BTC-USD, ^KS11, KRW=X
```

### 3-5. services/news_collector.py

```
현재: axios로 Finnhub REST API 직접 호출, 중복 제거, 24h 필터
신규: httpx.AsyncClient로 직접 호출 (finnhub-python SDK 제거)

핵심 개선:
- sync SDK + run_in_executor → 완전 async httpx 직접 호출
- asyncio.timeout(15) 로 카테고리별 타임아웃
- return_exceptions=True 로 한 카테고리 실패 시 나머지 계속
- 코드량: 약 80줄 → 약 50줄

수집 카테고리: general, forex, crypto, merger (동일)
결과: 최근 24시간 내 중복 제거 후 최대 50건
```

### 3-6. services/news_filter.py

```
현재 로직 그대로 유지 (점수 시스템이 잘 설계되어 있음)
단순히 Python으로 변환, schemas.NewsItem 사용:

점수 시스템:
- high_priority 키워드: +3점
- medium_priority 키워드: +1점
- 시간 가중: 3h이내 +5, 6h이내 +3, 12h이내 +1

반환: 상위 30건 (최소 20건)
```

### 3-7. services/briefing_store.py (신규)

```
역할: 브리핑 파일 저장/조회/자동 정리 (scheduler + main 양쪽에서 재사용)

함수:
- save_briefing(record)     : JSON 저장 + MAX_BRIEFINGS 초과 시 자동 정리
- load_latest()             : 최신 브리핑 반환
- load_by_id(id)            : 특정 브리핑 반환
- list_briefings(limit)     : 목록 반환

자동 정리:
파일 수가 settings.max_briefings 초과 시 오래된 것부터 삭제 (~10줄)
```

### 3-8. services/llm_engine.py

```
현재 문제:
- 폴백 체인이 복잡하게 얽혀 있음
- google-generativeai deprecated (gemini-2.0-flash 등 모델 접근 불가)

신규 설계:
- google-genai 신 SDK로 Gemini 호출
- provider 체인: 설정 provider → 폴백 provider (API 키 있는 것 순)
- anthropic SDK로 Claude 선택적 지원
- 각 호출에 asyncio.timeout(120) 적용

폴백 체인:
설정 모델 → 설정 폴백 모델 (2단계)

모델명 env 관리:
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_FALLBACK_MODEL=gemini-2.0-flash

프롬프트: 기존 PART 1-7 구조 그대로 유지
온도: 0.7 (동일)
```

### 3-9. services/portfolio_manager.py

```
기존 로직 동일:
- data/portfolio.json 읽기/쓰기
- LLM 입력용 텍스트 포맷팅
- 기본 포트폴리오: 주식 60%, 테크 20%, 암호화폐 10%, 현금 10%

schemas 모델로 타입 안전성 확보
```

### 3-10. scheduler.py

```
현재: node-cron 기반, 브리핑 생성 파이프라인
신규: APScheduler AsyncIOScheduler

파이프라인:
1. asyncio.gather(news_collector.collect_all(), market_data.get_snapshot())  ← 병렬
2. news_filter.filter_news()
3. portfolio_manager.get_portfolio()
4. llm_engine.generate_briefing()
5. briefing_store.save_briefing()                                            ← 신규 모듈 사용

개선:
- asyncio.gather()로 뉴스+시장데이터 병렬 수집 (현재는 순차)
- 중복 실행 방지: asyncio.Lock() 사용
- 기본 스케줄: 매일 07:00 KST
```

---

## 4. SSE (Server-Sent Events) 구현

```python
# FastAPI에서 SSE는 StreamingResponse + async generator로 구현
from fastapi.responses import StreamingResponse

async def generate_stream(request: Request):
    async for event in scheduler.run_with_progress():
        if await request.is_disconnected():
            break
        yield f"data: {event.model_dump_json()}\n\n"

@app.get("/api/briefing/generate/stream")
async def briefing_stream(request: Request):
    return StreamingResponse(
        generate_stream(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
```

진행 단계 이벤트 (프론트엔드 로딩 오버레이와 호환):
- `{"type": "progress", "step": 1, "message": "뉴스 수집 중..."}`
- `{"type": "progress", "step": 2, "message": "시장 데이터 수집 중..."}`
- `{"type": "progress", "step": 3, "message": "AI 분석 중..."}`
- `{"type": "complete", "data": {...}}`
- `{"type": "error", "message": "..."}`

---

## 5. 프론트엔드 변경 사항

기존 CSS/HTML/JS 100% 유지. 변경 없음.

---

## 6. 환경변수 (.env)

```env
# API Keys
FINNHUB_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
ANTHROPIC_API_KEY=      # 선택적

# LLM 설정
LLM_PROVIDER=openai     # openai | gemini | anthropic
LLM_MODEL=gpt-4o
LLM_FALLBACK_MODEL=gemini-2.0-flash

# 서버
PORT=3000
TZ=Asia/Seoul

# 스케줄
BRIEFING_CRON=0 7 * * *
MAX_BRIEFINGS=30        # 보관할 최대 브리핑 수 (초과 시 자동 삭제)
```

---

## 7. requirements.txt

```
fastapi
uvicorn[standard]
pydantic-settings
httpx
yfinance
openai
google-genai
anthropic
apscheduler
```

**기존 대비 변경:**
- 제거: `python-dotenv`, `finnhub-python`, `google-generativeai`, `pydantic`(자동 포함)
- 추가: `pydantic-settings`, `google-genai`, `anthropic`
- 순 패키지 수: 10 → 9

---

## 8. 빌드 순서 (구현 단계)

| 단계 | 파일 | 설명 |
|------|------|------|
| 1 | `requirements.txt`, `.env.example`, `.gitignore` | 개선된 패키지 목록 |
| 2 | `config.py` | pydantic-settings Settings 클래스 — 모든 서비스가 이것부터 import |
| 3 | `schemas.py` | 공유 Pydantic 모델 전체 정의 |
| 4 | `services/market_data.py` | yfinance + asyncio.timeout |
| 5 | `services/news_collector.py` | httpx 직접 호출 (SDK 없이) |
| 6 | `services/news_filter.py` | 단순 포팅, schemas.NewsItem 사용 |
| 7 | `services/briefing_store.py` | 저장/조회/자동 정리 |
| 8 | `services/llm_engine.py` | google-genai 신 SDK + anthropic 분기 |
| 9 | `services/portfolio_manager.py` | schemas 모델 사용 |
| 10 | `scheduler.py` | 파이프라인 + asyncio.Lock + SSE 이벤트 yield |
| 11 | `main.py` | CORS, lifespan, 모든 라우트, SSE 연결 해제 처리 |
| 12 | `public/` | 기존 파일 그대로 복사 |
| 13 | 통합 테스트 | 브리핑 생성 E2E 테스트 |

---

## 9. 주요 최적화 포인트 (기존 대비)

| 항목 | 기존 | 개선 |
|------|------|------|
| 시장 데이터 수집 | Yahoo Finance API 직접 호출 + 수동 폴백 3단계 (~200줄) | yfinance 라이브러리 + asyncio.timeout (~60줄) |
| 뉴스 수집 | axios REST 호출 | httpx 직접 async 호출 (SDK 불필요) |
| 뉴스+시장 데이터 수집 | 순차 실행 | `asyncio.gather()` 병렬 실행 |
| LLM 폴백 체인 | 4단계 (복잡) | 2단계 (env 기반) |
| Gemini SDK | google-generativeai (deprecated) | google-genai (신 SDK) |
| 설정 관리 | `os.getenv()` 산발적 호출 | pydantic-settings 타입 안전 중앙화 |
| 브리핑 저장 로직 | scheduler/main에 분산 | briefing_store.py 전담 모듈 |
| 브리핑 파일 정리 | 없음 | MAX_BRIEFINGS 초과 시 자동 삭제 |
| API 타임아웃 | 없음 | asyncio.timeout으로 hang 방지 |
| SSE 연결 해제 | 없음 | request.is_disconnected() 체크 |
| CORS | 없음 | CORSMiddleware 추가 |
| 타입 안전성 | 없음 | Pydantic 모델 (schemas.py 중앙화) |
| 모델명 관리 | 하드코딩 | 전부 env 변수화 |
| 코드 총량 | ~1,200줄 (서비스) | ~620줄 예상 |

---

## 10. 실행 방법 (완성 후)

```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 실행
uvicorn main:app --reload --port 3000

# 프로덕션 실행
uvicorn main:app --host 0.0.0.0 --port 3000
```
