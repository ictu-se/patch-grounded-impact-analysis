from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


COLORS = {
    "C0": "#4C78A8",
    "C1": "#59A14F",
    "C2": "#F28E2B",
    "C3": "#E15759",
    "C4": "#B07AA1",
    "C5": "#76B7B2",
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    condition = pd.read_csv(root / "analysis" / "outputs" / "se_surface_condition_summary.csv")
    risk = pd.read_csv(root / "analysis" / "outputs" / "se_surface_failure_risk.csv").set_index("condition")

    labels = condition["condition"].tolist()
    x = range(len(labels))

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.labelsize": 13,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "legend.fontsize": 10,
            "figure.dpi": 220,
        }
    )

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(11.2, 4.9),
        gridspec_kw={"width_ratios": [1.05, 1.0], "wspace": 0.32},
    )
    fig.patch.set_facecolor("white")
    fig.suptitle("Figure 1. Scaffold quality and risk summary", fontsize=15.5, y=1.03)

    bars = ax1.bar(
        x,
        condition["operational_quality"],
        color=[COLORS[label] for label in labels],
        edgecolor="#1f2933",
        linewidth=0.9,
        width=0.72,
        alpha=0.92,
    )
    ax1.plot(
        x,
        condition["repair_validity"],
        color="#111827",
        marker="o",
        markersize=6.4,
        linewidth=1.9,
        label="Repair validity",
        zorder=4,
    )
    ax1.plot(
        x,
        condition["instruction_alignment"],
        color="#8C564B",
        marker="s",
        markersize=6.2,
        linewidth=1.8,
        label="Instruction alignment",
        zorder=4,
    )
    for bar, value in zip(bars, condition["operational_quality"]):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.010,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=10.8,
            fontweight="bold",
            color="#111827",
        )
    ax1.set_title("Scaffold quality surface", pad=10)
    ax1.set_ylabel("Score")
    ax1.set_xticks(list(x), labels)
    ax1.set_ylim(0.43, 0.86)
    ax1.grid(False)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.legend(
        loc="upper center",
        bbox_to_anchor=(0.50, 0.985),
        ncol=2,
        frameon=False,
        borderpad=0.2,
        handlelength=2.1,
        columnspacing=1.0,
    )

    risk_cols = ["target_risk", "process_risk", "interface_risk", "stale_context_risk"]
    risk_labels = ["Target", "Process", "Interface", "Stale context"]
    image = ax2.imshow(risk.loc[labels, risk_cols], cmap="YlOrRd", vmin=0.20, vmax=0.50, aspect="auto")
    ax2.set_title("Risk profile by scaffold", pad=10)
    ax2.set_xticks(range(len(risk_labels)), risk_labels, rotation=24, ha="right")
    ax2.set_yticks(range(len(labels)), labels)
    ax2.tick_params(length=0)
    for row_index, condition_id in enumerate(labels):
        for col_index, col in enumerate(risk_cols):
            value = float(risk.loc[condition_id, col])
            ax2.text(
                col_index,
                row_index,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=10.8,
                color="#111827",
            )
    cbar = fig.colorbar(image, ax=ax2, fraction=0.046, pad=0.03)
    cbar.set_label("Risk score", rotation=270, labelpad=18)

    for path in [
        root / "paper_springer" / "figures" / "figure1_scaffold_quality_risk.png",
        root / "paper_springer" / "springer_submission_source" / "figures" / "figure1_scaffold_quality_risk.png",
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight", pad_inches=0.18)
        print(path)
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
