"""
브리핑 저장소.
- Upstash Redis 설정 시: Redis에 영구 저장 (Render 재시작 무관)
- Redis 미설정 시: 로컬 파일 fallback (개발환경)
"""
import json
import logging
from pathlib import Path

import httpx

from config import settings
from schemas import BriefingRecord

logger = logging.getLogger(__name__)

BRIEFINGS_DIR = Path("data/briefings")


# ===== Redis helpers =====

def _redis_enabled() -> bool:
    return bool(settings.upstash_redis_url and settings.upstash_redis_token)


async def _redis_pipeline(commands: list) -> list:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(
                f"{settings.upstash_redis_url}/pipeline",
                headers={"Authorization": f"Bearer {settings.upstash_redis_token}"},
                json=commands,
            )
            body = r.json()
            if not isinstance(body, list):
                logger.warning(f"[BriefingStore] Redis 비정상 응답: {body}")
                return []
            return [item.get("result") if isinstance(item, dict) else None for item in body]
    except Exception as e:
        logger.warning(f"[BriefingStore] Redis 호출 실패: {e}")
        return []


# ===== File fallback helpers =====

def _ensure_dir() -> None:
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)


def _cleanup_old_files() -> None:
    files = sorted(BRIEFINGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    for old in files[: -settings.max_briefings]:
        old.unlink()


def _load_file(path: Path) -> BriefingRecord | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return BriefingRecord(**data)
    except Exception as e:
        logger.warning(f"[BriefingStore] 파일 로드 실패 {path.name}: {e}")
        return None


# ===== Public API (async) =====

async def save_briefing(record: BriefingRecord) -> None:
    if _redis_enabled():
        await _redis_pipeline([
            ["SET", f"briefing:{record.id}", record.model_dump_json()],
            ["LPUSH", "briefings:ids", record.id],
            ["LTRIM", "briefings:ids", 0, settings.max_briefings - 1],
        ])
        logger.info(f"[BriefingStore] Redis 저장: {record.id}")
        return

    _ensure_dir()
    path = BRIEFINGS_DIR / f"{record.date}_{record.id}.json"
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"[BriefingStore] 파일 저장: {path.name}")
    _cleanup_old_files()


async def load_latest() -> BriefingRecord | None:
    if _redis_enabled():
        results = await _redis_pipeline([["LRANGE", "briefings:ids", 0, 0]])
        if results and results[0]:
            latest_id = results[0][0]
            r2 = await _redis_pipeline([["GET", f"briefing:{latest_id}"]])
            if r2 and r2[0]:
                try:
                    return BriefingRecord(**json.loads(r2[0]))
                except Exception as e:
                    logger.warning(f"[BriefingStore] Redis 파싱 실패: {e}")
        return None

    _ensure_dir()
    files = sorted(BRIEFINGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return _load_file(files[0]) if files else None


async def load_by_id(briefing_id: str) -> BriefingRecord | None:
    if _redis_enabled():
        results = await _redis_pipeline([["GET", f"briefing:{briefing_id}"]])
        if results and results[0]:
            try:
                return BriefingRecord(**json.loads(results[0]))
            except Exception as e:
                logger.warning(f"[BriefingStore] Redis 파싱 실패: {e}")
        return None

    _ensure_dir()
    for f in BRIEFINGS_DIR.glob("*.json"):
        if briefing_id in f.name:
            return _load_file(f)
    return None


async def list_briefings(limit: int = 20) -> list[BriefingRecord]:
    if _redis_enabled():
        results = await _redis_pipeline([["LRANGE", "briefings:ids", 0, limit - 1]])
        if results and results[0]:
            ids = results[0]
            cmds = [["GET", f"briefing:{bid}"] for bid in ids]
            raw_list = await _redis_pipeline(cmds)
            out = []
            for raw in raw_list:
                if raw:
                    try:
                        out.append(BriefingRecord(**json.loads(raw)))
                    except Exception:
                        pass
            return out
        return []

    _ensure_dir()
    files = sorted(BRIEFINGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for f in files[:limit]:
        record = _load_file(f)
        if record:
            result.append(record)
    return result
