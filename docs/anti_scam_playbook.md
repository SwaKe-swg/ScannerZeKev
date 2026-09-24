# Zephyr Anti-Scam Playbook v2.3

> Paper bot only (`REAL_TRADING=False`). Nessun metodo e infallibile: stacka filtri, fail-closed sui hard red.

## Legenda
- **AUTO** — implementato / cablato nel path di ingresso (RugCheck + Helius + DexScreener + blacklist + CONFIRM_ENTRY)
- **FUTURE** — automabile con API aggiuntive (Jito, funding graph, Token-2022 deep parse, Jupiter sim)
- **MANUAL** — richiede umano / UI esterna (Bubblemaps, social DYOR)

## Metodi (100+)

1. **Mint authority revoked (null)** — `AUTO` — Helius getAccountInfo — no infinite mint
2. **Freeze authority revoked** — `AUTO` — Helius — classic Solana honeypot lever
3. **Token-2022 transfer fee <= threshold** — `AUTO` — Parse transferFeeConfig; reject >5%
4. **RugCheck honeypot / freeze / fee flags** — `AUTO` — api.rugcheck.xyz summary risks
5. **RugCheck danger/critical reasons** — `AUTO` — Fail on danger-level risk names
6. **RugCheck raw score ceiling** — `AUTO` — Reject raw_score >= 1500
7. **Mint renounced (RugCheck)** — `AUTO` — is_renounced false -> reject
8. **Top-1 holder concentration** — `AUTO` — getTokenLargestAccounts / supply
9. **Liquidity / market-cap ratio** — `AUTO` — liq/fdv >= 10%
10. **Min liquidity USD** — `AUTO` — DexScreener liquidity.usd
11. **Market cap floor** — `AUTO` — Avoid micro rugs
12. **Market cap ceiling** — `AUTO` — Avoid late chase / already pumped
13. **Min buys m5** — `AUTO` — Activity filter
14. **Buy/sell pressure ratio** — `AUTO` — buys >= sells * ratio
15. **Min volume m5** — `AUTO` — DexScreener volume.m5
16. **Min price change m5 (no falling knife)** — `AUTO` — Reject chg_m5 < MIN (3%+)
17. **Max price change m5 (already pumped)** — `AUTO` — Reject parabolic late entries
18. **Late-chase heuristic** — `AUTO` — Many buys + weak momentum
19. **Zero-sell honeypot heuristic** — `AUTO` — Many buys, zero sells
20. **Entry score threshold** — `AUTO` — score_pair >= MIN_ENTRY_SCORE
21. **Symbol quality / length** — `AUTO` — Alnum + max length
22. **Blacklist address (timed)** — `AUTO` — paper_blacklist after SL
23. **Blacklist symbol (timed)** — `AUTO` — Avoid re-entry same ticker
24. **Permanent symbol blacklist** — `AUTO` — NP, WIRE never-green lessons
25. **CONFIRM_ENTRY re-fetch** — `AUTO` — Wait 15-25s; abort flat/red
26. **CONFIRM drawdown from signal** — `AUTO` — Abort if price drops > X% after signal
27. **Momentum vs buy consistency** — `AUTO` — Rising price must match buy pressure
28. **Cooldown between entries** — `AUTO` — Rate-limit paper exposure
29. **Max open positions** — `AUTO` — Cap concurrent risk
30. **Stop-loss + trailing** — `AUTO` — Risk manager exits
31. **Take-profit target** — `AUTO` — Lock winners
32. **LP status note from RugCheck** — `AUTO` — Soft unless REQUIRE_LP
33. **Fail-closed onchain API errors** — `AUTO` — When HELIUS set
34. **Slippage + fee modeling** — `AUTO` — Paper realism
35. **Dex id preference in score** — `AUTO` — raydium/orca/meteora bonus
36. **Socials presence soft score** — `AUTO` — info.websites/socials
37. **AntiRugEngine aggregate gate** — `AUTO` — verify_token_safety orchestration
38. **Log failed check names** — `AUTO` — Transparency for tuning
39. **Top-10 holder concentration excl LP** — `FUTURE` — Sum top10 minus pool vaults
40. **Same-funder wallet cluster** — `FUTURE` — Trace SOL funding ancestry
41. **Jito atomic launch bundles** — `FUTURE` — Bundle ID clustering at t0
42. **Serial deployer reputation** — `FUTURE` — Prior rugs / survival rate
43. **Fresh wallet top-holder flood** — `FUTURE` — Holders created hours before launch
44. **Sniper retention (still holding)** — `FUTURE` — Early buyers dumped vs held
45. **Dev wallet still holding %** — `FUTURE` — Creator supply retention
46. **Insider network (RugCheck graph)** — `FUTURE` — Shared characteristics among whales
47. **PermanentDelegate Token-2022** — `FUTURE` — Can confiscate any balance
48. **TransferHook present** — `FUTURE` — Programmable sell block
49. **TransferHook upgrade authority** — `FUTURE` — Malicious post-deploy upgrade
50. **NonTransferable extension** — `FUTURE` — Hard honeypot
51. **DefaultAccountState Frozen** — `FUTURE` — New accounts frozen
52. **Pausable extension / pause authority** — `FUTURE` — Global transfer halt
53. **Transfer fee authority still live** — `FUTURE` — 0% today, 99% tomorrow
54. **MintCloseAuthority** — `FUTURE` — Supply accounting edge cases
55. **Update/metadata authority mutable** — `FUTURE` — Phishing link swap in metadata
56. **Metadata URI points to IPFS vs ephemeral** — `FUTURE` — Social rug via metadata
57. **Copycat ticker vs known brands** — `FUTURE` — Symbol collision with majors
58. **Duplicate / near-dupe logo hash** — `FUTURE` — Image reuse across rugs
59. **Social handle copycat (extra underscore)** — `FUTURE` — X/TG impersonation
60. **X account prior CAs posted** — `FUTURE` — Serial promoter history
61. **X account age vs token age** — `FUTURE` — Brand-new socials on 'organic' claim
62. **DexScreener paid boost + dump pattern** — `FUTURE` — Boost then exit
63. **Age vs volume spike mismatch** — `FUTURE` — Hours old + insane vol = wash
64. **Wash trading circular flows** — `FUTURE` — Same wallets buy/sell loop
65. **Identical trade size bot cluster** — `FUTURE` — Compute-unit / tip fingerprint
66. **Multi-hop funding chain** — `FUTURE` — Mixer -> many buyers
67. **Exchange-funded vs OTC-funded buyers** — `FUTURE` — Quality of flow
68. **LP burned vs time-locked vs unlocked** — `FUTURE` — Locker contract verify
69. **Fake LP lock screenshots** — `MANUAL` — Off-chain social scam
70. **Raydium vs Pump.fun migration honesty** — `FUTURE` — Fake 'graduated' claims
71. **Bonding curve completion authenticity** — `FUTURE` — Pump.fun specific
72. **Pool vault excluded from top holders** — `FUTURE` — Avoid false concentration
73. **Burn address holdings counted correctly** — `FUTURE` — Dead supply vs float
74. **Simulate tiny Jupiter buy+sell** — `FUTURE` — Round-trip honeypot sim
75. **Priority fee / tip anomaly at launch** — `FUTURE` — MEV sniper storm
76. **Slot-0 multi-wallet buys** — `FUTURE` — Almost always bundled
77. **Creator funded early buyers** — `FUTURE` — Dev sybil
78. **Holder overlap across sister tokens** — `FUTURE` — Same crowd rugs
79. **Bubblemaps cluster visual review** — `MANUAL` — MANUAL cluster map
80. **GoPlus / external risk API** — `FUTURE` — Third-party composite
81. **Birdeye security fields** — `FUTURE` — When available
82. **Helius enhanced txs bot-cluster** — `FUTURE` — Operator forensics
83. **Operator profile / known serial DB** — `FUTURE` — SolSentry-style lists
84. **Telegram group admin ownership check** — `MANUAL` — Stolen community
85. **Website domain age / WHOIS** — `MANUAL` — Throwaway domains
86. **SSL / cloned WordPress templates** — `MANUAL` — Generic scam sites
87. **Roadmap/guarantee language NLP** — `MANUAL` — 'guaranteed 100x'
88. **Pressure language ('launch in 5 min')** — `MANUAL` — FOMO social eng
89. **Team doxx / multisig treasury** — `MANUAL` — Higher quality projects
90. **Liquidity depth levels (not just TVL)** — `FUTURE` — Thin book rugs
91. **Impact price for TRADE_SIZE_SOL** — `FUTURE` — Can we exit size?
92. **Cross-DEX liquidity split** — `FUTURE` — Fragmented exit
93. **Oracle / price feed manipulation** — `FUTURE` — Thin pool mark
94. **Token decimals weirdness** — `FUTURE` — 9 vs 6 traps / UI tricks
95. **Supply != marketed supply** — `FUTURE` — Metadata lie
96. **Freeze+thaw selective wallets** — `FUTURE` — Allowlist dump
97. **Blacklist extension Token-2022** — `FUTURE` — Account blocklist
98. **InterestBearing / ScaledUiAmount tricks** — `FUTURE` — Balance illusion
99. **Confidential transfer opacity** — `FUTURE` — Hidden flow
100. **CPI Guard / immmutable owner nuances** — `FUTURE` — Edge Token-2022
101. **Dev sold into first green candle** — `FUTURE` — Immediate dump
102. **KOL wallet cluster dump sync** — `FUTURE` — Paid shill exit
103. **Reply-guy bot networks on X** — `MANUAL` — Fake engagement
104. **Telegram bot comment farms** — `MANUAL` — Fake social proof
105. **Pinned CA mismatch vs Dex link** — `MANUAL` — Wrong contract bait
106. **Multiple mint addresses same brand** — `FUTURE` — Impostor mints
107. **Renounce after first buyers only** — `FUTURE` — Delayed trap
108. **LP migrate to unlocked pool** — `FUTURE` — Rug via migration
109. **Authority re-enabled via upgradeable program** — `FUTURE` — Proxy rug
110. **Stake farm fake APY drain** — `FUTURE` — Secondary scam
111. **Airdrop claim phishing site** — `MANUAL` — Off-bot manual
112. **Seed phrase DM after loss** — `MANUAL` — Support impersonation

## Fonti segnale pubbliche / nicchia (solo nomi — caveat: spesso scammy)

Questi feed sono **discovery**, non buy-signal. Molti canali promuovono token tossici o affiliati.

| Nome / handle | Tipo | Nota |
|---|---|---|
| Solana New Deploys (`solana_new_deploys`) | New mints | Feed deploy + mint/freeze flags |
| Solana New Tokens WITH TG (`SolanaDeploysTG` / `solanadeploystg`) | New mints w/ TG | Solo token con Telegram in metadata |
| Solana New Token Bot (`SolanaNewListing`) | Listings | Spesso legato a trading bot ads |
| Solana New Tokens (`solanatokensnew`) | New coins | Alert pre-trade; alta rumorosita |
| Solana New Pairs DEX Screener (`DSNewPairsSolana`) | New pairs | Raydium/FluxBeam style alerts |
| SolanaListing (sibling of SolanaNewListing) | Listings | Cross-promo trading bots |
| Trenchy (Telegram research bot) | Scan tool | Deployer + sniper/bundle context |
| SolSentry Telegram | Scan/alerts | Serial operator history |
| DeFade / MadeOnSol deployer hunter | Web tools | Bundle + serial deployer research |
| RugCheck.xyz | Scanner | Traffic-light Solana standard |

### Caveat IT
- I gruppi 'alpha' pubblici sono pieni di shill a pagamento e CA fasulli.
- Non join-required per il bot: usiamo DexScreener + on-chain, non signal group.
- Se un feed postea CA, verifica SEMPRE mint/freeze/LP e momentum 5m prima di qualsiasi paper entry.

## Nicchia che pochi bot usano (priorita FUTURE)
1. Same-funder + Jito bundle overlap (alta confidenza sybil).
2. Token-2022 PermanentDelegate / TransferHook upgrade authority.
3. Transfer-fee authority live anche a 0% fee corrente.
4. Logo perceptual-hash copycat across dead ticks.
5. Sniper retention + coordinated first-block sells.
6. Age vs volume spike + wash circular flows.
7. CONFIRM_ENTRY delay (noi: AUTO in 2.3) — evita never-green tipo $NP.

Totale metodi elencati: **112**. AUTO cablati tipicamente: **38** (piu gate compositi).

