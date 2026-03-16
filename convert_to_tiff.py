"""Convert PNG figures to TIFF 300 DPI (LZW compression) for journal submission."""
from PIL import Image
import os

FIGURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figures')

for fname in sorted(os.listdir(FIGURES_DIR)):
    if not fname.endswith('.png'):
        continue
    src = os.path.join(FIGURES_DIR, fname)
    dst = os.path.join(FIGURES_DIR, fname.replace('.png', '.tiff'))
    try:
        img = Image.open(src)
        # Always composite onto white background to handle any transparency
        if img.mode != 'RGB':
            rgba = img.convert('RGBA')
            bg = Image.new('RGB', rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[3])
            img = bg
        img.save(dst, format='TIFF', dpi=(300, 300), compression='tiff_lzw')
        src_kb = os.path.getsize(src) / 1024
        dst_kb = os.path.getsize(dst) / 1024
        print(f"  {fname} ({src_kb:.0f} KB) -> {os.path.basename(dst)} ({dst_kb:.0f} KB)")
    except Exception as e:
        print(f"  ERROR: {fname} — {e}")

print("Done. All figures converted to TIFF 300 DPI.")
