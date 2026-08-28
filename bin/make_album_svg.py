#!/usr/bin/env python3
"""Embed a cover image into an SVG, optionally down-scaling it first."""

import argparse
import base64
import io
import mimetypes
import sys
from pathlib import Path

from PIL import Image

COVER_SIZE = 120
CANVAS_WIDTH = 150
CANVAS_HEIGHT = 130
X = 20
Y = 5

SUPPORTED_MIME = ("image/jpeg", "image/png", "image/gif", "image/webp")

# Map MIME types to Pillow save-format strings
_MIME_TO_FORMAT = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/gif": "GIF",
    "image/webp": "WEBP",
}


def _resize_image(path: Path, width: int, mime: str) -> bytes:
    """Load *path*, scale it so its width equals *width* (keeping aspect
    ratio), and return the re-encoded bytes in the original format."""
    with Image.open(path) as img:
        orig_w, orig_h = img.size
        if orig_w <= width:
            # Image is already small enough – return original bytes.
            return path.read_bytes()

        ratio = width / orig_w
        new_h = round(orig_h * ratio)
        resized = img.resize((width, new_h), Image.LANCZOS)

        buf = io.BytesIO()
        fmt = _MIME_TO_FORMAT.get(mime, "JPEG")
        save_kwargs: dict = {}
        if fmt == "JPEG":
            save_kwargs["quality"] = 85
        resized.save(buf, format=fmt, **save_kwargs)
        return buf.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an SVG with an embedded (and optionally resized) cover image.",
    )
    parser.add_argument("cover", type=Path, help="Path to the cover image (jpg/png/gif/webp)")
    parser.add_argument("output", nargs="?", type=Path, default=Path("album.svg"),
                        help="Output SVG path (default: album.svg)")
    parser.add_argument("-w", "--width", type=int, default=None,
                        help="Scale the cover image down to this pixel width before embedding")

    args = parser.parse_args()
    cover: Path = args.cover
    output: Path = args.output
    target_width: int | None = args.width

    if not cover.is_file():
        print(f"Error: cover not found: {cover}", file=sys.stderr)
        sys.exit(1)

    mime = mimetypes.guess_type(cover.name)[0] or "image/jpeg"
    if mime not in SUPPORTED_MIME:
        print(f"Error: unsupported image type: {mime}", file=sys.stderr)
        sys.exit(1)

    if target_width is not None:
        image_bytes = _resize_image(cover, target_width, mime)
    else:
        image_bytes = cover.read_bytes()

    data = base64.b64encode(image_bytes).decode("ascii")
    href = f"data:{mime};base64,{data}"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
     width="{CANVAS_WIDTH}"
     height="{CANVAS_HEIGHT}"
     viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}">

  <image
    href="{href}"
    x="{X}"
    y="{Y}"
    width="{COVER_SIZE}"
    height="{COVER_SIZE}"
    preserveAspectRatio="xMidYMid meet" />

</svg>
'''

    output.write_text(svg, encoding="utf-8")
    size_kb = len(image_bytes) / 1024
    print(f"Created {output}  (embedded image: {size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
