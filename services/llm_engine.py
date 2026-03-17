import asyncio
import logging
import time

from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """YOUR CORE DIRECTIVE:
1. Generate a 6-part market briefing ONLY (Parts 1-6).
2. DO NOT include "Expert Panel", "전문가 패널", or any fictional commentary from Buffett, Musk, Trump, etc.
3. If user portfolio data is provided, add "PART 7 — 포트폴리오 맞춤 조언" as the final section.
4. STRICTLY FORBIDDEN: Any sections or parts other than 1-6 and optionally 7.

You are a professional macro strategist and cross-asset trader.
Your job is NOT to summarize news, but to transform news into actionable market insight.
Think like a hedge fund morning strategist.

Reasoning Chain:
Geopolitics/Macro -> Commodities/Rates/FX -> Equities -> Sector Rotation -> Trade Ideas.

Focus on signal over noise. Use professional financial terminology in Korean (한국어).

CRITICAL FOR PART 1: Always name the specific person (e.g., Trump, Powell, Yellen, Bessent) and their exact action or statement. Never open PART 1 with vague phrases like "글로벌 불확실성이 고조되고 있다" or "지정학적 리스크가 확대되고 있다". Lead with the concrete overnight event that most directly explains today's pre-market direction."""

FRAMEWORK_PROMPT = """Generate a daily market briefing using this EXACT structure:

PART 1 — 어젯밤 핵심 이벤트 & 시장 충격 분석
  규칙 (반드시 준수):
  1. ⚡ BREAKING 섹션에 항목이 있으면 그 내용이 PART 1의 첫 번째 주제여야 한다.
  2. 첫 문장: "어젯밤 [실명: Trump/Powell/Jensen Huang 등]이/가 [구체적 발표/수치/결정]을 발표하여 [지수/섹터/종목]에 [상승/하락/변동폭]을 미쳤다." 형식.
  3. 대통령 발표, 연준 발언, 주요 기업(NVDA/AAPL 등) 실적·제품 발표가 있으면 반드시 별도 항목으로 각각 다룬다.
  4. "글로벌 불확실성", "지정학적 리스크" 같은 추상 표현으로 시작 금지. 반드시 구체적 사건·수치·발언 인용.

PART 2 — 시장 방향성 확률
  반드시 아래 3줄 형식으로 시작 (합계=100%):
  📈 상승: XX%
  ➡️ 횡보: XX%
  📉 하락: XX%
  이후 각 시나리오의 핵심 근거 2-3줄.

PART 3 — 섹터 리더십
  주도 섹터(상위 3개)와 약세 섹터(하위 2개)를 명시하고, 각 섹터의 등락 이유 1문장.
  가능하면 ETF 심볼(XLK, XLE, XLF 등) 언급.

PART 4 — 핵심 리스크

PART 5 — 트레이드 아이디어
  반드시 아래 형식, 최소 2개:
  🎯 [종목/자산] [롱/숏]
  진입: [구체적 가격대] | 목표: [목표가] | 손절: [손절선] | R/R: 1:[비율]
  근거: [기술적/펀더멘털 근거, 수치 포함 1-2문장]

PART 6 — 10초 마켓 대시보드

CRITICAL: STOP IMMEDIATELY after PART 6. DO NOT generate an Expert Panel."""


LANG_INSTRUCTIONS = {
    "ko": "Korean (한국어)",
    "en": "English",
    "zh": "Chinese (中文)",
    "ja": "Japanese (日本語)",
}

PART7_LABELS = {
    "ko": "PART 7 — 포트폴리오 맞춤 조언",
    "en": "PART 7 — Personalized Portfolio Advice",
    "zh": "PART 7 — 个性化投资组合建议",
    "ja": "PART 7 — 個別ポートフォリオアドバイス",
}


def _build_user_prompt(news_text: str, market_text: str, portfolio_text: str = "", lang: str = "ko") -> str:
    lang_str = LANG_INSTRUCTIONS.get(lang, "English")
    part7_label = PART7_LABELS.get(lang, PART7_LABELS["en"])
    prompt = f"{FRAMEWORK_PROMPT}\n\n---\n\n{market_text}\n\n---\n\n{news_text}\n\n"
    if portfolio_text:
        prompt += (
            f"---\n\n=== USER PORTFOLIO ===\n{portfolio_text}\n\n"
            "Based on the user's portfolio above, provide ADDITIONAL personalized advice:\n"
            "- How today's macro events specifically impact their holdings\n"
            "- Any rebalancing suggestions\n"
            "- Risk alerts specific to their portfolio composition\n"
            f'Include this as "{part7_label}" at the very end. DO NOT generate an expert panel.\n\n'
        )
    prompt += f"---\n\nUsing the framework and data above, produce today's Morning Market Briefing in {lang_str}. STOP completion as soon as you output Part 6 (or Part 7 if applicable)."
    return prompt


async def _call_openai(user_prompt: str) -> tuple[str, str]:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    model = settings.llm_model
    logger.info(f"[LLM] OpenAI {model} 호출 중...")
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )
    content = resp.choices[0].message.content or ""
    return content, model


GEMINI_MODELS = [
    "gemini-3.0-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
]


async def _call_gemini(user_prompt: str, model_name: str | None = None) -> tuple[str, str]:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=settings.gemini_api_key)

    models_to_try = [model_name] if model_name else GEMINI_MODELS
    last_error: Exception | None = None

    for model in models_to_try:
        logger.info(f"[LLM] Gemini {model} 호출 중...")
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7,
                    max_output_tokens=2000,
                ),
            )
            content = response.text or ""
            return content, model
        except Exception as e:
            logger.warning(f"[LLM] Gemini {model} 실패: {e}, 다음 모델 시도...")
            last_error = e

    raise last_error


async def _call_anthropic(user_prompt: str) -> tuple[str, str]:
    import anthropic
    model = settings.llm_model if "claude" in settings.llm_model else "claude-opus-4-6"
    logger.info(f"[LLM] Anthropic {model} 호출 중...")
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model=model,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.7,
    )
    content = message.content[0].text if message.content else ""
    return content, model


def _build_provider_chain() -> list:
    """사용 가능한 provider 체인 구성. 기본 provider 먼저, 나머지 폴백."""
    provider = settings.llm_provider.lower()
    all_providers = []

    if provider == "openai" and settings.openai_api_key:
        all_providers.append(_call_openai)
    elif provider == "gemini" and settings.gemini_api_key:
        all_providers.append(_call_gemini)
    elif provider == "anthropic" and settings.anthropic_api_key:
        all_providers.append(_call_anthropic)

    # 폴백: 기본 provider 외 나머지를 모두 추가
    for fn, key in [
        (_call_openai, settings.openai_api_key),
        (_call_gemini, settings.gemini_api_key),
        (_call_anthropic, settings.anthropic_api_key),
    ]:
        if key and fn not in all_providers:
            all_providers.append(fn)

    return all_providers


async def generate_briefing(
    news_text: str,
    market_text: str,
    portfolio_text: str = "",
    lang: str = "ko",
) -> tuple[str, str, int]:
    """
    브리핑 생성.
    Returns: (content, model_name, generation_time_ms)
    """
    user_prompt = _build_user_prompt(news_text, market_text, portfolio_text, lang)
    chain = _build_provider_chain()

    if not chain:
        raise RuntimeError("사용 가능한 LLM provider가 없습니다. API 키를 확인하세요.")

    start = time.time()
    last_error: Exception | None = None

    for provider_fn in chain:
        try:
            async with asyncio.timeout(120):
                content, model_name = await provider_fn(user_prompt)
            elapsed_ms = int((time.time() - start) * 1000)
            logger.info(f"[LLM] 완료 ({elapsed_ms}ms) | 모델: {model_name}")
            return content, model_name, elapsed_ms
        except Exception as e:
            logger.warning(f"[LLM] {provider_fn.__name__} 실패: {e}, 다음 provider 시도...")
            last_error = e

    raise RuntimeError(f"모든 LLM provider 실패: {last_error}")
