class Config:
    # --- MODALITÀ TRADING ---
    REAL_TRADING = False               # False = Paper Trading Ultra-Realistico | True = Real Trading
    SOLANA_PRIVATE_KEY = ""           # Inserisci la tua chiave privata Base58 (solo se REAL_TRADING = True)
    
    # --- PARAMETRI DI BUDGET ---
    VIRTUAL_SOL_BALANCE = 0.30        # Budget virtuale libero in SOL
    TRADE_AMOUNT_SOL = 0.03           # Importo per singolo trade in SOL
    
    # --- PROTEZIONE REALE (SLIPPAGE & FEES) ---
    SLIPPAGE_BPS = 150                # 150 BPS = 1.5% Slippage massimo
    ESTIMATED_FEE_SOL = 0.0015        # Fee di rete + Priority Fee / Jito Tip per tx
    
    # --- TARGET PROFIT E LOSS ---
    TAKE_PROFIT_PCT = 100.0           # Target Take Profit (+100%)
    STOP_LOSS_PCT = -30.0             # Initial Stop Loss (-30%)
    
    # --- TELEGRAM ---
    TELEGRAM_BOT_TOKEN = "IL_TUO_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID = "IL_TUO_TELEGRAM_CHAT_ID"
    
    # --- RPC HELIUS INTEGRATO ---
    HELIUS_RPC_URL = "https://mainnet.helius-rpc.com/?api-key=92640d40-dd7c-44ca-b920-3d99f6b55abc"
    
    # --- API PREZZI ---
    DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"