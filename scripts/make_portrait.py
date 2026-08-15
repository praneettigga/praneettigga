#!/usr/bin/env python3
"""Create the animated ASCII portrait used by the profile README.

The source photograph is intentionally not stored in the repository. Pass a
local image, tune the crop/mask if needed, and commit only the generated SVG.
Requires Pillow (`python -m pip install Pillow`).
"""

from __future__ import annotations

import argparse
import base64
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


RAMP = " .,:;irsXA253hMHGS#9B&@"
LIGHT = "#57606a"
DARK = "#c9d1d9"
FONT_SIZE = 12
CHAR_WIDTH = 7.22
LINE_HEIGHT = 14


def parse_box(value: str) -> tuple[int, int, int, int]:
    values = tuple(int(part.strip()) for part in value.split(","))
    if len(values) != 4:
        raise argparse.ArgumentTypeError("expected left,top,right,bottom")
    return values


def parse_points(value: str) -> list[tuple[float, float]]:
    """Parse normalized x:y points used for a feathered subject mask."""
    try:
        points = [tuple(float(n) for n in pair.split(":")) for pair in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected x:y,x:y using values from 0 to 1") from exc
    if len(points) < 3 or any(len(point) != 2 for point in points):
        raise argparse.ArgumentTypeError("a mask needs at least three x:y points")
    if any(not 0 <= n <= 1 for point in points for n in point):
        raise argparse.ArgumentTypeError("mask coordinates must be between 0 and 1")
    return points


def load_font(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return (
        "@font-face{font-family:ProfileMono;font-style:normal;font-weight:400;"
        f"src:url(data:font/woff2;base64,{encoded}) format('woff2')}}"
    )


def prepare(source: Path, crop: tuple[int, int, int, int] | None,
            mask_points: list[tuple[float, float]] | None) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    if crop:
        image = image.crop(crop)

    # Preserve a hand-cut PNG's real alpha edge. Compositing before contrast
    # processing also keeps transparent pixels from skewing the tonal range.
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    flattened = Image.alpha_composite(white, image).convert("RGB")
    gray = ImageOps.grayscale(flattened)
    gray = ImageOps.autocontrast(gray, cutoff=(1, 2))
    gray = ImageEnhance.Contrast(gray).enhance(1.28)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=1.5, percent=125, threshold=3))

    if mask_points:
        width, height = gray.size
        polygon = [(round(x * width), round(y * height)) for x, y in mask_points]
        mask = Image.new("L", gray.size, 0)
        ImageDraw.Draw(mask).polygon(polygon, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(max(2, width // 90)))
        gray = Image.composite(gray, Image.new("L", gray.size, 255), mask)

    # A mild darkening curve preserves eyes, glasses, lapels, and hair after the
    # image is reduced to a small character grid.
    return gray.point(lambda value: round(255 * (value / 255) ** 1.58))


def ascii_rows(image: Image.Image, columns: int) -> list[str]:
    width, height = image.size
    rows = max(1, round(columns * (height / width) * 0.48))
    reduced = image.resize((columns, rows), Image.Resampling.LANCZOS)
    pixels = list(reduced.get_flattened_data())
    output: list[str] = []
    for row in range(rows):
        line = "".join(
            RAMP[min(len(RAMP) - 1, round((1 - pixels[row * columns + col] / 255) * (len(RAMP) - 1)))]
            for col in range(columns)
        ).rstrip()
        output.append(line)
    while output and not output[0].strip():
        output.pop(0)
    while output and not output[-1].strip():
        output.pop()
    return output


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(rows: list[str], font_path: Path, alt: str) -> str:
    padding = 12
    width = round(max((len(row) for row in rows), default=1) * CHAR_WIDTH + padding * 2)
    height = len(rows) * LINE_HEIGHT + padding * 2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f"<title id=\"title\">{escape(alt)}</title>",
        '<desc id="desc">A monochrome portrait drawn with animated ASCII characters.</desc>',
        f"<style>{load_font(font_path)}.ink{{fill:{LIGHT}}}"
        f"@media(prefers-color-scheme:dark){{.ink{{fill:{DARK}}}}}</style>",
    ]
    for index, row in enumerate(rows):
        y = padding + index * LINE_HEIGHT
        delay = index * 0.055
        row_width = max(1, len(row)) * CHAR_WIDTH
        parts.append(
            f'<clipPath id="row{index}"><rect x="{padding}" y="{y}" height="{LINE_HEIGHT}" width="0">'
            f'<animate attributeName="width" from="0" to="{row_width:.1f}" begin="{delay:.3f}s" '
            f'dur="0.32s" fill="freeze"/></rect></clipPath>'
        )
        parts.append(
            f'<text x="{padding}" y="{y + 10.5:.1f}" class="ink" font-family="ProfileMono,monospace" '
            f'font-size="{FONT_SIZE}" xml:space="preserve" clip-path="url(#row{index})">{escape(row)}</text>'
        )
        parts.append(
            f'<rect y="{y + 1}" width="5" height="11" class="ink" opacity="0">'
            f'<animate attributeName="x" from="{padding}" to="{padding + row_width:.1f}" '
            f'begin="{delay:.3f}s" dur="0.32s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.75" begin="{delay:.3f}s"/>'
            f'<set attributeName="opacity" to="0" begin="{delay + 0.32:.3f}s"/></rect>'
        )
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("photo", type=Path)
    parser.add_argument("--output", type=Path, default=Path("assets/portrait.svg"))
    parser.add_argument("--font", type=Path, default=Path("assets/fonts/mono-regular.woff2"))
    parser.add_argument("--crop", type=parse_box)
    parser.add_argument("--mask-points", type=parse_points)
    parser.add_argument("--columns", type=int, default=82)
    parser.add_argument("--alt", default="Praneet Nischal Tigga")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    rows = ascii_rows(prepare(args.photo, args.crop, args.mask_points), args.columns)
    if args.preview:
        print("\n".join(rows))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(rows, args.font, args.alt), encoding="utf-8")
    print(f"wrote {args.output} ({len(rows)} rows x {args.columns} columns)")


if __name__ == "__main__":
    main()
