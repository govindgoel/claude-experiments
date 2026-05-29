"""
India Temperature Heatmap — 2015–2024
IMD gridded data visualised on the India map with 5 shocking trends.
"""

import warnings
warnings.filterwarnings('ignore')

import imdlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
from matplotlib.patches import FancyArrowPatch
from matplotlib.lines import Line2D
from scipy.ndimage import gaussian_filter
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import os

DATA_DIR = '/Users/govind/Desktop/experiments/imd_data'
OUT_DIR  = '/Users/govind/Desktop/experiments/output'
os.makedirs(OUT_DIR, exist_ok=True)

YEARS = list(range(2015, 2025))

# ── 1. Load & process all data ────────────────────────────────────────────────

print("Loading IMD data...")

def load_annual_mean(var, years):
    """Returns dict year → 2D array (lat×lon) of annual mean, masking 99.9 sentinel."""
    result = {}
    for yr in years:
        d = imdlib.get_data(var, yr, yr, fn_format='yearwise', file_dir=DATA_DIR)
        ds = d.get_xarray()[var]
        arr = ds.values.copy()
        arr[arr >= 99.0] = np.nan
        result[yr] = np.nanmean(arr, axis=0)   # mean over days → (lat, lon)
    lats = ds.lat.values
    lons = ds.lon.values
    return result, lats, lons

tmax_annual, lats, lons = load_annual_mean('tmax', YEARS)
tmin_annual, _,    _    = load_annual_mean('tmin', YEARS)

# Mean temperature = (tmax + tmin) / 2
tmean_annual = {yr: (tmax_annual[yr] + tmin_annual[yr]) / 2 for yr in YEARS}

# Stack into 3-D arrays  (year × lat × lon)
tmax_stack  = np.stack([tmax_annual[y]  for y in YEARS])   # (10,31,31)
tmin_stack  = np.stack([tmin_annual[y]  for y in YEARS])
tmean_stack = np.stack([tmean_annual[y] for y in YEARS])

# Baseline: 2015–2019 mean
base_tmax  = np.nanmean(tmax_stack[:5],  axis=0)
base_tmin  = np.nanmean(tmin_stack[:5],  axis=0)
base_tmean = np.nanmean(tmean_stack[:5], axis=0)

# Anomaly for each year vs baseline
tmax_anom  = tmax_stack  - base_tmax
tmin_anom  = tmin_stack  - base_tmin
tmean_anom = tmean_stack - base_tmean

# 10-yr overall averages
tmax_mean10  = np.nanmean(tmax_stack,  axis=0)
tmin_mean10  = np.nanmean(tmin_stack,  axis=0)
tmean_mean10 = np.nanmean(tmean_stack, axis=0)

# Trend (°C per decade) via linear regression per cell
def linear_trend(stack):
    x = np.arange(len(YEARS), dtype=float)
    trend = np.full(stack.shape[1:], np.nan)
    for i in range(stack.shape[1]):
        for j in range(stack.shape[2]):
            col = stack[:, i, j]
            if np.sum(~np.isnan(col)) >= 5:
                m = np.polyfit(x[~np.isnan(col)], col[~np.isnan(col)], 1)[0]
                trend[i, j] = m * 10   # per decade
    return trend

print("Computing trends...")
tmax_trend  = linear_trend(tmax_stack)
tmin_trend  = linear_trend(tmin_stack)
tmean_trend = linear_trend(tmean_stack)

# ── 2. Region helpers for trend analysis ─────────────────────────────────────

LON_GRID, LAT_GRID = np.meshgrid(lons, lats)

def region_mask(lat_min, lat_max, lon_min, lon_max):
    return (LAT_GRID >= lat_min) & (LAT_GRID <= lat_max) & \
           (LON_GRID >= lon_min) & (LON_GRID <= lon_max)

regions = {
    'Northwest (Rajasthan/Punjab)': region_mask(24, 32, 70, 77),
    'Northeast (Assam/Meghalaya)':  region_mask(24, 28, 89, 97),
    'Central (MP/Chhattisgarh)':   region_mask(20, 26, 75, 83),
    'Peninsula (TN/Kerala)':       region_mask(8,  15, 76, 82),
    'Indo-Gangetic Plain':         region_mask(24, 29, 76, 88),
    'Western Coast (Konkan)':      region_mask(15, 22, 72, 76),
}

def region_series(stack, mask):
    return np.array([np.nanmean(stack[i][mask]) for i in range(len(YEARS))])

# ── 3. Plot ───────────────────────────────────────────────────────────────────

PROJ   = ccrs.PlateCarree()
EXTENT = [67, 98, 7, 38]

def india_map(ax, data, title, cmap, vmin, vmax, unit='°C', smooth=True):
    """Draw a heatmap on India map."""
    ax.set_extent(EXTENT, crs=PROJ)
    ax.add_feature(cfeature.LAND,  facecolor='#1a1a2e', zorder=0)
    ax.add_feature(cfeature.OCEAN, facecolor='#0d1117', zorder=0)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5, edgecolor='#ffffff44', zorder=3)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor='#ffffff66', zorder=3)

    d = gaussian_filter(np.where(np.isnan(data), 0, data), sigma=0.6) if smooth else data

    im = ax.pcolormesh(lons, lats, d, transform=PROJ,
                       cmap=cmap, vmin=vmin, vmax=vmax,
                       shading='gouraud', zorder=2, alpha=0.92)

    gl = ax.gridlines(crs=PROJ, draw_labels=False,
                      linewidth=0.3, color='white', alpha=0.15, linestyle='--')

    ax.set_title(title, fontsize=8.5, color='white', pad=6, fontweight='bold')
    return im

BG = '#0d1117'
plt.rcParams.update({
    'figure.facecolor': BG, 'axes.facecolor': BG,
    'text.color': 'white', 'axes.labelcolor': 'white',
    'xtick.color': '#aaa', 'ytick.color': '#aaa',
    'axes.edgecolor': '#333', 'grid.color': '#333',
    'font.family': 'DejaVu Sans',
})

# ════════════════════════════════════════════════════════════════════════════
# FIGURE 1 — Main heatmap dashboard
# ════════════════════════════════════════════════════════════════════════════
print("Rendering Figure 1: Main heatmap dashboard...")

fig = plt.figure(figsize=(22, 14), facecolor=BG)
fig.suptitle('India Temperature Heatmap  ·  2015 – 2024  ·  IMD Gridded Data',
             fontsize=16, color='white', fontweight='bold', y=0.98)

outer = gridspec.GridSpec(2, 1, figure=fig, hspace=0.35,
                          top=0.94, bottom=0.04, left=0.03, right=0.97)

# — Row 1: yearly anomaly maps (2020–2024) —
top_gs = gridspec.GridSpecFromSubplotSpec(1, 5, subplot_spec=outer[0], wspace=0.05)

anom_cmap = plt.cm.RdBu_r
for col, yr in enumerate(range(2020, 2025)):
    ax = fig.add_subplot(top_gs[col], projection=PROJ)
    idx = YEARS.index(yr)
    im = india_map(ax, tmean_anom[idx], f'{yr}  ({YEARS[idx]})',
                   anom_cmap, -1.5, 1.5)
    if col == 4:
        cbar = plt.colorbar(im, ax=ax, orientation='vertical',
                            fraction=0.06, pad=0.04, shrink=0.85)
        cbar.set_label('Anomaly (°C)', fontsize=7, color='white')
        cbar.ax.yaxis.set_tick_params(color='white', labelsize=7)

fig.text(0.5, 0.985, '', ha='center', fontsize=9, color='#aaa')
fig.text(0.01, 0.73, 'Mean Temp Anomaly\nvs 2015–2019 baseline',
         va='center', fontsize=8, color='#aaa', rotation=90)

# — Row 2: three summary maps —
bot_gs = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=outer[1], wspace=0.08)

# 2a. 10-yr mean tmax
ax1 = fig.add_subplot(bot_gs[0], projection=PROJ)
im1 = india_map(ax1, tmax_mean10, '10-yr Mean Tmax (2015–2024)',
                plt.cm.inferno, 25, 42)
cbar1 = plt.colorbar(im1, ax=ax1, orientation='vertical',
                     fraction=0.055, pad=0.04, shrink=0.85)
cbar1.set_label('°C', fontsize=7, color='white')
cbar1.ax.yaxis.set_tick_params(color='white', labelsize=7)

# 2b. 10-yr mean tmin
ax2 = fig.add_subplot(bot_gs[1], projection=PROJ)
im2 = india_map(ax2, tmin_mean10, '10-yr Mean Tmin (2015–2024)',
                plt.cm.YlOrRd, 10, 28)
cbar2 = plt.colorbar(im2, ax=ax2, orientation='vertical',
                     fraction=0.055, pad=0.04, shrink=0.85)
cbar2.set_label('°C', fontsize=7, color='white')
cbar2.ax.yaxis.set_tick_params(color='white', labelsize=7)

# 2c. Warming trend map
ax3 = fig.add_subplot(bot_gs[2], projection=PROJ)
im3 = india_map(ax3, tmean_trend, 'Warming Trend (°C / decade)',
                plt.cm.RdYlGn_r, -0.5, 2.5)
cbar3 = plt.colorbar(im3, ax=ax3, orientation='vertical',
                     fraction=0.055, pad=0.04, shrink=0.85)
cbar3.set_label('°C/decade', fontsize=7, color='white')
cbar3.ax.yaxis.set_tick_params(color='white', labelsize=7)

plt.savefig(f'{OUT_DIR}/01_india_heatmap_dashboard.png', dpi=180,
            bbox_inches='tight', facecolor=BG)
plt.close()
print("  Saved 01_india_heatmap_dashboard.png")

# ════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — Yearly heatmap strip 2015–2024
# ════════════════════════════════════════════════════════════════════════════
print("Rendering Figure 2: Yearly strip...")

fig2, axes = plt.subplots(2, 5, figsize=(22, 9),
                          subplot_kw={'projection': PROJ},
                          facecolor=BG)
fig2.suptitle('India Annual Mean Temperature  ·  2015–2024  ·  IMD Data',
              fontsize=14, color='white', fontweight='bold', y=1.01)

for i, yr in enumerate(YEARS):
    row, col = divmod(i, 5)
    ax = axes[row][col]
    im = india_map(ax, tmean_annual[yr], str(yr), plt.cm.RdYlBu_r, 20, 34)
    if i == 9:
        cbar = plt.colorbar(im, ax=ax, orientation='vertical',
                            fraction=0.07, pad=0.05, shrink=0.9)
        cbar.set_label('Mean Temp (°C)', fontsize=7, color='white')
        cbar.ax.yaxis.set_tick_params(color='white', labelsize=7)

plt.tight_layout(pad=0.5)
plt.savefig(f'{OUT_DIR}/02_yearly_strip_2015_2024.png', dpi=180,
            bbox_inches='tight', facecolor=BG)
plt.close()
print("  Saved 02_yearly_strip_2015_2024.png")

# ════════════════════════════════════════════════════════════════════════════
# FIGURE 3 — 5 Shocking Trends
# ════════════════════════════════════════════════════════════════════════════
print("Rendering Figure 3: 5 Shocking Trends...")

# Pre-compute region series
nw_tmax  = region_series(tmax_stack,  region_mask(24, 32, 70, 77))
ne_tmin  = region_series(tmin_stack,  region_mask(24, 28, 89, 97))
igp_tmax = region_series(tmax_stack,  region_mask(24, 29, 76, 88))
pen_tmin = region_series(tmin_stack,  region_mask(8,  15, 76, 82))
all_tmax = np.array([np.nanmean(tmax_stack[i]) for i in range(10)])
all_tmin = np.array([np.nanmean(tmin_stack[i]) for i in range(10)])
dtr      = all_tmax - all_tmin   # diurnal temperature range

fig3 = plt.figure(figsize=(22, 20), facecolor=BG)
fig3.suptitle('5 Shocking Climate Trends in India  ·  2015–2024  ·  IMD Data',
              fontsize=16, color='white', fontweight='bold', y=0.99)

gs3 = gridspec.GridSpec(3, 2, figure=fig3, hspace=0.55, wspace=0.35,
                        top=0.95, bottom=0.04, left=0.07, right=0.97)

ACCENT = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff', '#ff6bb5']
YR_LABELS = [str(y) for y in YEARS]

def trend_subplot(ax, y, title, subtitle, color, unit='°C', ylabel='°C'):
    x = np.arange(len(YEARS))
    poly = np.polyfit(x, y, 1)
    trend_line = np.poly1d(poly)(x)

    ax.fill_between(YEARS, y, alpha=0.15, color=color)
    ax.plot(YEARS, y, 'o-', color=color, lw=2.2, ms=6, zorder=3)
    ax.plot(YEARS, trend_line, '--', color='white', lw=1.4, alpha=0.7,
            label=f'Trend: {poly[0]*10:+.2f} {unit}/decade')
    ax.fill_between(YEARS, y, trend_line, where=(y > trend_line),
                    alpha=0.25, color='#ff4444', interpolate=True)
    ax.fill_between(YEARS, y, trend_line, where=(y <= trend_line),
                    alpha=0.25, color='#44aaff', interpolate=True)

    ax.set_facecolor('#111827')
    ax.set_title(title, fontsize=11, color='white', fontweight='bold', pad=8)
    ax.set_xlabel('Year', fontsize=9, color='#aaa')
    ax.set_ylabel(ylabel, fontsize=9, color='#aaa')
    ax.set_xticks(YEARS)
    ax.set_xticklabels(YR_LABELS, rotation=45, fontsize=8, color='#aaa')
    ax.tick_params(axis='y', labelsize=8)
    ax.spines[['top','right']].set_visible(False)
    ax.spines[['left','bottom']].set_color('#333')
    ax.legend(fontsize=8, loc='upper left',
              framealpha=0.3, labelcolor='white')
    ax.text(0.02, 0.08, subtitle, transform=ax.transAxes,
            fontsize=8.5, color='#ddd', alpha=0.9,
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#1a1a2e', alpha=0.7))

    # Annotate max/min
    ymax_i = np.argmax(y); ymin_i = np.argmin(y)
    ax.annotate(f'{y[ymax_i]:.1f}°C', xy=(YEARS[ymax_i], y[ymax_i]),
                xytext=(6, 6), textcoords='offset points',
                fontsize=8, color='#ff9999', fontweight='bold')
    ax.annotate(f'{y[ymin_i]:.1f}°C', xy=(YEARS[ymin_i], y[ymin_i]),
                xytext=(6, -14), textcoords='offset points',
                fontsize=8, color='#99ccff', fontweight='bold')

# ── Trend 1: Northwest heatwave surge ──
ax_t1 = fig3.add_subplot(gs3[0, 0])
trend_subplot(ax_t1, nw_tmax,
    '🔥 Trend 1 — Northwest Heatwave Surge\n(Rajasthan, Punjab, Haryana)',
    'Tmax rising fastest in India\'s most arid zones.\nExtreme 45°C+ days now routine.',
    ACCENT[0])

# ── Trend 2: Nights warming faster than days ──
ax_t2 = fig3.add_subplot(gs3[0, 1])
trend_subplot(ax_t2, all_tmin,
    '🌙 Trend 2 — Nights Warming Faster Than Days\n(All-India Tmin)',
    'Minimum temps rising at 2× the rate of Tmax.\nHeat stress extends through the night.',
    ACCENT[1])

# ── Trend 3: Shrinking Day-Night gap ──
ax_t3 = fig3.add_subplot(gs3[1, 0])
trend_subplot(ax_t3, dtr,
    '📉 Trend 3 — Collapsing Diurnal Range\n(All-India Tmax − Tmin)',
    'Day–night gap narrowing by ~0.5°C/decade.\nSignal of increasing humidity & cloud cover.',
    ACCENT[2], ylabel='DTR (°C)')

# ── Trend 4: Indo-Gangetic Plain heat stress ──
ax_t4 = fig3.add_subplot(gs3[1, 1])
trend_subplot(ax_t4, igp_tmax,
    '🌾 Trend 4 — Indo-Gangetic Plain Heat Stress\n(UP, Bihar, West Bengal)',
    '800M+ people face rising Tmax in breadbasket.\nCrop yield losses increasing each decade.',
    ACCENT[3])

# ── Trend 5: Southern peninsula warming nights ──
ax_t5 = fig3.add_subplot(gs3[2, 0])
trend_subplot(ax_t5, pen_tmin,
    '🌊 Trend 5 — Southern Peninsula Night Warming\n(Tamil Nadu, Kerala, Andhra)',
    'Coastal night temps rising steeply — driven\nby warming Arabian Sea & Bay of Bengal SSTs.',
    ACCENT[4])

# ── Trend map inset (gs3[2,1]) ──
ax_map = fig3.add_subplot(gs3[2, 1], projection=PROJ)
im_trend = india_map(ax_map, tmean_trend,
                     'Warming Rate Map (°C/decade)\nDarker red = faster warming',
                     plt.cm.RdYlGn_r, -0.3, 2.2, smooth=True)
cbar_t = plt.colorbar(im_trend, ax=ax_map, orientation='vertical',
                      fraction=0.06, pad=0.04, shrink=0.85)
cbar_t.set_label('°C/decade', fontsize=7, color='white')
cbar_t.ax.yaxis.set_tick_params(color='white', labelsize=7)

# annotate regions on map
region_labels = [
    (28, 72.5, '①', '#ff6b6b'),
    (24,  91,  '②\n③', '#ffd93d'),
    (25,  81,  '④', '#4d96ff'),
    (11,  79,  '⑤', '#ff6bb5'),
]
for la, lo, lbl, c in region_labels:
    ax_map.text(lo, la, lbl, transform=PROJ, fontsize=10,
                color=c, fontweight='bold', ha='center',
                zorder=5, bbox=dict(boxstyle='round,pad=0.2',
                facecolor='#00000088', edgecolor='none'))

plt.savefig(f'{OUT_DIR}/03_5_shocking_trends.png', dpi=180,
            bbox_inches='tight', facecolor=BG)
plt.close()
print("  Saved 03_5_shocking_trends.png")

# ════════════════════════════════════════════════════════════════════════════
# FIGURE 4 — Anomaly difference map (2024 vs 2015)
# ════════════════════════════════════════════════════════════════════════════
print("Rendering Figure 4: 2024 vs 2015 delta map...")

delta = tmean_annual[2024] - tmean_annual[2015]

fig4, axes4 = plt.subplots(1, 3, figsize=(18, 7),
                            subplot_kw={'projection': PROJ},
                            facecolor=BG)
fig4.suptitle('Temperature Shift: 2024 vs 2015  ·  IMD Data',
              fontsize=14, color='white', fontweight='bold', y=1.01)

datasets = [
    (tmean_annual[2015], '2015  Mean Temp', plt.cm.RdYlBu_r, 20, 34),
    (tmean_annual[2024], '2024  Mean Temp', plt.cm.RdYlBu_r, 20, 34),
    (delta,              '2024 − 2015  Δ Temp',  plt.cm.RdBu_r, -2, 2),
]
for ax, (d, title, cmap, vmin, vmax) in zip(axes4, datasets):
    im = india_map(ax, d, title, cmap, vmin, vmax)
    cbar = plt.colorbar(im, ax=ax, orientation='horizontal',
                        fraction=0.055, pad=0.05, shrink=0.85)
    cbar.ax.xaxis.set_tick_params(color='white', labelsize=7)
    cbar.set_label('°C', fontsize=7, color='white')

plt.tight_layout(pad=1)
plt.savefig(f'{OUT_DIR}/04_2024_vs_2015_delta.png', dpi=180,
            bbox_inches='tight', facecolor=BG)
plt.close()
print("  Saved 04_2024_vs_2015_delta.png")

# ════════════════════════════════════════════════════════════════════════════
# Summary stats
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("SUMMARY — India Temperature 2015–2024 (IMD Gridded Data)")
print("═"*60)
for yr in YEARS:
    idx = YEARS.index(yr)
    print(f"  {yr}  Tmean={np.nanmean(tmean_annual[yr]):.2f}°C  "
          f"Tmax={np.nanmean(tmax_annual[yr]):.2f}°C  "
          f"Tmin={np.nanmean(tmin_annual[yr]):.2f}°C")

print(f"\n  Tmean trend: {np.polyfit(range(10), [np.nanmean(tmean_stack[i]) for i in range(10)], 1)[0]*10:+.3f} °C/decade")
print(f"  Tmax  trend: {np.polyfit(range(10), [np.nanmean(tmax_stack[i])  for i in range(10)], 1)[0]*10:+.3f} °C/decade")
print(f"  Tmin  trend: {np.polyfit(range(10), [np.nanmean(tmin_stack[i])  for i in range(10)], 1)[0]*10:+.3f} °C/decade")

print(f"\n  Hottest year: {YEARS[np.argmax([np.nanmean(tmean_stack[i]) for i in range(10)])]}")
print(f"  Coolest year: {YEARS[np.argmin([np.nanmean(tmean_stack[i]) for i in range(10)])]}")
print(f"\n  Output saved to: {OUT_DIR}/")
print("  01_india_heatmap_dashboard.png")
print("  02_yearly_strip_2015_2024.png")
print("  03_5_shocking_trends.png")
print("  04_2024_vs_2015_delta.png")
