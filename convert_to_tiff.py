"""Convert PNG figures to TIFF 300 DPI (LZW compression) for journal submission."""
from PIL import Image
import os

FIGURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figures')

for fname in sorted(os.listdir(FIGURES_DIR)):
    if not fname.endswith('.png'):
        continue
    src = os.path.join(FIGURES_DIR, fname)
    dst = os.path.join(FIGURES_DIR, fname.replace('.png', '.tiff'))
    img = Image.open(src)
    # Convert RGBA to RGB (TIFF with LZW doesn't handle alpha well)
    if img.mode == 'RGBA':
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    img.save(dst, format='TIFF', dpi=(300, 300), compression='tiff_lzw')
    src_kb = os.path.getsize(src) / 1024
    dst_kb = os.path.getsize(dst) / 1024
    print(f"  {fname} ({src_kb:.0f} KB) -> {os.path.basename(dst)} ({dst_kb:.0f} KB)")

print("Done. All figures converted to TIFF 300 DPI.")
