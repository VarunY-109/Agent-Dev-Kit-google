"""Image Analysis Agent.

A pure-Python ADK agent that accepts image inputs (uploaded through
the ADK web UI) and answers questions about them. The agent also
exposes a small set of helper tools for working with image files on
disk.

Tools:

* ``load_image`` - read a local image file, return its size, mode
  and a base64 preview that downstream tools can embed in a prompt.
* ``image_metadata`` - return EXIF-free metadata (size, mode, format).
* ``analyze_image`` - placeholder that returns a deterministic
  description derived from file properties, useful for offline smoke
  tests.
"""

import base64
import io
import os
from typing import Dict

try:
    from PIL import Image  # type: ignore
    _PIL_OK = True
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore
    _PIL_OK = False

from google.adk.agents import Agent

_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB
_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def _validate_path(path: str) -> Dict:
    if not path:
        return {"status": "error", "error": "No path provided."}
    if not os.path.isfile(path):
        return {"status": "error", "error": f"File not found: {path!r}"}
    suffix = os.path.splitext(path)[1].lower()
    if suffix not in _ALLOWED_SUFFIXES:
        return {
            "status": "error",
            "error": f"Unsupported image type '{suffix}'. "
                     f"Allowed: {sorted(_ALLOWED_SUFFIXES)}",
        }
    size = os.path.getsize(path)
    if size > _MAX_IMAGE_BYTES:
        return {
            "status": "error",
            "error": f"Image is {size} bytes; max is {_MAX_IMAGE_BYTES}.",
        }
    return {"status": "ok", "suffix": suffix, "size": size}


def image_metadata(path: str) -> dict:
    """Return basic metadata for an image file on disk.

    Args:
        path: Filesystem path to the image.

    Returns:
        A dict with file size, format, and (if Pillow is available)
        pixel dimensions and colour mode.
    """
    ok = _validate_path(path)
    if ok["status"] != "ok":
        return ok

    info: Dict = {
        "status": "ok",
        "path": os.path.abspath(path),
        "size_bytes": ok["size"],
        "format": os.path.splitext(path)[1].lstrip(".").upper(),
    }

    if _PIL_OK:
        with Image.open(path) as im:  # type: ignore[arg-type]
            info["width"] = im.width
            info["height"] = im.height
            info["mode"] = im.mode
            info["format"] = (im.format or info["format"]).upper()
    else:
        info["note"] = "Pillow not installed; install `Pillow` for pixel-level metadata."

    return info


def load_image(path: str, max_dim: int = 1024) -> dict:
    """Load an image, downscale it if needed and return a base64 preview.

    Args:
        path:    Filesystem path to the image.
        max_dim: Maximum width or height (in pixels) after resizing.
                 Set to 0 to skip resizing.

    Returns:
        A dict with the image's metadata plus a base64-encoded
        preview that the LLM can use as multimodal context.
    """
    ok = _validate_path(path)
    if ok["status"] != "ok":
        return ok

    if not _PIL_OK:
        with open(path, "rb") as f:
            data = f.read()
        return {
            "status": "ok",
            "path": os.path.abspath(path),
            "size_bytes": ok["size"],
            "encoding": "base64",
            "mime_type": f"image/{ok['suffix'].lstrip('.').replace('jpg','jpeg')}",
            "data": base64.b64encode(data).decode("ascii"),
            "note": "Pillow not installed; returning original bytes without resizing.",
        }

    with Image.open(path) as im:  # type: ignore[arg-type]
        original = {"width": im.width, "height": im.height, "mode": im.mode}
        if max_dim and max(im.size) > max_dim:
            im.thumbnail((max_dim, max_dim))
        buf = io.BytesIO()
        fmt = (im.format or "PNG").upper()
        mime = "image/png" if fmt == "PNG" else f"image/{fmt.lower()}"
        if fmt == "JPEG" and im.mode != "RGB":
            im = im.convert("RGB")
        im.save(buf, format=fmt)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "status": "ok",
        "path": os.path.abspath(path),
        "size_bytes": ok["size"],
        "original": original,
        "resized": {"width": im.width, "height": im.height},
        "encoding": "base64",
        "mime_type": mime,
        "data": encoded,
    }


def dominant_colors(path: str, n: int = 5) -> dict:
    """Return the most common colours in an image as hex codes.

    Args:
        path: Filesystem path to the image.
        n:    How many colours to return (default 5, max 20).

    Returns:
        A dict with a list of ``{"hex": str, "count": int}`` entries.
    """
    ok = _validate_path(path)
    if ok["status"] != "ok":
        return ok
    if not _PIL_OK:
        return {
            "status": "error",
            "error": "Pillow is required for color analysis. `pip install Pillow`.",
        }

    n = max(1, min(int(n), 20))
    with Image.open(path) as im:  # type: ignore[arg-type]
        im = im.convert("RGB").resize((128, 128))  # speed up
        pixels = list(im.getdata())

    counts: Dict[int, int] = {}
    for r, g, b in pixels:
        key = ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)
        counts[key] = counts.get(key, 0) + 1

    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]
    colors = []
    for key, count in top:
        r = ((key >> 8) & 0xF) * 17
        g = ((key >> 4) & 0xF) * 17
        b = (key & 0xF) * 17
        colors.append({"hex": f"#{r:02X}{g:02X}{b:02X}", "count": count})

    return {"status": "ok", "colors": colors}


root_agent = Agent(
    name="image_analysis_agent",
    model="gemini-2.0-flash",
    description=(
        "Multimodal agent that describes, summarises and answers "
        "questions about images the user uploads or references by path."
    ),
    instruction="""
    You are a multimodal image-analysis assistant.

    CAPABILITIES:
    - When the user attaches an image in the ADK web UI, the Gemini
      model receives it directly - describe what you see, answer
      the user's question, and quote any visible text verbatim.
    - When the user references an image by file path, first call
      `image_metadata` to confirm the file exists and is readable,
      then `load_image` to obtain a base64 preview, and finally
      call `dominant_colors` to enrich the description with palette
      information.

    RULES:
    - Never invent text, numbers, or labels that you cannot see.
    - If the image is blurry, say so rather than guessing.
    - When the user asks for structured data (JSON, table), format
      your final response using the requested schema.
    - Cite pixel-level facts (size, colours) from the tools, not
      from visual estimation.
    """,
    tools=[image_metadata, load_image, dominant_colors],
)
