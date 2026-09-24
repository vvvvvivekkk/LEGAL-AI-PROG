"""Paper figures. Every number here is copied from a logged run:
retrieval -> experiments/2026-09-23-ablations/retrieval/*/results.json
probes    -> experiments/2026-09-23-ablations/verification/results.json
screens   -> experiments/ui_reskin/after/*.png
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUT, exist_ok=True)

INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
S1 = "#2a78d6"  # categorical slot 1 (validated with slot 2)
S2 = "#eb6834"  # categorical slot 2

plt.rcParams.update({
    "font.family": "Liberation Serif",
    "font.size": 8,
    "axes.edgecolor": INK2,
    "axes.labelcolor": INK,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})

# ---------- Fig 4: retrieval F1 by chunking x retrieval setting ----------
ret_dir = os.path.join(REPO, "experiments/2026-09-23-ablations/retrieval")
settings = [("dense", True), ("dense", False), ("hybrid", True), ("hybrid", False)]
labels = ["Dense\n+ rerank", "Dense", "Hybrid\n+ rerank", "Hybrid"]


def f1(chunking, mode, rerank):
    name = f"{chunking}-{mode}-{'rerank' if rerank else 'norerank'}"
    with open(os.path.join(ret_dir, name, "results.json")) as fh:
        d = json.load(fh)
    agg = d.get("aggregate", d)
    return agg["f1"]


sac = [f1("sac", m, r) for m, r in settings]
fb = [f1("fallback", m, r) for m, r in settings]
print("SAC F1", sac, "fallback F1", fb)

fig, ax = plt.subplots(figsize=(3.4, 2.1))
x = range(len(settings))
w = 0.36
b1 = ax.bar([i - w / 2 for i in x], sac, w, color=S1, edgecolor="white", linewidth=1.5, label="SAC", zorder=3)
b2 = ax.bar([i + w / 2 for i in x], fb, w, color=S2, edgecolor="white", linewidth=1.5,
            hatch="////", label="Paragraph fallback", zorder=3)
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.008, f"{b.get_height():.3f}",
                ha="center", va="bottom", fontsize=6.5, color=INK2)
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylabel("F1 (k = 5)")
ax.set_ylim(0, 0.5)
ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
ax.legend(frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.14), fontsize=7)
fig.savefig(os.path.join(OUT, "fig6_retrieval_f1.png"))
plt.close(fig)

# ---------- Fig 5: known-bad claims that reach the user, per arm ----------
with open(os.path.join(REPO, "experiments/2026-09-23-ablations/verification/results.json")) as fh:
    ver = json.load(fh)
arms = ["full_chain", "minus_v1", "minus_v2", "minus_v3", "minus_v4", "minus_v5", "minus_v6"]
arm_labels = ["Full\nchain", "−V1", "−V2", "−V3", "−V4", "−V5", "−V6"]
probes = ver["probes"]
surfaced = []
for a in arms:
    total = 0
    for pname, pdata in probes.items():
        arm = pdata["arms"][a] if "arms" in pdata else pdata[a]
        total += arm["bad_claims_surfaced"]
    surfaced.append(total)
print("surfaced", dict(zip(arms, surfaced)))
n_bad = 0
for pname, pdata in probes.items():
    arm = pdata["arms"]["full_chain"] if "arms" in pdata else pdata["full_chain"]
    n_bad += arm["bad_claims_total"]
print("total bad claims across probes", n_bad)

fig, ax = plt.subplots(figsize=(3.4, 1.9))
bars = ax.bar(range(len(arms)), surfaced, 0.55, color=S1, linewidth=0, zorder=3)
for i, v in enumerate(surfaced):
    ax.text(i, v + 0.6, f"{v}", ha="center", va="bottom", fontsize=7, color=INK)
ax.set_xticks(range(len(arms)))
ax.set_xticklabels(arm_labels)
ax.set_ylabel(f"Bad claims shown (of {n_bad})")
ax.set_ylim(0, max(n_bad, max(surfaced)) * 1.18)
ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
fig.savefig(os.path.join(OUT, "fig7_probe_surfaced.png"))
plt.close(fig)


# ---------- diagrams ----------
def box(ax, x, y, w, h, text, fill="#f3f2ee", edge=INK2, bold=False, size=7.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.04",
                                facecolor=fill, edgecolor=edge, linewidth=0.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=INK,
            fontweight="bold" if bold else "normal", linespacing=1.15)


def arrow(ax, x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=INK2, linewidth=0.8, shrinkA=0, shrinkB=0))


# Fig 1: pipeline (vertical, one column)
steps = [
    "Document upload (PDF / TXT)\nextract, clean, SHA-256 de-duplication",
    "Chunking\nSAC if Act/Section structure found, else paragraphs",
    "Embedding + LanceDB index\ndense vectors and full-text index, one table",
    "Hybrid retrieval\nvector + keyword, RRF fusion, cross-encoder rerank",
    "Citation-forced generation\none claim per line, each ending in a chunk id",
    "Verification chain V1–V6\nper-claim checks -> VCS",
]
fig, ax = plt.subplots(figsize=(3.4, 4.9))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
h, gap, top = 0.082, 0.042, 0.975
ys = []
for i, s in enumerate(steps):
    y = top - h - i * (h + gap)
    ys.append(y)
    box(ax, 0.06, y, 0.88, h, s)
    if i:
        arrow(ax, 0.5, ys[i - 1], 0.5, y + h)
yg = ys[-1] - gap - h
arrow(ax, 0.5, ys[-1], 0.5, yg + h)
box(ax, 0.2, yg, 0.6, h, "VCS ≥ 0.60 ?", fill="#e3edfa", edge=S1, bold=True)
yo = yg - gap - h
arrow(ax, 0.35, yg, 0.27, yo + h)
arrow(ax, 0.65, yg, 0.73, yo + h)
box(ax, 0.03, yo, 0.43, h, "Answer + citations\n+ proof object", fill="#e6f4ee", edge="#1baf7a")
box(ax, 0.54, yo, 0.43, h, "Abstain\n(or labelled general-\nknowledge answer)", fill="#fdeee6", edge=S2, size=7)
ax.text(0.26, yg - gap / 2, "yes", fontsize=6.5, color=INK2, ha="right", va="center")
ax.text(0.74, yg - gap / 2, "no", fontsize=6.5, color=INK2, ha="left", va="center")
fig.savefig(os.path.join(OUT, "fig1_pipeline.png"))
plt.close(fig)

# Fig 2: verification chain
fig, ax = plt.subplots(figsize=(3.4, 2.5))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
det = [
    ("V1  Citation exists", "hard gate"),
    ("V2  Source entails claim (NLI)", "hard gate on CONTRADICTS"),
    ("V3  Atomic-fact fidelity", "graded, w = 0.35"),
    ("V4  Self-consistency", "graded, w = 0.25, optional"),
]
bh, bg = 0.15, 0.04
for i, (t, sub) in enumerate(det):
    y = 0.93 - bh - i * (bh + bg)
    box(ax, 0.02, y, 0.55, bh, f"{t}\n{sub}", size=6.8)
    arrow(ax, 0.57, y + bh / 2, 0.66, 0.5)
box(ax, 0.66, 0.36, 0.32, 0.28, "V5  VCS gate\nmean claim score\nvs. threshold", fill="#e3edfa", edge=S1, bold=True, size=6.8)
box(ax, 0.66, 0.03, 0.32, 0.2, "V6  Proof object\nverdicts + quoted spans", size=6.5)
arrow(ax, 0.82, 0.36, 0.82, 0.23)
ax.text(0.30, 0.955, "Detection (per claim)", ha="center", fontsize=7, color=INK2, style="italic")
ax.text(0.82, 0.68, "Decision", ha="center", fontsize=7, color=INK2, style="italic")
fig.savefig(os.path.join(OUT, "fig2_verification_chain.png"))
plt.close(fig)

# Figs 3-5: crops of the web interface, captured during real queries after the
# light theme was applied (experiments/ui_reskin/after/).
shots = os.path.join(REPO, "experiments/ui_reskin/after")
crops = [
    ("04-ask-verified.png", (456, 250, 1168, 690), "fig3_verified_answer.png"),
    ("05-ask-abstained.png", (456, 190, 1168, 492), "fig4_abstained_answer.png"),
    ("07-evaluation.png", (217, 289, 1150, 747), "fig5_embedding_space.png"),
]
crops.append(("../../2026-09-24-human-e2e/screens/ask-C2-proof.png", (496, 195, 1208, 905),
              "fig8_incomplete_answer.png"))
for src, box_, out in crops:
    Image.open(os.path.join(shots, src)).convert("RGB").crop(box_).save(os.path.join(OUT, out))
print("done:", sorted(os.listdir(OUT)))
