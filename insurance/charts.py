"""Insurance Analytics charts (PNG images made with matplotlib)."""
import io

import matplotlib
matplotlib.use("Agg")            # no window, just images
import matplotlib.pyplot as plt

from insurance.analytics import expected_pain, RECOVERED_PAIN, TARGET_CHECKINS_PER_WEEK

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"
RISK_COLORS = {"low": "#0ca30c", "medium": "#fab219", "high": "#d03b3b"}


def _figure(title, subtitle=""):
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=110)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    fig.suptitle(title, x=0.06, ha="left", fontsize=13, color=INK, fontweight="bold")
    if subtitle:
        ax.set_title(subtitle, loc="left", fontsize=9.5, color=INK2, pad=10)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", facecolor=SURFACE)
    plt.close(fig)
    return buf.getvalue()


def recovery_trend(weekly, start_pain, similar, title="Recovery trend") -> bytes:
    """User's weekly average pain vs the expected curve for similar patients (shaded: typical range)."""
    last_week = max([w["week"] for w in weekly] + [similar["p75_weeks"]])
    xs = [i / 4 for i in range(int(last_week * 4) + 5)]
    fast = [expected_pain(start_pain, similar["p25_weeks"], x) for x in xs]
    slow = [expected_pain(start_pain, similar["p75_weeks"], x) for x in xs]
    mid = [expected_pain(start_pain, similar["median_weeks"], x) for x in xs]

    fig, ax = _figure(title, f"Average pain per week since the claim, vs {similar['n_patients']} similar patients")
    ax.fill_between(xs, fast, slow, color=ORANGE, alpha=0.12, linewidth=0, label="Typical range (similar patients)")
    ax.plot(xs, mid, color=ORANGE, linewidth=2, linestyle="--", label="Expected (similar patients)")
    if weekly:
        wx = [w["week"] + 0.5 for w in weekly]
        wy = [w["avg_pain"] for w in weekly]
        ax.plot(wx, wy, color=BLUE, linewidth=2, marker="o", markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=2, label="This patient")
        ax.annotate(f"{wy[-1]:g}", (wx[-1], wy[-1]), textcoords="offset points", xytext=(8, 6),
                    color=INK, fontsize=9)
    ax.axhline(RECOVERED_PAIN, color=AXIS, linewidth=1)
    ax.text(xs[-1], RECOVERED_PAIN + 0.15, "recovered", color=MUTED, fontsize=8, ha="right", va="bottom")
    ax.set_ylim(0, 10)
    ax.set_xlim(0, xs[-1])
    ax.set_xlabel("Weeks since claim", color=MUTED, fontsize=9)
    ax.set_ylabel("Pain (0-10)", color=MUTED, fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK2, loc="upper right")
    return _png(fig)


def utilization(checkins_per_week, title="PT utilization") -> bytes:
    """Check-ins per week, with the weekly target."""
    fig, ax = _figure(title, f"Check-ins per week since the claim (target: {TARGET_CHECKINS_PER_WEEK})")
    weeks = list(range(len(checkins_per_week)))
    ax.bar(weeks, checkins_per_week, color=BLUE, width=0.6, edgecolor=SURFACE, linewidth=2)
    ax.axhline(TARGET_CHECKINS_PER_WEEK, color=INK2, linewidth=1, linestyle="--")
    ax.text(len(weeks) - 0.6, TARGET_CHECKINS_PER_WEEK + 0.1, "target", color=INK2, fontsize=8, ha="right")
    for x, v in zip(weeks, checkins_per_week):
        ax.text(x, v + 0.08, str(v), ha="center", va="bottom", color=INK, fontsize=9)
    ax.set_xticks(weeks, [f"Week {w + 1}" for w in weeks])
    ax.set_ylim(0, max(checkins_per_week + [TARGET_CHECKINS_PER_WEEK]) + 1.5)
    ax.yaxis.get_major_locator().set_params(integer=True)
    return _png(fig)


def risk_distribution(counts: dict, title="Claims by risk level") -> bytes:
    """How many analyzed claims are low, medium and high risk."""
    levels = ["low", "medium", "high"]
    values = [counts.get(l, 0) for l in levels]
    fig, ax = _figure(title, "Latest analysis of each claim")
    ax.bar(levels, values, color=[RISK_COLORS[l] for l in levels], width=0.55, edgecolor=SURFACE, linewidth=2)
    for x, v in enumerate(values):
        ax.text(x, v + 0.05, str(v), ha="center", va="bottom", color=INK, fontsize=10)
    ax.set_xticks(range(3), ["Low risk", "Medium risk", "High risk"])
    ax.set_ylim(0, max(values + [1]) * 1.25)
    ax.yaxis.get_major_locator().set_params(integer=True)
    return _png(fig)
