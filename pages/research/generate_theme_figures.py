"""Theme-only derivatives of recorded figures; never reconstruct numerical data.

Remove the white matte and replace ink colors at the original pixel coordinates.
Recovered alpha preserves scatter density/antialiasing. No resize, crop, fitting,
interpolation, or new predictions. Original files remain unchanged and linked.
Requires numpy and Pillow. Run after generate_cpmg_figure.py for all chart assets.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).parent / 'assets'
PALETTES = {
    'light': {'ink': '#263344', 'blue': '#175da3', 'orange': '#b75b00'},
    'dark': {'ink': '#e5edf7', 'blue': '#54cfff', 'orange': '#ffb454'},
}


def rgb(hex_color):
    return np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255


records = []
for name in ('chemical-shift-gnn-recorded.png', 'chemical-shift-mlp-recorded.png',
             'published-dispersion-figure4.jpg'):
    source = OUT / name
    pixels = np.asarray(Image.open(source).convert('RGB'), dtype=float) / 255
    r, g, b = np.moveaxis(pixels, -1, 0)
    published = source.suffix == '.jpg'
    # Saved scatter uses matplotlib tab:blue. Published figure uses blue/orange.
    blue = (b - r > .04) & (b > g)
    orange = (r - b > .04) & (r > g)
    if not published:
        orange[:] = False
    alpha = 1 - pixels.mean(axis=-1)
    blue_source = rgb('#363397' if published else '#1f77b4')
    alpha[blue] = np.max((1 - pixels[blue]) / (1 - blue_source), axis=-1)
    alpha[orange] = np.max((1 - pixels[orange]) / (1 - rgb('#f39c12')), axis=-1)
    # JPEG white-matte compression noise is not figure content.
    if published:
        alpha[pixels.min(axis=-1) >= 250 / 255] = 0
    alpha = np.clip(alpha, 0, 1)
    derivatives = []
    for theme, palette in PALETTES.items():
        colors = np.broadcast_to(rgb(palette['ink']), pixels.shape).copy()
        colors[blue] = rgb(palette['blue'])
        colors[orange] = rgb(palette['orange'])
        rgba = np.rint(np.dstack([colors, alpha]) * 255).astype('uint8')
        target = OUT / f'{source.stem}-{theme}.png'
        Image.fromarray(rgba).save(target)
        assert Image.open(target).size == Image.open(source).size
        derivatives.append(target.name)
    records.append({'source': name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'size_px': list(Image.open(source).size), 'derivatives': derivatives})

(OUT / 'theme-figure-provenance.json').write_text(json.dumps({
    'method': 'White-matte removal and per-pixel ink recoloring only; original pixel coordinates and dimensions retained.',
    'script': '../generate_theme_figures.py', 'palettes': PALETTES, 'figures': records,
}, indent=2) + '\n')
