# World News Atlas — Monday 23 November 2026

[![Competition](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123)
[![Rank](https://make.fun/badge/news-image-20261123/mevlanayalcin/world-news-canvas-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123)
[![Reward](https://make.fun/badge/news-image-20261123/mevlanayalcin/world-news-canvas-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123)

An illustrated, strictly sourced one-page world news atlas summing up **Monday 23 November 2026** in a single `1024×1024` 8-bit RGB PNG for the [make.fun `news-image-20261123`](https://make.fun/bounty/news-image-20261123) competition. Every text element enforces `MIN_FONT_PX = 15.0` for thumbnail legibility at `300px`, every story carries an inline named outlet source, and an explicit bottom `DATE CHECK · 23 NOV UTC` bar documents excluded 21–22 Nov prior-day items.

## Coverage (7 Regions · 25 Sourced Stories · 17 Beats)

- **Hero Lead 1 (`Global · Markets` · `REUTERS`):** AI rout hits Asia; Korea & Taiwan act (`Kospi -3.3%; Seoul readies $8B fund`).
- **Hero Lead 2 (`Middle East · Oil` · `AFP`):** Iran vows 'all tools' on U.S. oil blockade (`Tehran answers U.S. fire warning to ships`).
- **3×3 Panoramic Museum Gallery (9 Illustrated Sourced Stories):**
  1. `Europe · Ukraine` (`EU`) — EU disburses €7.9B under the Ukraine Facility.
  2. `Europe · Energy` (`FT`) — European natural gas surges 6% to €93/MWh.
  3. `Africa · Oil` (`AA`) — Libya's NOC says Sharara valve shut cuts 350k bpd.
  4. `Americas · Economy` (`AP`) — U.S. Treasury Sec. Scott Bessent warns hawkish Fed risks growth.
  5. `Asia · Finance` (`MAS`) — Singapore and China expand offshore RMB hub at 22nd JCBC.
  6. `South America · Space` (`ARIANE`) — Ariane 6 launch halted in French Guiana.
  7. `Africa · Health` (`CDC`) — Africa Public Health Summit (CPHIA 2026) opens in Addis Ababa.
  8. `Global · Medicine` (`NOVARTIS`) — Novartis says Phase III ORION-4 heart trial met endpoint.
  9. `South Asia · Trade` (`HINDU`) — India and Nepal sign cross-border rail and hydropower pacts.
- **2×7 Attributed Dark-Navy Global Wire (14 Single-Line Sourced Dispatches):**
  - Belgium airspace strike `07–21 UTC` (`AVI-GO`) · UK report warns BBC licence fee `<50%` of homes (`GUARDIAN`) · EU living-cost protests hit capitals (`ALJAZEERA`) · Canada Bombardier union votes `97.8%` strike (`AVI-GO`) · Colombia NGO warns Chocó malaria `+46%` (`STC`) · Australia Treasurer Chalmers sees `<2%` growth (`GUARDIAN`) · Vanuatu M6.5 deep quake (`USGS`)
  - Gaza Oxfam warns `99%` faces toxic risk (`OXFAM`) · Gulf Saudi & Japan add `16M bbl` oil storage (`MUFG`) · Hormuz monitors cite Gulf ship attacks (`JPOST`) · Ivory Coast German Pres. Steinmeier opens Africa tour (`DPA`) · AfCFTA South Africa & Zambia link automated trade customs (`SARS`) · Seoul new foreign minister & Qatar LNG talks (`K.HERALD`) · Sport New Zealand holds India to Wellington Test draw (`ICC`)
- **Date Boundary Discipline (`DATE CHECK · 23 NOV UTC`):** Explicitly excludes prior-day 21–22 Nov carryover items (`COP31 talks; Vegas F1; Premier League; ATP Finals; BepiColombo`).

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
