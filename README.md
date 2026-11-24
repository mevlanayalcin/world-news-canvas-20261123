# World News Chronicle — Monday 23 November 2026

[![Competition](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123)
[![Rank](https://make.fun/badge/news-image-20261123/mevlanayalcin/world-news-canvas-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123)
[![Reward](https://make.fun/badge/news-image-20261123/mevlanayalcin/world-news-canvas-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123)

An archival one-page illustrated world news chronicle summing up **Monday 23 November 2026** in a single `1024×1024` 8-bit RGB PNG for the [make.fun `news-image-20261123`](https://make.fun/bounty/news-image-20261123) competition. Built with 100% original Python/Pillow vector illustrations, a chronological `THE DAY IN UTC` timeline, 13 illustrated story cards with factual sub-decks, a bundled Natural Earth 110m locator map, 23 sourced light-ivory wire dispatches, verification badges (`CONFIRMED` / `OFFICIAL` / `REPORTED` / `CLAIM`), and an explicit `DATE CHECK` exclusion box.

## Coverage (36 Verified Mon 23 Nov Stories · 7 Regions · 18 Beats)

- **Top 3 Flagship Illustrated Leads:**
  1. `Global · Markets` (`CONFIRMED` · `Reuters, AP`) — AI stock rout hits Asia; Kospi falls 3.3% & China hits 16-month lows; Seoul readies $8B fund as Taiwan widens curbs.
  2. `Middle East · Security` (`CONFIRMED` · `AFP, AA, Fox News`) — Iran vows "all tools" against U.S. Hormuz naval blockade warnings while Trump tells Fox strikes may resume after Jan 1.
  3. `Europe · Spain Law` (`OFFICIAL` · `Supreme Court, Reuters`) — Spain Supreme Court Criminal Chamber grants amnesty closing 2017 Catalan independence cases against Carles Puigdemont and two former ministers.
- **10 Illustrated Feature Cards (`#4–#13`):**
  4. `Cricket · NZ` (`OFFICIAL` · `ICC, ESPN`) — New Zealand bat out the final day in Wellington after India's 720/9d to hold a Test draw.
  5. `Europe Gas` (`CONFIRMED` · `FT, MUFG`) — European natural gas jumps 6% to €93/MWh on cold forecasts and Hormuz risks.
  6. `Belgium` (`CONFIRMED` · `AA, Al Jazeera`) — National anti-austerity strike halts Belgian ATC `07:00–21:00` local (`06–20 UTC`), grounding flights.
  7. `Germany` (`CONFIRMED` · `Police, DPA`) — Roughly 450 German schools and Danish sites receive coordinated emailed bomb-threat hoaxes deemed unfounded by police.
  8. `Libya Oil` (`CONFIRMED` · `NOC, AA, Reuters`) — Unauthorized Sharara pipeline valve closure cuts 350k bpd of Libyan crude output.
  9. `Africa Health` (`OFFICIAL` · `Africa CDC`) — Africa Public Health Summit (CPHIA 2026) opens in Addis Ababa with maternal guidelines and a 60% local-vaccine goal by 2040.
  10. `US Weather` (`CONFIRMED` · `CNN, SFO`) — Bay Area braces for Pacific storms and a forecast +2.8ft king-tide surge, prompting flood barriers at SFO before holiday travel.
  11. `Guiana Space` (`OFFICIAL` · `Arianespace, CNES`) — Ariane 6 Flight VA271 carrying 36 Amazon Leo satellites halted at Kourou over a ground-support fault.
  12. `Medicine` (`OFFICIAL` · `Novartis`) — Phase III ORION-4 heart trial readout shows Leqvio met its primary cardiovascular endpoint.
  13. `Oceania` (`OFFICIAL` · `USGS`) — USGS logs a strong M6.5 deep earthquake off Vanuatu with no tsunami warning.
- **23 Additional Sourced Wire Stories (`#14–#36`):**
  - US Fed warning (`AP`) · Canada Bombardier 97.8% strike vote (`AVI-GO`) · Colombia Chocó malaria +46% (`STC`) · Falklands deepwater oil warning (`Guardian`) · UK FTSE 100 Compass Group NY primary-listing plan (`LSE`) · UK Met Police probe of David Walliams (`ITV/CNN`) · UK BBC licence fee report (`Guardian`) · UK–EU youth-mobility tuition talks (`Guardian`) · Europe cost-of-living protests (`Al Jazeera`) · Japan Education Min. Seki resignation pressure (`Xinhua`) · Singapore–China MAS/PBOC RMB hub (`MAS`) · India–Nepal hydro & rail pacts (`Hindu`)
  - South Korea FM Lim & Qatar LNG talks (`K.Herald`) · Macquarie $1.2B APAC towers buyout (`Reuters`) · Cambridge study tracing adult blood cancer to early-life cell mutations (`Nature`) · Gaza 99% toxic-risk warning (`Oxfam`) · Saudi–Japan 16M bbl crude storage (`MUFG`) · Hormuz shipping attacks (`JPost`) · Durban Africa & Global South Water Summit opened by Deputy Pres. Mashatile (`SABC`) · German Pres. Steinmeier Africa tour in Abidjan (`DPA`) · South Africa & Zambia automated customs corridor (`SARS`) · Australia Treasurer Chalmers `<2%` GDP outlook (`Guardian`) · Brent crude steadying near $91.97/bbl amid Gulf risk (`Reuters`)
- **Date Boundary Discipline (`DATE CHECK`):** Explicitly excludes prior-day items from Sun 22 Nov or earlier (`COP31 climate talks`, `Dymer Kyiv strike`, `Manchester Co-op Live 12k evac`, `Vegas F1`, `Alcaraz ATP`, `Liverpool 4–0`, `S. Korea exit`, `BepiColombo`, `EU €7.9B (20 Nov)`, `Bank of Ghana`, `An-12`).

## Running

```bash
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

`main.ts` runs on Node 22 with zero external dependencies, validates every PNG chunk CRC-32 checksum, header dimensions (`<= 1024×1024`), 8-bit RGB encoding, and `< 1 MiB` byte cap, and writes `entry.png` deterministically to `$MAKEFUN_OUTPUT_DIR` (default `/output`).

## Re-rendering the Chronicle

```bash
python3 tools/render_atlas.py
```

Uses the bundled Natural Earth 110m geometry in `tools/ne_110m_land.geojson` with zero network or external temporary-file dependencies.

## License

MIT — see [LICENSE](LICENSE).
