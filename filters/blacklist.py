import json
import time
from pathlib import Path
from config import Config

_PATH = Path(__file__).resolve().parent.parent / "paper_blacklist.json"

# Permanent never-reenter lessons (do not expire)
PERMANENT_SYMBOLS = {"NP", "WIRE"}
PERMANENT_ADDRESSES = {
    # $NP stop-loss never-green lesson
    "H61eoVSK7XmGmAA3NTt5d3Rg4WDxvqMfqpWSeZSJk1aG",
    # $WIRE falling-knife lesson
    "HExJd47752Q2Nqm1EpMDrvfPKWdeVtZ3ATh1TukU1tYn",
}


def _load() -> dict:
    if not _PATH.exists():
        return {"addresses": {}, "symbols": {}, "permanent_symbols": [], "permanent_addresses": []}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"addresses": {}, "symbols": {}, "permanent_symbols": [], "permanent_addresses": []}


def _save(data: dict) -> None:
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _permanent_sets(data: dict) -> tuple[set, set]:
    syms = set(PERMANENT_SYMBOLS)
    addrs = set(PERMANENT_ADDRESSES)
    for s in data.get("permanent_symbols") or []:
        if s:
            syms.add(str(s).upper())
    for a in data.get("permanent_addresses") or []:
        if a:
            addrs.add(str(a))
    return addrs, syms


def is_blacklisted(address: str, symbol: str) -> tuple[bool, str]:
    data = _load()
    perm_addrs, perm_syms = _permanent_sets(data)
    if address and address in perm_addrs:
        return True, "permanent_address_blacklist"
    if symbol and symbol.upper() in perm_syms:
        return True, "permanent_symbol_blacklist"

    now = time.time()
    hours = float(getattr(Config, "BLACKLIST_HOURS", 6.0))
    cutoff = now - hours * 3600
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


def add_permanent(address: str = "", symbol: str = "", reason: str = "permanent") -> None:
    data = _load()
    if symbol:
        ps = data.setdefault("permanent_symbols", [])
        up = symbol.upper()
        if up not in ps:
            ps.append(up)
    if address:
        pa = data.setdefault("permanent_addresses", [])
        if address not in pa:
            pa.append(address)
    data.setdefault("last_reason", {})[address or symbol] = reason
    _save(data)
