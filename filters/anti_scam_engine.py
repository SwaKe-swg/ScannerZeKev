"""Anti-scam engine v2.3 — fail-closed hard reds using RugCheck + Helius + Dex fields."""
from __future__ import annotations

import logging
from typing import Any

from config import Config

logger = logging.getLogger(__name__)


async def run_anti_scam_checks(
    token_address: str,
    dex_data: dict | None = None,
) -> tuple[bool, str, list[str]]:
    """
    Run automatable anti-scam checks.
    Returns (ok, reason, failed_check_names).
    Fail-closed on hard reds when APIs respond; soft-skip only when explicitly configured.
    """
    dex_data = dex_data or {}
    failed: list[str] = []
    soft_notes: list[str] = []

    liq = float(dex_data.get("liquidity_usd", 0) or 0)
    fdv = float(dex_data.get("fdv", 0) or dex_data.get("market_cap", 0) or 0)
    buys = int(dex_data.get("buys_m5", 0) or 0)
    sells = int(dex_data.get("sells_m5", 0) or 0)
    chg = float(dex_data.get("price_change_m5", 0) or 0)

    if getattr(Config, "CHECK_LIQ_MC_RATIO", True) and fdv > 0 and liq / fdv < float(
        getattr(Config, "MIN_LIQ_MC_RATIO", 0.10)
    ):
        failed.append("liq_mc_ratio")
        _log_fail(token_address, "liq_mc_ratio", f"liq/mc={liq/fdv:.3f}")

    if getattr(Config, "CHECK_HONEYPOT_ZERO_SELLS", True) and buys >= int(
        getattr(Config, "HONEYPOT_ZERO_SELL_BUYS", 25)
    ) and sells == 0:
        failed.append("honeypot_zero_sells")
        _log_fail(token_address, "honeypot_zero_sells", f"buys={buys} sells=0")

    if getattr(Config, "REQUIRE_MOMENTUM_BUY_CONSISTENCY", True):
        if chg >= float(getattr(Config, "MIN_PRICE_CHANGE_M5", 3.0)) and sells > 0:
            if buys < sells * float(getattr(Config, "MIN_BUY_SELL_RATIO", 1.2)):
                failed.append("momentum_buy_inconsistent")
                _log_fail(
                    token_address,
                    "momentum_buy_inconsistent",
                    f"chg={chg:+.1f}% buys={buys} sells={sells}",
                )

    rug: dict[str, Any] = {}
    if getattr(Config, "USE_RUGCHECK", True):
        try:
            from dex.rugcheck import check_rug_pull
            rug = await check_rug_pull(token_address)
        except Exception as e:
            logger.warning("RugCheck error %s: %s", token_address[:8], e)
            if getattr(Config, "FAIL_CLOSED_RUGCHECK", False):
                failed.append("rugcheck_api_error")
                _log_fail(token_address, "rugcheck_api_error", str(e))
            else:
                soft_notes.append("rugcheck_unavailable")

    if rug:
        if getattr(Config, "CHECK_RUGCHECK_HONEYPOT", True) and rug.get("is_honeypot"):
            failed.append("rugcheck_honeypot")
            _log_fail(token_address, "rugcheck_honeypot", rug.get("reasons"))

        if getattr(Config, "CHECK_RUGCHECK_RENOUNCED", True) and rug.get("is_renounced") is False:
            failed.append("mint_not_renounced_rugcheck")
            _log_fail(token_address, "mint_not_renounced_rugcheck", "")

        raw = int(rug.get("raw_score") or 0)
        max_raw = int(getattr(Config, "MAX_RUGCHECK_RAW_SCORE", 1500))
        if getattr(Config, "CHECK_RUGCHECK_SCORE", True) and raw >= max_raw:
            failed.append("rugcheck_high_score")
            _log_fail(token_address, "rugcheck_high_score", f"raw={raw}")

        reasons = [str(r).lower() for r in (rug.get("reasons") or [])]
        danger_kw = ("freeze", "mint", "honeypot", "transfer fee", "mutable", "authority", "rug")
        if getattr(Config, "CHECK_RUGCHECK_DANGER", True):
            for r in reasons:
                if any(k in r for k in danger_kw):
                    failed.append(f"rugcheck_danger:{r[:40]}")
                    _log_fail(token_address, "rugcheck_danger", r)
                    break

        lp = str(rug.get("lp_locked", "unknown")).lower()
        if getattr(Config, "REQUIRE_LP_LOCKED_OR_BURNED", False) and lp not in ("yes", "burned", "locked"):
            if getattr(Config, "FAIL_CLOSED_LP", False):
                failed.append("lp_not_locked")
                _log_fail(token_address, "lp_not_locked", lp)
            else:
                soft_notes.append(f"lp_status={lp}")

    onchain: dict[str, Any] = {}
    if getattr(Config, "USE_ONCHAIN_CHECKS", True) and getattr(Config, "HELIUS_API_KEY", ""):
        try:
            from dex.onchain import check_solana_mint_security
            onchain = await check_solana_mint_security(token_address)
        except Exception as e:
            logger.warning("Onchain error %s: %s", token_address[:8], e)
            if getattr(Config, "FAIL_CLOSED_ONCHAIN", True):
                failed.append("onchain_api_error")
                _log_fail(token_address, "onchain_api_error", str(e))
            else:
                soft_notes.append("onchain_unavailable")

    if onchain:
        if onchain.get("safe") is False:
            reason = str(onchain.get("reason") or "onchain_unsafe")
            tag = "onchain_unsafe"
            if "mint" in reason.lower():
                tag = "mint_authority_active"
            elif "freeze" in reason.lower():
                tag = "freeze_authority_active"
            failed.append(tag)
            _log_fail(token_address, tag, reason)

        fee_pct = float(onchain.get("transfer_fee_pct") or 0)
        max_fee = float(getattr(Config, "MAX_TRANSFER_FEE_PCT", 5.0))
        if getattr(Config, "CHECK_TRANSFER_FEE", True) and fee_pct > max_fee:
            failed.append("token2022_transfer_fee")
            _log_fail(token_address, "token2022_transfer_fee", f"{fee_pct}%")

        top_pct = float(onchain.get("top_holder_pct") or 0)
        max_top = float(getattr(Config, "MAX_TOP_HOLDER_PCT", 20.0))
        if getattr(Config, "CHECK_TOP_HOLDER", True) and top_pct > max_top > 0:
            failed.append("top_holder_concentration")
            _log_fail(token_address, "top_holder_concentration", f"{top_pct:.1f}%")

    if failed:
        seen = set()
        uniq = []
        for f in failed:
            if f not in seen:
                seen.add(f)
                uniq.append(f)
        reason = "ANTI_SCAM: " + ", ".join(uniq[:5])
        logger.warning("[ANTI_SCAM FAIL] %s -> %s", token_address[:12], reason)
        return False, reason, uniq

    if soft_notes:
        logger.info("[ANTI_SCAM OK soft] %s notes=%s", token_address[:12], soft_notes)
    else:
        logger.info("[ANTI_SCAM OK] %s", token_address[:12])
    return True, "SAFE", []


def _log_fail(addr: str, check: str, detail: Any) -> None:
    logger.warning("[ANTI_SCAM] check=%s mint=%s detail=%s", check, addr[:12], detail)


async def confirm_entry_still_green(
    token_address: str,
    signal_price: float,
    signal_chg_m5: float,
) -> tuple[bool, str, dict]:
    """Wait CONFIRM_ENTRY_SECONDS then re-fetch; abort if flat/red or drawdown > X%."""
    import asyncio
    import httpx

    wait_s = float(getattr(Config, "CONFIRM_ENTRY_SECONDS", 20))
    max_dd = float(getattr(Config, "CONFIRM_MAX_DRAWDOWN_PCT", 5.0))
    min_chg = float(getattr(Config, "MIN_PRICE_CHANGE_M5", 3.0))

    if wait_s > 0:
        await asyncio.sleep(wait_s)

    out = {
        "signal_price": signal_price,
        "confirm_price": signal_price,
        "confirm_chg_m5": signal_chg_m5,
        "drawdown_pct": 0.0,
    }
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            res = await client.get(url)
            if res.status_code != 200:
                if getattr(Config, "FAIL_CLOSED_CONFIRM", True):
                    return False, "confirm_fetch_failed", out
                return True, "confirm_skip_fetch", out
            pairs = res.json().get("pairs") or []
            if not pairs:
                if getattr(Config, "FAIL_CLOSED_CONFIRM", True):
                    return False, "confirm_no_pairs", out
                return True, "confirm_skip_pairs", out
            p = pairs[0]
            price = float(p.get("priceUsd") or 0)
            pc = (p.get("priceChange") or {}).get("m5")
            chg = float(pc or 0)
            out["confirm_price"] = price
            out["confirm_chg_m5"] = chg
            if signal_price > 0 and price > 0:
                dd = ((price - signal_price) / signal_price) * 100.0
                out["drawdown_pct"] = dd
                if dd < -abs(max_dd):
                    logger.warning("[CONFIRM] abort %s drawdown=%.1f%%", token_address[:12], dd)
                    return False, f"confirm_drawdown({dd:.1f}%)", out
            if chg < min_chg:
                logger.warning(
                    "[CONFIRM] abort %s still flat/red chg_m5=%+.1f%%",
                    token_address[:12],
                    chg,
                )
                return False, f"confirm_momentum({chg:+.1f}%)", out
    except Exception as e:
        logger.error("confirm_entry error: %s", e)
        if getattr(Config, "FAIL_CLOSED_CONFIRM", True):
            return False, f"confirm_error:{e}", out
    return True, "CONFIRMED", out
