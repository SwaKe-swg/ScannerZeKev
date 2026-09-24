def build_trading_links_text(token_address: str) -> str:
    axiom_url = f"https://axiom.trade/token/{token_address}"
    photon_url = f"https://photon-sol.tinyastro.io/en/lp/{token_address}"
    bullx_url = f"https://neo.bullx.io/terminal?chainId=1399811149&address={token_address}"
    pump_url = f"https://pump.fun/coin/{token_address}"
    dex_url = f"https://dexscreener.com/solana/{token_address}"

    return (
        "<b>Link rapidi (solo per guardare il token):</b>\n"
        f'• <a href="{axiom_url}">Axiom</a>\n'
        f'• <a href="{photon_url}">Photon</a>\n'
        f'• <a href="{bullx_url}">BullX</a>\n'
        f'• <a href="{pump_url}">Pump.fun</a>\n'
        f'• <a href="{dex_url}">DexScreener</a>'
    )
