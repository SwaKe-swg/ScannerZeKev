import json
import time
from pathlib import Path
from config import Config

_PATH = Path(__file__).resolve().parent.parent / "paper_blacklist.json"


def _load() -> dict:
    if not _PATH.exists():
        return {"addresses": {}, "symbols": {}}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"addresses": {}, "symbols": {}}


def _save(data: dict) -> None:
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_blacklisted(address: str, symbol: str) -> tuple[bool, str]:
    data = _load()
    now = time.time()
    hours = float(getattr(Config, "BLACKLIST_HOURS", 6.0))
    cutoff = now - hours * 3600
    # purge expired
    data["addresses"] = {k: v for k, v in data.get("addresses", {}).items() if v >= cutoff}
    data["symbols"] = {k: v for k, v in data.get("symbols", {}).items() if v >= cutoff}
    _save(data)
    if address and address in data["addresses"]:
        return True, "address_blacklist"
    if symbol and symbol.upper() in data["symbols"]:
        return True, "symbol_blacklist"
    return False, ""


def add_blacklist(address: str, symbol: str, reason: str = "stop_loss") -> None:
    data = _load()
    now = time.time()
    if address:
        data.setdefault("addresses", {})[address] = now
    if symbol:
        data.setdefault("symbols", {})[symbol.upper()] = now
    data.setdefault("last_reason", {})[address or symbol] = reason
    _save(data)
