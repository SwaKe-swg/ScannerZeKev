import logging
import httpx
from config import Config

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(self, initial_balance=0.30, trade_amount=0.03):
        self.balance = initial_balance
        self.trade_amount = trade_amount
        self.positions = {}
        self.slippage_factor = 1.0 + (Config.SLIPPAGE_BPS / 10000.0) # 1.015 (+1.5% slippage)

    def open_virtual_trade(self, token_address: str, symbol: str, raw_price_usd: float) -> dict:
        max_open = int(getattr(Config, "MAX_OPEN_POSITIONS", 2))
        if len(self.positions) >= max_open:
            logger.warning(f"Max posizioni aperte ({max_open}) raggiunto, skip ${symbol}")
            return None
        if token_address in self.positions:
            return None
        total_cost = self.trade_amount + Config.ESTIMATED_FEE_SOL
        if self.balance < total_cost:
            logger.warning(f"âš ï¸ Saldo insufficiente ({self.balance:.4f} SOL) incluso fee ({Config.ESTIMATED_FEE_SOL} SOL) per ${symbol}")
            return None

        self.balance -= total_cost
        execution_price = raw_price_usd * self.slippage_factor

        trade_info = {
            "symbol": symbol,
            "address": token_address,
            "token_address": token_address,
            "buy_sol": self.trade_amount,
            "entry_price_usd": execution_price,
            "current_price_usd": execution_price,
            "max_pnl_reached": 0.0,
            "pnl_pct": 0.0,
            "pnl_sol": 0.0,
            "status": "OPEN"
        }
        self.positions[token_address] = trade_info
        logger.info(f"ðŸ§ª [BUY] ${symbol} @ ${execution_price:.8f} (Slippage: {Config.SLIPPAGE_BPS/100}% | Fee: {Config.ESTIMATED_FEE_SOL} SOL)")
        return trade_info

    async def get_fast_price(self, client: httpx.AsyncClient, token_address: str, default_price: float) -> float:
        """Lettura ad alta frequenza da Jupiter Price API v2."""
        try:
            url = f"{Config.JUPITER_PRICE_API}?ids={token_address}"
            res = await client.get(url, timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                price_str = data.get("data", {}).get(token_address, {}).get("price")
                if price_str:
                    return float(price_str)
        except Exception:
            pass

        # Fallback rapido su DexScreener
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            res = await client.get(url, timeout=3.0)
            if res.status_code == 200:
                pairs = res.json().get("pairs")
                if pairs:
                    return float(pairs[0].get("priceUsd", default_price))
        except Exception:
            pass

        return default_price

    async def update_positions_pnl(self, client: httpx.AsyncClient, take_profit_pct: float = 100.0, initial_stop_loss_pct: float = -30.0):
        open_updates = []
        closed_trades = []
        to_remove = []

        for addr, pos in list(self.positions.items()):
            try:
                current_price = await self.get_fast_price(client, addr, pos["current_price_usd"])
                pos["current_price_usd"] = current_price
                entry = pos["entry_price_usd"]

                if entry > 0:
                    raw_pnl_pct = ((current_price - entry) / entry) * 100.0
                    pos["pnl_pct"] = raw_pnl_pct
                    pos["pnl_sol"] = pos["buy_sol"] * (raw_pnl_pct / 100.0)

                    if raw_pnl_pct > pos["max_pnl_reached"]:
                        pos["max_pnl_reached"] = raw_pnl_pct

                # Trailing stop: blocca prima i guadagni, taglia prima le perdite
                dynamic_stop_loss = initial_stop_loss_pct
                max_p = pos["max_pnl_reached"]

                if max_p >= 30.0:
                    dynamic_stop_loss = 15.0
                elif max_p >= 20.0:
                    dynamic_stop_loss = 8.0
                elif max_p >= 12.0:
                    dynamic_stop_loss = 3.0
                elif max_p >= 6.0:
                    dynamic_stop_loss = 0.0

                # Chiusura Posizioni
                if raw_pnl_pct >= take_profit_pct or raw_pnl_pct <= dynamic_stop_loss:
                    is_tp = raw_pnl_pct >= take_profit_pct
                    if is_tp:
                        pos["status"] = f"TAKE PROFIT (obiettivo +{take_profit_pct:.0f}%)"
                    elif dynamic_stop_loss > initial_stop_loss_pct:
                        pos["status"] = (
                            f"TRAILING STOP (aveva toccato {max_p:+.1f}%, "
                            f"chiuso a {raw_pnl_pct:+.1f}%)"
                        )
                    else:
                        pos["status"] = (
                            f"STOP LOSS (limite {initial_stop_loss_pct:.0f}%, "
                            f"chiuso a {raw_pnl_pct:+.1f}%)"
                        )

                    # PenalitÃ  Slippage in vendita e sottrazione Priority Fee
                    exit_price_after_slippage = current_price / self.slippage_factor
                    realized_pnl_pct = ((exit_price_after_slippage - entry) / entry) * 100.0
                    realized_pnl_sol = pos["buy_sol"] * (realized_pnl_pct / 100.0)
                    
                    net_returned_sol = max(0.0, pos["buy_sol"] + realized_pnl_sol - Config.ESTIMATED_FEE_SOL)
                    self.balance += net_returned_sol
                    
                    pos["pnl_pct"] = realized_pnl_pct
                    pos["pnl_sol"] = realized_pnl_sol - Config.ESTIMATED_FEE_SOL
                    
                    closed_trades.append(pos)
                    to_remove.append(addr)
                else:
                    open_updates.append(pos)

            except Exception as e:
                logger.error(f"Errore update PnL ${pos['symbol']}: {e}")

        for addr in to_remove:
            del self.positions[addr]

        return open_updates, closed_trades

    def get_balance(self) -> float:
        return self.balance

    def get_total_equity_sol(self) -> float:
        open_val = sum(pos["buy_sol"] + pos["pnl_sol"] for pos in self.positions.values())
        return self.balance + open_val