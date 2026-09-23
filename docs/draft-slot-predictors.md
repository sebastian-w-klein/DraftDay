# What predicts draft slot? Findings from 8,660 combine invitees

**Question.** College prospects have thin data. Players who have already gone through the draft (most now or formerly in the league) have a lot. Which prospect traits, measured *before* the draft, are statistically significant predictors of where a player gets picked? The answer should feed the prospect and player models in DraftDay.

**Short answer.** Four things matter consistently, roughly in this order:

1. **Age at draft.** Younger means earlier, at every position.
2. **Speed relative to size.** This is the 40 time, best expressed as weight-adjusted speed score.
3. **Size for the position.** This matters most in the trenches and at EDGE.
4. **College production.** This applies only to QB, RB, WR and TE, and it adds significant signal on top of everything else.

Vertical jump, short shuttle and bench press add almost nothing to *where* a player goes once the other traits are known. Public measurables and production together reach an out-of-sample Spearman ρ of about 0.3–0.5, so most of the variation in draft slot comes from scouting information. The mock-draft consensus already in DraftDay is still the main signal. These findings are best used as priors and as supporting features.

Every number below comes from `python -m backend.app.draft_slot.cli`. The full tables are in [`backend/artifacts/draft_slot/report.md`](../backend/artifacts/draft_slot/report.md).

## Data

| Source | What it gives | Coverage |
|---|---|---|
| nflverse `combine` | Height, weight, 40, bench, vertical, broad, 3-cone, shuttle, school, draft pick | Every combine invitee, 2000–2026 (8,660 after removing K/P/LS) |
| nflverse `draft_picks` | Pick and PFR age | Drafted players |
| nflverse `players` | Birth date, ESPN id | Players who reached the NFL |
| cfbfastR `team_info` | Conference and FBS/FCS status per season | 99.5% of invitees matched to a school |
| cfbfastR play-level `player_stats` | College passing, rushing, receiving and defensive production | 2014+ seasons, so 2015+ draft classes. 92–98% of skill players and DBs linked, 77–80% of DL, ~0% of OL (the feed has no OL stats) |

The population is **combine invitees**, drafted and undrafted (65% drafted). Keeping the undrafted players lets the analysis separate two questions: *whether* a prospect is drafted, and *where*.

## Method

Each position group (QB, RB, WR, TE, OT, IOL, EDGE, IDL, LB, CB, S) is modelled separately. Drill results are z-scored within position and oriented so that positive means better. The analysis uses three targets:

- **Slot (drafted):** −log(pick) among drafted players. The log spreads out early picks, where value changes fastest.
- **P(drafted):** a logit of drafted vs undrafted.
- **Draft capital:** −log(pick), with undrafted players set to pick 300.

Four lenses must broadly agree before a trait counts as a predictor:

1. **Univariate Spearman** correlation.
2. **Multivariate OLS/logit** with HC3 robust errors, controlling for all other traits and draft year.
3. **Nested F-tests** that drop one trait group at a time (partial R²).
4. **Out-of-sample leave-one-draft-year-out gradient boosting**, with grouped permutation importance tested across held-out years.

All p-values are Benjamini-Hochberg FDR-adjusted.

**Leakage guard.** Birth dates exist almost only for players who reached the NFL, so "age is missing" nearly means "went undrafted". Age is therefore used only for the drafted-only target, on complete cases. An earlier pass that ignored this made age look like a near-perfect predictor of being drafted. The tests pin this behavior.

## Findings

### 1. Age is the most consistent predictor of slot

Age is significant at q < 0.001 at all 11 positions. Its partial R² ranges from 0.04 (IOL) to 0.13 (QB), which makes it the largest single group at 9 of 11 positions. Pooled, one SD of age (about 0.9 years) moves −log(pick) by 0.26. Mean age falls steadily by round, from 22.9 in round 7 to 22.1 in round 1.

Part of this is reverse causality: the best prospects declare early. It is still a clean, pre-draft signal, and the current prospect model does not use it.

### 2. Speed, adjusted for size, is the dominant athletic trait

- The 40 is significant for slot at every position except QB, with partial R² from 0.03 (IOL, IDL) to 0.11 (EDGE).
- Out of sample, shuffling speed costs 0.11–0.31 held-out ρ. That makes it the most important group at 10 of 11 positions.
- On its own, weight barely correlates with slot (ρ ≈ 0–0.16). With the 40 in the model, weight becomes strongly positive, so teams pay for speed *at a given size*.
- Barnwell's speed score (weight × 200 / 40⁴) combines the two. Its univariate ρ with slot beats the raw 40 at all 11 positions (for example 0.39 vs 0.30 at EDGE and 0.38 vs 0.34 at OT).

### 3. Size matters most in the trenches and at EDGE

The size group is significant for slot at 9 of 11 positions. It is largest at EDGE (0.081), IDL (0.057), OT (0.046) and TE (0.044). QB height matters for *getting drafted* (logit +0.60, q < 0.001) but not for where.

### 4. The secondary drills are weak

- **Broad jump** is significant pooled (+0.10), for slot at CB and TE, and for draft capital at RB, OT, EDGE and CB. The **vertical** is never significant, at any position or target, once broad and the 40 are in the model.
- **3-cone** matters for QB, EDGE and IDL, and out of sample for IOL and OT.
- **Short shuttle** predicts being drafted (pooled logit +0.15) but not slot.
- **Bench press** has no significant effect on slot at any position except IDL (partial R² 0.013). QBs are excluded because they almost never bench.

### 5. School tier matters more for being drafted than for where

FBS and Power-conference flags are strongly significant for P(drafted) (pooled +0.68 and +0.31 log-odds) and draft capital. Their effect on slot among drafted players is small (partial R² ≤ 0.022).

### 6. Skipping drills signals top-prospect status

At QB, WR, TE, RB and EDGE, skipping drills is associated with *earlier* picks (partial R² 0.041–0.094). The likely reason is that consensus top prospects sit out.

**Caveat:** before 2017 the combine file has almost no missing 40 times (pro-day times appear to fill the gaps), so this signal is identified mainly from 2017–2026. Treat it as a proxy for scouting consensus, not a trait.

### 7. College production adds signal for QB, RB, WR and TE, not for defenders

The production group is tested on top of combine, age and school, using 2015+ classes:

| Pos | Partial R² (slot) | Out-of-sample Δρ | Metrics that carry it (univariate ρ with slot) |
|---|---|---|---|
| QB | **0.232*** | 0.158 (ns, n=121) | Final-year Y/A +0.32, TD rate +0.24, fewer FBS seasons |
| TE | **0.193*** | 0.150** | Rec Y/G +0.34, rec-yard share +0.28, Y/target +0.23 |
| RB | **0.121** | 0.268** | TD/G +0.36, rush Y/G +0.29, Y/C +0.25 |
| WR | **0.116*** | 0.208*** | Dominator +0.25, rec-yard share +0.25, Y/target +0.19, breakout age (younger) +0.18 |
| EDGE | 0.046 (ns) | 0.118 (q = 0.052) | Sacks/G +0.20 univariate, but absorbed by athletic traits |
| IDL, LB, CB, S | ≤ 0.044 (ns) | ns | S: INT/G +0.22 univariate only. CB ball production: nothing |

In these tables, `***` means q < 0.001 and `**` means q < 0.01.

Rates and team shares are used rather than raw totals because the play-level feed covers only about 70–85% of games. With production added, out-of-sample ρ is higher at QB (0.37 → 0.46), RB (0.43 → 0.52), WR (0.43 → 0.47), TE (0.36 → 0.39) and LB (0.40 → 0.44). These are different samples (2000+ vs 2015+ linked players), so read the gaps as indicative; the nested F-test is the like-for-like comparison.

### 8. The relationships are stable over time

Comparing 2000–2012 with 2013+, only one of 166 trait coefficients changed significantly: IDL 3-cone, which went from +0.42 to 0.00. The priors can be applied to current classes.

### 9. The ceiling is modest

Out-of-sample ρ with draft capital is 0.32–0.43 from combine and school alone, and up to 0.52 with production. Within drafted players, ρ is 0.19–0.49. Film grades, medicals and interviews explain the rest, and in DraftDay they are captured only through the mock-draft consensus.

## Using this in DraftDay

`backend/artifacts/draft_slot/position_priors.json` holds per-position linear models with their exact preprocessing. `backend.app.draft_slot.priors.score_prospects` applies them to any frame built with `features.add_features`. There are three variants:

| Variant | Target | Needs | Use |
|---|---|---|---|
| `athletic` | Draft capital | Combine and school | `ProspectFeature.athletic_score`, for any invitee |
| `slot` | −log(pick) \| drafted | Plus age | Expected pick (`prior_pick`), usable as a fallback `consensus_rank` for prospects with thin mock coverage |
| `production` | −log(pick) \| drafted | Plus college stats, 2015+ | `ProspectFeature.production_score` for QB, RB, WR and TE |

Pass `max_p_value=0.05` to keep only coefficients that survived significance.

Concrete recommendations for the existing models:

1. **Add `age_at_draft`** to prospect and player features. It is the strongest missing signal.
2. **Build `athletic_score` from position-specific weights:** speed score first, then size, broad jump and 3-cone. Drop the vertical and bench, which are noise for slot, except bench for IDL.
3. **Build `production_score` only for QB, RB, WR and TE,** using the metrics in the table above. Do not spend model capacity on defensive production.
4. **Treat these as priors, not replacements.** The consensus rank carries information these traits cannot. A reasonable next step is to blend `prior_pick` with `consensus_rank` and weight the prior more when mock coverage is sparse (Day 3 prospects).

## Limitations and next data to add

- **Population:** combine invitees only. Drafted non-invitees, about 10–15% of picks, are not included.
- **Pro days:** the source mixes pro-day 40s into pre-2017 data, and other drills are combine-only.
- **Missing context:** there is no injury history, medical flags, recruiting stars or PFF grades. There are no historical big boards either, which would let the analysis measure what traits add *beyond* the market.
- **Undrafted ages:** birth dates for undrafted invitees would lift the age restriction on the drafted/undrafted targets.
- **Offensive line:** OL production is not available from the feed.

## Reproducing

```bash
pip install -e ".[research]"
python -m backend.app.draft_slot.cli            # downloads ~150 MB on first run, ~3 min
python -m backend.app.draft_slot.cli --skip-oos # tables only (reuses last CV results)
pytest tests/test_draft_slot.py
```

Raw downloads and the joined table are cached under `data/draft_slot/`, which is gitignored. Data comes from nflverse (combine, draft picks, players) and sportsdataverse cfbfastR-data (college play-level stats, team info); attribute them in any public use.
