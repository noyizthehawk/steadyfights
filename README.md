# 🥊 UFC Fighter Analytics
> Data-driven analysis of UFC fighter performance and fight outcomes.

---

## About

This project uses statistical analysis and machine learning to investigate what factors influence success in professional MMA. It combines exploratory data analysis, hypothesis testing, and predictive modeling to uncover patterns in fighter performance.

## Project Structure

| Part | Focus | Status |
|------|-------|--------|
| **Part 1** | Statistical analysis of common MMA beliefs |
| **Part 2** | Career trajectory and fighter evolution modeling |
| **Part 3** | Predictive modeling and matchup analysis | 
| **Part 4** | Fighter archetype clustering and profiling |

---

## Key Findings

### 🔬 Part 2 — Fighter Prime Window Analysis

![Prime Window Analysis](prime_window_analysis.png)

**What the data shows:**

The left chart plots the distribution of peak performance timing across fighters. The distribution is right-skewed with the mean and median both sitting at fight **#5**, meaning most fighters hit their statistical peak very early in their careers — often within their first handful of UFC bouts. A large spike at fights 1–2 followed by a secondary peak around fights 5–6 suggests two distinct groups: those who enter the UFC already at their ceiling, and those who develop rapidly over a short window.

The right chart tells an equally striking story. Win rate declines monotonically across career stages — from **60.6%** in the Early phase (fights 1–5), down to **52.0%** in Mid (6–10), **50.2%** in Prime (11–15), and **44.2%** in the Late stage (16+). Contrary to the common narrative that fighters peak in their "experienced prime," the data suggests that survivorship bias and competition level adjustments make early career performance the strongest predictor. By the time fighters reach their late career, they are fighting against a tougher pool *and* may be in physical decline.

> **Takeaway:** UFC fighters peak earlier than conventional wisdom suggests. Career longevity does not equal sustained performance — the prime window is short and front-loaded.

---

### 📊 Part 1 — Busting MMA Myths with Data

#### Myth #1: Does Reach Advantage Predict Wins?

![Myth 1 - Reach Advantage](myth1_reach_advantage.png)

**Verdict: Partially TRUE — but only at the extremes.**

Across most reach difference brackets, the red fighter's win rate hovers between **51–62%**, only modestly above the 50% baseline. The effect is real but weak for differences under 15 cm. However, when the reach advantage exceeds **+20 cm**, win rate jumps sharply to **~73%** — a meaningful signal. At the negative extreme (reach disadvantage of 20+ cm), the win rate barely clears 50%.

The relationship is **non-linear**: small reach differences barely matter, but extreme reach mismatches are a significant factor. Reach alone is not predictive at typical margins, but matchmakers and bettors should pay attention when the gap is large.

---

#### Myth #2: Does Youth Beat Experience?

![Myth 2 - Youth vs Experience](myth2_youth_vs_experience.png)

**Verdict: FALSE — older fighters hold a consistent edge.**

This chart measures the red fighter's win rate as a function of the age difference (red minus blue). When the red fighter is **younger** (negative values on the x-axis), win rates drop toward 51–58%. When the red fighter is **older**, win rates climb steadily — reaching **~66%** when they're 0–1 years older, **~68%** when 2–3 years older, and peaking at **~76%** when 5–10 years older.

This seems counterintuitive, but it likely reflects that older fighters in the UFC at a similar record are still competing because they are elite — they've survived the selection pressure. Age in MMA appears to be a proxy for experience, durability, and mental composure rather than physical decline (within the competitive range of most UFC matchups).

> **Takeaway:** Don't bet against the older fighter. In competitive MMA, age and experience correlate positively with winning, up to a point.

---

#### Myth #3: Wrestlers Beat Strikers?

![Myth 3 - Wrestlers vs Strikers](myth3_wrestlers_vs_strikers.png)

**Verdict: TRUE — wrestling confers a significant style advantage.**

In cross-style matchups (wrestler vs. striker), wrestlers win approximately **57.6%** of the time while strikers win just **~42.3%**. That's a ~15 percentage point gap against the 50% baseline — a large and practically meaningful edge.

This aligns with the long-standing MMA principle that wrestling is the most effective base style because it allows the wrestler to **dictate where the fight takes place**. A striker cannot implement their gameplan on their back. The data confirms what coaches have argued for decades: wrestling is a structural advantage in MMA, not just a stylistic preference.

---

#### Myth #4: Does Size Impact Vary by Division?

![Myth 4 - Size by Division](myth4_size_by_division.png)

**Verdict: YES — and the pattern is striking.**

This chart shows the correlation between height/reach and winning, broken down by weight class. Several patterns emerge:

- **Flyweight** is the outlier: both height and reach show *negative* correlations with winning (~-0.11 and ~-0.07), suggesting that in the smallest division, being compact and stocky may be advantageous.
- **Light Heavyweight and Heavyweight** show the strongest positive correlations for reach (~0.15), confirming that size matters most when the weight cap is highest and body types are most variable.
- **Women's Strawweight** also shows a notable *negative* reach correlation (~-0.13), echoing the Flyweight pattern — smaller divisions may reward compact frames.
- **Women's Bantamweight** bucks this trend with positive correlations for both height (~0.14) and reach (~0.12), suggesting body type effects are not uniform across women's divisions.

> **Takeaway:** Size isn't universally good or bad — its impact is highly division-dependent. In lighter divisions, being compact can be an advantage. In heavier divisions, longer reach is a genuine edge.

---

## Goals

- [x] Test hypotheses about fight outcomes with data
- [x] Identify patterns in fighter career development
- [ ] Build interpretable models for fight prediction
- [ ] Extract actionable insights from historical fight data

---

## Tech Stack

- **Python** — pandas, numpy, scikit-learn, matplotlib, seaborn
- **Statistical Analysis** — hypothesis testing, correlation analysis, distribution modeling
- **Machine Learning** — classification models, clustering (coming in Parts 3–4)

---

*Educational research project — not intended for gambling or commercial use.*
