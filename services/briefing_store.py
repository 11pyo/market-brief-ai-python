import json
import logging
from pathlib import Path

from config import settings
from schemas import BriefingRecord

logger = logging.getLogger(__name__)

BRIEFINGS_DIR = Path("data/briefings")


def _ensure_dir() -> None:
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)


def save_briefing(record: BriefingRecord) -> None:
    _ensure_dir()
    path = BRIEFINGS_DIR / f"{record.date}_{record.id}.json"
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"[BriefingStore] 저장: {path.name}")
    _cleanup_old()


def _cleanup_old() -> None:
    files = sorted(BRIEFINGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    for old in files[: -settings.max_briefings]:
        old.unlink()
        logger.info(f"[BriefingStore] 오래된 브리핑 삭제: {old.name}")


def load_latest() -> BriefingRecord | None:
    _ensure_dir()
    files = sorted(BRIEFINGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    return _load_file(files[0])


def load_by_id(briefing_id: str) -> BriefingRecord | None:
    _ensure_dir()
    for f in BRIEFINGS_DIR.glob("*.json"):
        if briefing_id in f.name:
            return _load_file(f)
    return None


def list_briefings(limit: int = 20) -> list[BriefingRecord]:
    _ensure_dir()
    files = sorted(BRIEFINGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for f in files[:limit]:
        record = _load_file(f)
        if record:
            result.append(record)
    return result


def _load_file(path: Path) -> BriefingRecord | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return BriefingRecord(**data)
    except Exception as e:
        logger.warning(f"[BriefingStore] 파일 로드 실패 {path.name}: {e}")
        return None
