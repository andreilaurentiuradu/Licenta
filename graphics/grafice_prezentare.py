# -*- coding: utf-8 -*-
"""Generează 3 grafice pentru prezentarea de licență LawrAnalyzer."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

OUT = Path(__file__).parent
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 13,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

ACCENT = "#2563eb"   # albastru platformă
GRAY   = "#9ca3af"   # gri baseline
GREEN  = "#16a34a"

# ---------------------------------------------------------------- Grafic 1: sondaj
labels = [
    "Antrenori fără instrument\nautomat de predicție",
    "Antrenori dispuși să partajeze\ndatele (doar on-premise)",
    "Antrenori interesați de\npredicția riscului",
    "Sportivi dispuși să\nfolosească platforma",
    "Antrenori care NU colectează\ndate structurate",
]
vals = [100, 80, 70, 67, 20]
fig, ax = plt.subplots(figsize=(9, 4.6))
bars = ax.barh(labels[::-1], vals[::-1], color=ACCENT, height=0.6)
ax.set_xlim(0, 100)
ax.set_xlabel("% dintre respondenți")
ax.set_title("Rezultatele sondajului (28 respondenți: 10 antrenori, 18 sportivi)",
             fontweight="bold", pad=14)
for b, v in zip(bars, vals[::-1]):
    ax.text(v + 1.5, b.get_y() + b.get_height()/2, f"{v}%",
            va="center", fontweight="bold", color="#374151")
ax.xaxis.grid(True, alpha=0.25)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(OUT / "grafic_1_sondaj.png", bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- Grafic 2: acuratețe vs baseline
fig, ax = plt.subplots(figsize=(6.2, 4.6))
x = ["Baseline\n(clasa majoritară)", "Model\nLawrAnalyzer"]
y = [57.4, 73.1]
bars = ax.bar(x, y, color=[GRAY, ACCENT], width=0.55)
ax.set_ylim(0, 100)
ax.set_ylabel("Acuratețe (%)")
ax.set_title("Acuratețea modelului vs. baseline", fontweight="bold", pad=14)
for b, v in zip(bars, y):
    ax.text(b.get_x() + b.get_width()/2, v + 1.5, f"{v}%",
            ha="center", fontweight="bold")
# săgeată îmbunătățire
ax.annotate("+15.7 pp", xy=(1, 73.1), xytext=(1, 88),
            ha="center", fontweight="bold", color=GREEN,
            arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.8))
ax.yaxis.grid(True, alpha=0.25)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(OUT / "grafic_2_acuratete.png", bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- Grafic 3: acuratețe vs nr. cluburi
k      = [1, 2, 4, 8, 16]
acc    = [73.1, 71.8, 72.4, 72.9, 73.3]
fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.axhline(73.1, color=GRAY, ls="--", lw=1.6, label="Model centralizat (73.1%)")
ax.plot(range(len(k)), acc, "-o", color=ACCENT, lw=2.4, ms=8,
        label="Model federat (FedAvg)")
ax.set_xticks(range(len(k)))
ax.set_xticklabels([f"K={v}" for v in k])
ax.set_ylim(70.5, 74)
ax.set_xlabel("Număr de cluburi participante")
ax.set_ylabel("Acuratețe globală (%)")
ax.set_title("Convergența FL: acuratețea crește cu numărul de cluburi",
             fontweight="bold", pad=14)
for i, v in enumerate(acc):
    ax.text(i, v + 0.08, f"{v}%", ha="center", fontsize=11, fontweight="bold")
ax.legend(frameon=False, loc="lower right")
ax.yaxis.grid(True, alpha=0.25)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(OUT / "grafic_3_convergenta_fl.png", bbox_inches="tight")
plt.close(fig)

print("Generate:", *[p.name for p in OUT.glob("grafic_*.png")])
