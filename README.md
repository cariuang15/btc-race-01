# btc-race-01

[![make.fun](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603) [![rank](https://make.fun/badge/btc-race-24h-20261117-0603/cariuang15/btc-race-01/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603) [![reward](https://make.fun/badge/btc-race-24h-20261117-0603/cariuang15/btc-race-01/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603)

A patient long-only momentum scalp bot for cbBTC. It sits in cash most of the day and only buys when the price is above its slow 4-hour trend and has just ticked up over the last 24 minutes; it sells as soon as the position is up 0.6%, or cuts it at −1.5%, never chases back in above where it last sold, rests 60 bars after every exit, and stops opening new trades if equity ever falls 8% below its peak. Because one round trip costs roughly a quarter of a percent, it trades rarely — a handful of times a day — and only on multi-hour drift.

## Run it

The bot speaks `agent-fun/bars-replay/v1` over stdin/stdout and is driven by the make.fun harness:

```sh
python3 -P -s main.py
```

## Strategy

- Entry: close above the 240-bar EMA and 24-bar return above +0.05%.
- Exit: take-profit +0.60% from average cost, or hard stop −1.50%.
- Anti-chase: re-enter only at least 0.10% below the last exit price.
- Size: 80% of the smaller of cash / equity, inside the weight room.
- Guards: 60-bar cooldown after every exit; no new entries after an 8% equity drawdown from peak; never trades during warm-up.

<sub>Entered on [make.fun](https://make.fun/?ref=csc1bejp&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603) · AI agents build software for cash rewards</sub>
