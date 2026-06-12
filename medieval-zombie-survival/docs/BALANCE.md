# Balance notes

Balance is tuned with a headless bot harness (`scripts/debug/Simulator.gd`)
that plays the real game through input actions at accelerated time:

```bash
MZS_SIM=gather MZS_SIM_DAYS=4 MZS_SIM_SPEED=16 \
  godot --headless --path . --audio-driver Dummy
```

Modes: `idle` (stays in town, self-defense only), `gather` (works the
chop/forage/eat/warm-up loop), `hunt` (seeks fights). CSV telemetry prints
every 2 in-game hours: hp, hunger, stamina, level, kills, zombie population,
wood/food stocks, bleeding/cold flags, weapon condition.

## Findings that drove the current numbers

Round 1 (pre-balance): all three bots died by day 3 — every death was
starvation, not zombies. Food was the bottleneck; combat, durability, XP and
the population curve were already healthy.

Fixes: hunger drain 0.2 -> 0.16/s (cold multiplier 1.4 -> 1.3), starvation
damage 1.2 -> 0.5/s, bleeding 0.35/s, berries 20 -> 24 food, mushrooms
12 -> 18, raw fish 12 -> 16, bushes can drop a second berry and regrow in
65s, bandages craftable from 2 fiber (no zombie cloth needed), more food in
ground scatter.

Round 2: night pressure killed the aggressive bot on day 1. Night population
multiplier 1.4 -> 1.25, night runner share 0.25 -> 0.2, night sight 170 ->
160, hordes start night 4 (then every 3rd night) at 6 + 2/day, cap 30.

## Verified outcome (4-day sims, Normal settings)

| Mode   | Result                                                        |
|--------|---------------------------------------------------------------|
| idle   | Survives to the night-4 horde, then dies hungry — by design   |
| gather | Survives indefinitely: food-positive, level 2, sword at 72%   |
| hunt   | Healthy through day 4, dies to the horde with empty reserves  |

The target shape: doing nothing fails at the first horde; working the
survival loop sustains; aggression is viable but unforgiving at the margins.
