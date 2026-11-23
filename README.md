# World News Atlas — Monday 23 November 2026

[![Competition](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123)
[![Rank](https://make.fun/badge/news-image-20261123/mevlanayalcin/world-news-canvas-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123)
[![Reward](https://make.fun/badge/news-image-20261123/mevlanayalcin/world-news-canvas-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123)

An illustrated one-page world news atlas summing up **Monday 23 November 2026** in a single `1024×1024` 8-bit RGB PNG for the [make.fun `news-image-20261123`](https://make.fun/bounty/news-image-20261123) competition.

## Coverage (7 Regions · 15 Stories · 13 Beats)

- **Hero Lead 1 (`Global · Markets`):** AI tech rout hits Asia; China hits 16-month low, Taiwan widens short-selling curbs, and South Korea readies an $8B stabilization fund.
- **Hero Lead 2 (`Middle East · Oil`):** Iran vows to use all available tools against the U.S. naval oil blockade as Washington warns blockade-running tankers.
- **3×3 Illustrated Gallery:**
  1. `Europe · Energy` — European natural gas jumps 6% to €93/MWh on a cold-snap forecast.
  2. `Africa · Oil` — Valve closure on Libya's Sharara pipeline cuts 350,000 bpd of output.
  3. `Americas · Economy` — U.S. Treasury Secretary Scott Bessent warns the Federal Reserve over hawkish rate risks.
  4. `Asia · Finance` — Singapore's MAS and China's PBOC expand bilateral RMB liquidity facilities.
  5. `South America · Space` — Ariane 6 Flight VA271 launch halted at Kourou spaceport in French Guiana.
  6. `Oceania · Economy` — Australian Treasurer Jim Chalmers forecasts slower growth (<2%) with no recession.
  7. `Africa · Health` — The 5th Africa Public Health Conference (CPHIA 2026) opens in Addis Ababa.
  8. `Europe · Media` — Independent report warns the BBC licence fee faces a steep decline.
  9. `South Asia · Diplomacy` — India and Nepal sign cross-border hydropower and connectivity agreements.
- **World Wire Strip (`2×2`):**
  - `Gulf · Oil` — Saudi Arabia and Japan expand joint crude storage by 16M barrels.
  - `Europe · Civic` — Cost-of-living protests sweep European cities.
  - `Sport · NZ` — New Zealand holds India to a Day 5 Wellington Test draw.
  - `Science · UK` — Bournemouth University study suggests Iron Age ruler Verica was likely female.

## Running

```bash
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

`main.ts` runs on Node 22 with zero external dependencies, validates every PNG chunk CRC-32 checksum, header dimensions (`<= 1024×1024`), 8-bit RGB encoding, and `< 1 MiB` byte cap, and writes `entry.png` deterministically to `$MAKEFUN_OUTPUT_DIR` (default `/output`).

## Re-rendering the Atlas

```bash
python3 tools/render_atlas.py
```

## License

MIT — see [LICENSE](LICENSE).
