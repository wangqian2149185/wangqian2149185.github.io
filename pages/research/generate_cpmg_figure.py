"""Rebuild the portfolio's synthetic CR illustration (Python + matplotlib).

All parameters are illustrative, not estimates from Wang et al. (2022).
Carver–Richards single-mode expression, equal intrinsic R2, ideal pulses.
nu_CPMG = 1/(4*tau_cp); dw in rad/s; kex in s^-1.
Model scope: Baldwin (2014), doi:10.1016/j.jmr.2014.02.023.
This is not an exact finite-time CPMG signal calculation or a fit.
"""
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).parent / 'assets'
OUT.mkdir(exist_ok=True)
PA, DW, R20 = 0.95, 1000.0, 10.0
RATES = (20000.0, 5000.0, 1000.0)


def cr(nu, kex):
    psi = kex**2 - DW**2
    root = math.sqrt(psi**2 + 4 * DW**2 * kex**2 * (2 * PA - 1)**2)
    dplus = 0.5 * (1 + (kex**2 + DW**2) / root)
    eta_plus = math.sqrt(psi + root) / (2 * math.sqrt(2) * nu)
    eta_minus = math.sqrt(-psi + root) / (2 * math.sqrt(2) * nu)
    argument = dplus * math.cosh(eta_plus) - (dplus - 1) * math.cos(eta_minus)
    return R20 + kex / 2 - nu * math.acosh(max(1.0, argument))


frequencies = [80 + 960 * i / 240 for i in range(241)]
curves = [[cr(nu, rate) for nu in frequencies] for rate in RATES]
assert all(math.isfinite(y) and y >= R20 - 1e-8 for curve in curves for y in curve)
assert abs(curves[0][0] - 12.3326) < 1e-4
with (OUT / 'exchange-rate-sweep.csv').open('w', newline='') as f:
    writer = csv.writer(f, lineterminator='\n')
    writer.writerow(['nu_CPMG_Hz', *[f'R2eff_s-1_kex_{k:g}_s-1' for k in RATES]])
    writer.writerows(zip(frequencies, *curves))

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'svg.fonttype': 'none'})
for theme, colors, ink, grid in [
    ('light', ['#6541b5', '#b34d05', '#007567'], '#263344', '#d5dde5'),
    ('dark', ['#bc9aff', '#ffb454', '#42f5ce'], '#e5edf7', '#394454'),
]:
    with plt.rc_context({'text.color': ink, 'axes.labelcolor': ink,
                         'axes.edgecolor': ink, 'xtick.color': ink, 'ytick.color': ink}):
        fig, ax = plt.subplots(figsize=(9.4, 5.3), layout='constrained')
        for k, values, color, style in zip(RATES, curves, colors, [':', '--', '-']):
            ax.plot(frequencies, values, label=rf'$k_{{ex}}$ = {k:,.0f} s$^{{-1}}$', color=color, linestyle=style, linewidth=2.7)
        ax.axhline(R20, color=ink, alpha=.55, linewidth=1, linestyle='--')
        ax.text(1020, 10.5, r'$R_{2,0}$', ha='right', fontsize=11, color=ink)
        ax.set(xlim=(80, 1040), ylim=(8, 36), xlabel=r'$\nu_{CPMG}$ (Hz)', ylabel=r'$R_{2,eff}$ (s$^{-1}$)')
        ax.set_xticks([80, 240, 400, 560, 720, 880, 1040])
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', color=grid, linewidth=0.8)
        ax.legend(frameon=False, loc='upper right')
        for suffix in ('svg', 'png'):
            path = OUT / f'exchange-rate-sweep-{theme}.{suffix}'
            fig.savefig(path, dpi=180, transparent=True)
            if suffix == 'svg':
                path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
            if theme == 'light':
                (OUT / f'exchange-rate-sweep.{suffix}').write_bytes(path.read_bytes())
        plt.close(fig)
for k, values in zip(RATES, curves):
    print(f'kex={k:g}: R(80)={values[0]:.6f}, R(1040)={values[-1]:.6f}, difference={values[0]-values[-1]:.6f}')
