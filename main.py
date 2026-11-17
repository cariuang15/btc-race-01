"""btc-race-01: a long-only momentum scalp bot for cbBTC (agent-fun/bars-replay/v1).

Strategy in plain words: sit in cash most of the day and only buy when the
price is riding above its slow 4-hour trend AND it has just ticked up over the
last 24 minutes. Sell as soon as the position is up 0.6%, several times what
one round trip costs, or cut it at -1.5% if the trend turns. Never chase:
after a sale, only buy back in at least 0.1% below the price the bot last
sold at, so it cannot sell a top and immediately buy it back higher. Rest 60
bars after every exit, and stop opening new trades if equity ever falls 8%
below its peak.

A round trip costs roughly a quarter of a percent, so one-minute noise is
untradable; the bot therefore trades rarely (a handful of times a day) and
only on multi-hour drift. Standard library only; no network, no clock, no
files, no randomness, so two runs on the same data produce identical orders.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars  # noqa: E402

SYMBOL = "CBBTC"

# --- parameters (chosen from the dev window; see dev/NOTES.md) ---
EMA_SLOW = 240          # slow trend: 4-hour exponential average of closes
ENTRY_N = 24            # momentum lookback, in bars (minutes)
ENTRY_MIN = 0.0005      # minimum 24-bar return to enter (+0.05%)
TAKE_PROFIT_BPS = 60    # exit when up 0.60% from the average cost
HARD_STOP_BPS = 150     # exit when down 1.50% from the average cost
SIZE_FRAC = 0.8         # spend 80% of the smaller of cash / equity per entry
COOLDOWN_BARS = 60      # rest this many bars after every exit
CHASE_BPS = 10          # re-enter only 0.10% below the last exit price
DRAWDOWN_GUARD_BPS = 800  # stop opening trades if equity falls 8% off its peak


class ScalpBot:
    """Keeps the bot's own bookkeeping; the SDK owns the wire and the account."""

    def __init__(self):
        self.closes = []          # every close seen, oldest first (price units)
        self.ema_slow = None      # slow trend average of closes
        self.entry_price = None   # average cost of the open position (price units)
        self.last_exit = None     # close at which the last sale was decided
        self.cool_until = -1      # first seq on which a new entry is allowed
        self.equity_peak = None   # highest equity seen, for the drawdown guard
        self.trades = 0           # orders sent (buys + sells)

    def on_batch(self, state, batch):
        close = state.close(SYMBOL)
        if close is None:
            return []
        # History first, decisions second: warm-up batches build the trend
        # too, even though no order may be decided on one.
        self.closes.append(close)
        if self.ema_slow is None:
            self.ema_slow = float(close)
        else:
            self.ema_slow += (2.0 / (EMA_SLOW + 1)) * (close - self.ema_slow)
        if self.equity_peak is None or state.equity > self.equity_peak:
            self.equity_peak = state.equity

        if state.warming_up:
            return []

        holding = state.positions.get(SYMBOL)
        if holding is not None and holding.qty > 0:
            if self.entry_price is None:
                # First batch the filled position shows up: recover its
                # average cost from the harness's own cost basis.
                self.entry_price = holding.cost * 10 ** 7 // holding.qty
            take_profit = close >= self.entry_price * (10_000 + TAKE_PROFIT_BPS) // 10_000
            hard_stop = close <= self.entry_price * (10_000 - HARD_STOP_BPS) // 10_000
            if take_profit or hard_stop:
                self.last_exit = close
                self.entry_price = None
                self.cool_until = state.seq + COOLDOWN_BARS
                self.trades += 1
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": 100}]
            return []

        # Flat: only a fresh entry, and only when everything agrees.
        self.entry_price = None
        if len(self.closes) < ENTRY_N + 1:
            return []
        if state.seq <= self.cool_until:
            return []
        if state.equity < self.equity_peak * (10_000 - DRAWDOWN_GUARD_BPS) // 10_000:
            return []  # drawdown guard: sit out until the window ends
        if close <= self.ema_slow:
            return []  # below the slow trend: no long
        if close / self.closes[-ENTRY_N - 1] - 1 <= ENTRY_MIN:
            return []  # no fresh 24-minute momentum
        if self.last_exit is not None:
            if close >= self.last_exit * (10_000 - CHASE_BPS) // 10_000:
                return []  # too close to where we last sold: do not chase
        notional = int(min(state.cash, state.equity) * SIZE_FRAC)
        notional = min(notional, state.weight_room(SYMBOL))
        if notional < 1_000_000:  # below the $1 minimum notional
            return []
        self.trades += 1
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": notional, "max_slippage_bps": 100}]

    def on_done(self, state, done):
        # Diagnostics go to stderr only; stdout carries replies alone.
        sys.stderr.write(
            "btc-race-01 done: batches=%d orders=%d final_equity_usdc=%.2f\n"
            % (done["seq"], self.trades, state.equity / 1_000_000)
        )


def main():
    bot = ScalpBot()
    makefun_bars.run(bot.on_batch, on_done=bot.on_done)


if __name__ == "__main__":
    main()
