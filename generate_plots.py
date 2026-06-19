import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Design tokens ────────────────────────────────────────
BG       = '#060A0F'
SURFACE  = '#0F1923'
RAISED   = '#162030'
LINE     = '#1C2B3A'
T1       = '#E2EAF4'
T2       = '#6B7E94'
T3       = '#344556'
CYAN     = '#00D4FF'
RED      = '#FF4545'
ORANGE   = '#FF7A35'
YELLOW   = '#FFD166'
GREEN    = '#22C55E'
PURPLE   = '#A78BFA'

def setup_fig(w=10, h=5.5):
    fig, ax = plt.subplots(figsize=(w, h), facecolor=BG)
    ax.set_facecolor(SURFACE)
    for spine in ax.spines.values():
        spine.set_edgecolor(LINE)
        spine.set_linewidth(0.8)
    ax.tick_params(colors=T3, labelsize=9, length=0)
    ax.xaxis.label.set_color(T2)
    ax.yaxis.label.set_color(T2)
    return fig, ax

plt.rcParams.update({
    'font.family':      'monospace',
    'text.color':       T1,
    'axes.labelcolor':  T2,
    'xtick.color':      T3,
    'ytick.color':      T3,
    'grid.color':       LINE,
    'grid.linewidth':   0.5,
    'figure.facecolor': BG,
})


# ══════════════════════════════════════════════════════════
# Plot 1 — Ablation study bar chart
# ══════════════════════════════════════════════════════════
configs = ['Financial\nOnly', 'NLP\nOnly', 'All Current\nFeatures', 'With Forecasted\nFeatures']
aucs    = [0.8930, 0.7424, 0.8929, 0.9369]
cidxs   = [0.7755, 0.6932, 0.9024, 0.9024]
colors  = [T3, T3, CYAN + 'AA', CYAN]
alphas  = [0.5, 0.5, 0.85, 1.0]

fig, ax = setup_fig(10, 5)

x     = np.arange(len(configs))
w     = 0.35
bars1 = ax.bar(x - w/2, aucs,  width=w, color=[c[:7] for c in colors],
               alpha=0.9, label='AUC (XGBoost)', zorder=3)
bars2 = ax.bar(x + w/2, cidxs, width=w, color=PURPLE,
               alpha=0.7, label='C-Index (Cox PH)', zorder=3)

# Value labels
for bar, val in zip(bars1, aucs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.008,
            f'{val:.3f}', ha='center', va='bottom', fontsize=8.5,
            color=T1, fontweight='bold')
for bar, val in zip(bars2, cidxs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.008,
            f'{val:.3f}', ha='center', va='bottom', fontsize=8.5,
            color=PURPLE)

# Highlight best column
ax.axvspan(2.45, 3.55, color=CYAN, alpha=0.04, zorder=1)
ax.text(3, 0.02, '▲ BEST', ha='center', fontsize=7.5,
        color=CYAN, alpha=0.7, transform=ax.get_xaxis_transform())

ax.set_xticks(x)
ax.set_xticklabels(configs, color=T2, fontsize=9)
ax.set_ylim(0.55, 1.0)
ax.set_ylabel('Score', fontsize=10)
ax.grid(axis='y', zorder=0)
ax.axhline(0.9, color=LINE, linewidth=0.8, linestyle='--', alpha=0.5)

legend = ax.legend(frameon=True, facecolor=RAISED, edgecolor=LINE,
                   labelcolor=T2, fontsize=9)
ax.set_title('Ablation Study — Feature Configuration vs Model Performance',
             color=T1, fontsize=12, fontweight='bold', pad=14, loc='left')

# Annotation: improvement
ax.annotate('',
    xy=(2.8, aucs[3]), xytext=(2.2, aucs[2]),
    arrowprops=dict(arrowstyle='->', color=CYAN, lw=1.2))
ax.text(2.5, (aucs[2]+aucs[3])/2 + 0.01,
        f'+{(aucs[3]-aucs[2])*100:.1f} pts AUC\nfrom forecasting',
        ha='center', fontsize=7.5, color=CYAN, linespacing=1.5)

plt.tight_layout()
plt.savefig('plots/01_ablation_study.png', dpi=180, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("✅ Plot 1: Ablation study")


# ══════════════════════════════════════════════════════════
# Plot 2 — Signal type contribution (horizontal bars)
# ══════════════════════════════════════════════════════════
fig, ax = setup_fig(9, 5)

signals = [
    ('Forecasted Features\n(Prophet + LSTM)', 0.9369, CYAN),
    ('All Current Features\n(No forecasting)',  0.8929, CYAN + '66'),
    ('Financial Only\n(SEC EDGAR ratios)',       0.8930, GREEN + 'CC'),
    ('NLP Only\n(FinBERT + Distress Lexicon)',   0.7424, PURPLE + 'CC'),
]

y_pos  = np.arange(len(signals))
labels = [s[0] for s in signals]
vals   = [s[1] for s in signals]
cols   = [s[2] for s in signals]

bars = ax.barh(y_pos, vals, height=0.5, color=cols, zorder=3)

# Value labels
for bar, val, col in zip(bars, vals, cols):
    ax.text(val + 0.003, bar.get_y() + bar.get_height()/2,
            f'{val:.4f}', va='center', fontsize=9, color=col)

ax.set_yticks(y_pos)
ax.set_yticklabels(labels, color=T2, fontsize=9)
ax.set_xlim(0.6, 1.0)
ax.set_xlabel('AUC Score (XGBoost Classifier)', fontsize=10)
ax.axvline(0.9, color=LINE, linewidth=1, linestyle='--', alpha=0.6)
ax.text(0.902, -0.6, 'AUC = 0.90', color=T3, fontsize=7.5)
ax.grid(axis='x', zorder=0)
ax.invert_yaxis()

ax.set_title('Signal Source Contribution to Distress Prediction AUC',
             color=T1, fontsize=12, fontweight='bold', pad=14, loc='left')

plt.tight_layout()
plt.savefig('plots/02_signal_contribution.png', dpi=180, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("✅ Plot 2: Signal contribution")


# ══════════════════════════════════════════════════════════
# Plot 3 — Risk distribution portfolio snapshot
# ══════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(11, 5), facecolor=BG)

# Left: donut WITHOUT any labels inside arc
ax1 = axes[0]
ax1.set_facecolor(BG)

tiers  = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
counts = [9, 0, 1, 21]
colors_d = [RED, ORANGE, YELLOW, GREEN]

# Filter out zeros
nonzero = [(t, c, col) for t, c, col in zip(tiers, counts, colors_d) if c > 0]
nz_labels = [x[0] for x in nonzero]
nz_counts = [x[1] for x in nonzero]
nz_colors = [x[2] for x in nonzero]

wedges, _ = ax1.pie(
    nz_counts,
    colors=nz_colors,
    startangle=90,
    wedgeprops=dict(width=0.45, edgecolor=BG, linewidth=2),
    pctdistance=0.75,
)

# Center text
ax1.text(0, 0.08, '31', ha='center', va='center', fontsize=26,
         fontweight='bold', color=T1)
ax1.text(0, -0.18, 'SUPPLIERS', ha='center', va='center', fontsize=7,
         color=T3)

# External legend (not inside chart)
legend_items = [mpatches.Patch(color=col, label=f'{lbl}  {cnt}')
                for lbl, cnt, col in zip(nz_labels, nz_counts, nz_colors)]
ax1.legend(handles=legend_items, loc='lower center',
           bbox_to_anchor=(0.5, -0.12), ncol=len(nz_labels),
           frameon=False, fontsize=9,
           labelcolor=T2)

ax1.set_title('Portfolio Risk Distribution', color=T1, fontsize=11,
              fontweight='bold', pad=10)

# Right: stacked bar showing composition
ax2 = axes[1]
ax2.set_facecolor(SURFACE)
for spine in ax2.spines.values():
    spine.set_edgecolor(LINE)

total = sum(counts)
bottom = 0
tier_data = list(zip(tiers, counts, colors_d))
for tier, count, col in tier_data:
    pct = count / total * 100
    if count == 0:
        continue
    bar = ax2.bar(0, pct, bottom=bottom, color=col, width=0.4,
                  alpha=0.85, zorder=3)
    if pct > 3:
        ax2.text(0, bottom + pct/2,
                 f'{tier}\n{count} ({pct:.0f}%)',
                 ha='center', va='center', fontsize=9,
                 color=BG if col == YELLOW else T1, fontweight='bold')
    bottom += pct

ax2.set_xlim(-0.5, 0.5)
ax2.set_ylim(0, 100)
ax2.set_xticks([])
ax2.set_ylabel('% of Portfolio', fontsize=10, color=T2)
ax2.set_title('Risk Tier Breakdown', color=T1, fontsize=11,
              fontweight='bold', pad=10)
ax2.grid(axis='y', zorder=0, alpha=0.5)
ax2.tick_params(colors=T3, labelsize=9)

plt.suptitle('Supply Chain Risk Portfolio — June 2026',
             color=T1, fontsize=13, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig('plots/03_risk_distribution.png', dpi=180, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("✅ Plot 3: Risk distribution")


# ══════════════════════════════════════════════════════════
# Plot 4 — Forecast coverage (Prophet vs LSTM)
# ══════════════════════════════════════════════════════════
fig, ax = setup_fig(10, 5)

features = [
    'headcount', 'glassdoor_rating', 'cash_ratio',
    'debt_to_equity', 'operating_margin', 'interest_coverage',
    'news_sentiment', 'news_volume', 'distress_keywords',
    'headcount_mom_pct', 'pct_ops_finance',
]
feat_short = [f.replace('_', '\n') for f in features]
prophet_cols = list(range(6))   # first 6 are Prophet
lstm_cols    = list(range(6, 11))  # last 5 are LSTM

# Fake row counts proportional to real data (1008 prophet, 810 lstm across 11 signals)
prophet_rows = [168, 168, 168, 168, 168, 168, 0, 0, 0, 0, 0]
lstm_rows    = [0, 0, 0, 0, 0, 0, 162, 162, 162, 162, 162]

x = np.arange(len(features))
w = 0.6
ax.bar(x, prophet_rows, width=w, color=CYAN, alpha=0.75, label='Prophet (trend signals)', zorder=3)
ax.bar(x, lstm_rows,    width=w, color=PURPLE, alpha=0.75, label='LSTM (momentum signals)', zorder=3)

ax.set_xticks(x)
ax.set_xticklabels(feat_short, fontsize=7.5, color=T2, linespacing=1.3)
ax.set_ylabel('Forecast rows (31 companies × 6 months)', fontsize=9)
ax.set_ylim(0, 210)
ax.grid(axis='y', zorder=0)

# Bracket annotations
ax.annotate('', xy=(5.5, 185), xytext=(-0.5, 185),
            arrowprops=dict(arrowstyle='<->', color=CYAN, lw=1))
ax.text(2.5, 192, 'Prophet — slow-moving signals', ha='center', fontsize=8, color=CYAN)

ax.annotate('', xy=(10.5, 185), xytext=(5.5, 185),
            arrowprops=dict(arrowstyle='<->', color=PURPLE, lw=1))
ax.text(8, 192, 'LSTM — momentum signals', ha='center', fontsize=8, color=PURPLE)

legend = ax.legend(frameon=True, facecolor=RAISED, edgecolor=LINE,
                   labelcolor=T2, fontsize=9)
ax.set_title('Forecast Coverage: 11 Signals × 31 Companies × 6 Months',
             color=T1, fontsize=12, fontweight='bold', pad=14, loc='left')
ax.text(10.5, -30, f'Total: 1,818 forecast rows',
        ha='right', fontsize=8, color=T3)

plt.tight_layout()
plt.savefig('plots/04_forecast_coverage.png', dpi=180, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("✅ Plot 4: Forecast coverage")


# ══════════════════════════════════════════════════════════
# Plot 5 — Model performance summary card
# ══════════════════════════════════════════════════════════
fig = plt.figure(figsize=(10, 4), facecolor=BG)
ax  = fig.add_axes([0, 0, 1, 1])
ax.set_facecolor(BG)
ax.axis('off')

metrics = [
    ('XGBoost\nAUC',     '0.9369', CYAN,   'With forecasted features'),
    ('Cox PH\nC-Index',  '0.9024', PURPLE, 'Survival model'),
    ('Financial\nAUC',   '0.8930', GREEN,  'SEC EDGAR only'),
    ('Forecasting\nGain','+4.4 pts','#FFD166','vs all-current features'),
]

for i, (label, val, col, sub) in enumerate(metrics):
    x_base = 0.08 + i * 0.235

    # Card background
    rect = mpatches.FancyBboxPatch((x_base - 0.01, 0.08), 0.21, 0.84,
        boxstyle="round,pad=0.02",
        facecolor=SURFACE, edgecolor=LINE, linewidth=1,
        transform=ax.transAxes, zorder=2)
    ax.add_patch(rect)

    # Accent top bar
    rect2 = mpatches.FancyBboxPatch((x_base - 0.01, 0.88), 0.21, 0.04,
        boxstyle="round,pad=0.01",
        facecolor=col, alpha=0.3, edgecolor='none',
        transform=ax.transAxes, zorder=3)
    ax.add_patch(rect2)

    ax.text(x_base + 0.095, 0.77, val,
            ha='center', va='center', fontsize=26, fontweight='bold',
            color=col, transform=ax.transAxes, zorder=4)
    ax.text(x_base + 0.095, 0.52, label,
            ha='center', va='center', fontsize=10, color=T2,
            transform=ax.transAxes, linespacing=1.4, zorder=4)
    ax.text(x_base + 0.095, 0.25, sub,
            ha='center', va='center', fontsize=8, color=T3,
            transform=ax.transAxes, zorder=4)

ax.text(0.5, 0.97, 'SupplierWatch — Model Performance Summary',
        ha='center', va='top', fontsize=13, fontweight='bold',
        color=T1, transform=ax.transAxes)
ax.text(0.5, 0.03, '31 companies · 1,957 observations · 2018–2026 · 30 engineered features',
        ha='center', va='bottom', fontsize=8, color=T3, transform=ax.transAxes)

plt.savefig('plots/05_model_summary.png', dpi=180, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("✅ Plot 5: Model summary card")


# ══════════════════════════════════════════════════════════
# Plot 6 — Data pipeline architecture diagram
# ══════════════════════════════════════════════════════════
fig, ax = setup_fig(12, 4)
ax.set_facecolor(BG)
ax.axis('off')
ax.set_xlim(0, 12)
ax.set_ylim(0, 4)

stages = [
    (1.0,  'Phase 1\nData Collection',  ['SEC EDGAR', 'GDELT News', 'LinkedIn', 'Glassdoor'], CYAN),
    (3.5,  'Phase 2\nNLP + Features',   ['FinBERT Sentiment', 'Distress Lexicon', '30 features'], GREEN),
    (6.0,  'Phase 3\nForecasting',      ['Prophet (6 signals)', 'LSTM (5 signals)', '1,818 rows'], PURPLE),
    (8.5,  'Phase 4\nRisk Modeling',    ['XGBoost AUC 0.94', 'Cox C-Index 0.90', 'SHAP explain'], YELLOW),
    (11.0, 'Phase 5\nDashboard',        ['FastAPI REST', 'React + Recharts', 'AWS EC2'], ORANGE),
]

for x, title, items, col in stages:
    # Box
    rect = mpatches.FancyBboxPatch((x - 0.95, 0.3), 1.9, 3.4,
        boxstyle="round,pad=0.1",
        facecolor=SURFACE, edgecolor=col + '55', linewidth=1.5,
        transform=ax.transData, zorder=2)
    ax.add_patch(rect)

    # Top accent
    rect2 = mpatches.FancyBboxPatch((x - 0.95, 3.45), 1.9, 0.25,
        boxstyle="round,pad=0.05",
        facecolor=col, alpha=0.2, edgecolor='none',
        transform=ax.transData, zorder=3)
    ax.add_patch(rect2)

    ax.text(x, 3.2, title, ha='center', va='center',
            fontsize=8.5, fontweight='bold', color=col,
            linespacing=1.4, transform=ax.transData, zorder=4)

    for j, item in enumerate(items):
        ax.text(x, 2.3 - j * 0.55, item, ha='center', va='center',
                fontsize=7.5, color=T3, transform=ax.transData, zorder=4)

# Arrows between stages
for i in range(len(stages) - 1):
    x1 = stages[i][0]   + 0.95
    x2 = stages[i+1][0] - 0.95
    col = stages[i][3]
    ax.annotate('', xy=(x2, 2), xytext=(x1, 2),
                arrowprops=dict(arrowstyle='->', color=col + '88', lw=1.5),
                transform=ax.transData, zorder=5)

ax.text(6, 3.9, 'SupplierWatch — End-to-End ML Pipeline',
        ha='center', va='center', fontsize=12, fontweight='bold',
        color=T1, transform=ax.transData)

plt.savefig('plots/06_pipeline_architecture.png', dpi=180, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("✅ Plot 6: Pipeline architecture")

# print("\n✅ All 6 plots generated in plots/")
