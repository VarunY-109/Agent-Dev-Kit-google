# === MODULE METADATA ===
# File: image_analysis_agent/agent.py
# Version: 1.1.0
# Author: Image Analysis Agent Team
# Date: 2025-01-15
# Description: A pure-Python ADK agent that accepts image inputs (uploaded through
#   the ADK web UI) and answers questions about them. The agent also exposes a
#   small set of helper tools for working with image files on disk.
# License: Proprietary / Internal Use
# Requirements: google-adk, Pillow (optional but recommended)
#
# === USAGE OVERVIEW ===
# This module defines three callable tools (`image_metadata`, `load_image`,
# `dominant_colors`) and a root ADK `Agent` named `root_agent` that wires them
# together with a multimodal capable model (gemini-2.0-flash).
#
# Quick example:
#   >>> from image_analysis_agent.agent import root_agent
#   >>> # Use root_agent within an ADK session to process user-uploaded images.
#   >>> from image_analysis_agent.agent import load_image
#   >>> result = load_image("/path/to/photo.jpg", max_dim=512)
#   >>> result["data"]  # base64-encoded preview string
#
# Tool summary:
#   - image_metadata  : Lightweight file/dimension inspection (no decoding overhead).
#   - load_image      : Full decode, optional downscale, and base64 export.
#   - dominant_colors : Colour palette extraction via quantised pixel counting.
#
# IMPORTANT: All tools share a common validation step via `_validate_path`.
# Failures return a dict with "status": "error" rather than raising exceptions,
# so callers must check the status before using other fields.
#
# TODO (v1.2.0): Add EXIF extraction support when Pillow ≥ 10.0 is required.
# FIXME: The `dominant_colors` function uses a fixed 128×128 resize which may
#   lose accuracy for very small images; consider adaptive sizing.


# === IMPORTS AND ENVIRONMENT SETUP ===
# Standard library imports used throughout the module.
import base64    # For encoding binary image data to base64 strings.
import io         # For in-memory binary buffers (BytesIO) during image encoding.
import os         # For filesystem path validation and size checks.
from typing import Dict  # Type hint for dictionary return values.

# NOTE: Pillow is an optional dependency. The agent functions without it,
# but with reduced capabilities (no resizing, no pixel metadata, no color analysis).
# We gracefully degrade by catching the import failure at module load time.
try:
    from PIL import Image  # type: ignore
    _PIL_OK = True  # Flag indicating Pillow is available for advanced operations.
except Exception:  # pragma: no cover - optional dependency path
    Image = None  # type: ignore
    _PIL_OK = False

# ADK framework import — provides the Agent class used to construct root_agent.
from google.adk.agents import Agent


# === CONSTANTS AND CONFIGURATION ===
# Maximum file size (8 MB) allowed for image uploads. This prevents memory
# exhaustion when a user accidentally selects a large video or uncompressed TIFF.
# TODO (v1.2.0): Make _MAX_IMAGE_BYTES configurable via environment variable.
_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB ceiling for safety

# Whitelist of accepted file extensions. Lowercase comparisons are performed
# on the extension to avoid case-sensitivity issues (e.g., ".JPG" vs ".jpg").
_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


# === UTILITY: PATH VALIDATION ===
# All public tools call `_validate_path` first to centralise error handling.
# This avoids duplicated checks and ensures consistent error response shapes.
# Type: (path: str) -> Dict[str, object]
def _validate_path(path: str) -> Dict:
    """Validate that `path` points to a permissible image file.

    The function performs four sequential checks, returning early on the
    first failure:

    1. **Non-empty path** — an empty string is meaningless.
    2. **File existence** — verifies the path resolves to a regular file.
    3. **Extension whitelist** — only known image formats are accepted.
    4. **File size limit** — rejects files larger than 8 MB.

    Args:
        path: Absolute or relative filesystem path to the candidate image.

    Returns:
        On success: ``{"status": "ok", "suffix": ".png", "size": 12345}``
        On failure: ``{"status": "error", "error": "descriptive message"}``

    Examples:
        >>> _validate_path("")
        {'status': 'error', 'error': 'No path provided.'}
        >>> _validate_path("/nonexistent/file.txt")
        {'status': 'error', 'error': "File not found: '/nonexistent/file.txt'"}
        >>> _validate_path("/tmp/photo.png")  # doctest: +SKIP
        {'status': 'ok', 'suffix': '.png', 'size': 45231}

    NOTE: This function does NOT open the file or read its contents,
    so it is safe to call for untrusted paths without triggering decompression
    attacks (though the subsequent `Image.open` in other functions is not
    immune to malicious image files — see CVE-2016-xxx for historical context).
    """
    # Check 1 — reject empty or None-like paths immediately.
    if not path:
        return {"status": "error", "error": "No path provided."}

    # Check 2 — confirm the file actually exists on disk.
    if not os.path.isfile(path):
        return {"status": "error", "error": f"File not found: {path!r}"}

    # Check 3 — ensure the file extension is in our allowed set.
    # We normalise to lowercase so ".JPG" and ".jpg" are treated identically.
    suffix = os.path.splitext(path)[1].lower()
    if suffix not in _ALLOWED_SUFFIXES:
        return {
            "status": "error",
            "error": f"Unsupported image type '{suffix}'. "
                     f"Allowed: {sorted(_ALLOWED_SUFFIXES)}",
        }

    # Check 4 — enforce the 8 MB upper bound to protect memory.
    size = os.path.getsize(path)
    if size > _MAX_IMAGE_BYTES:
        return {
            "status": "error",
            "error": f"Image is {size} bytes; max is {_MAX_IMAGE_BYTES}.",
        }

    return {"status": "ok", "suffix": suffix, "size": size}


# === SECTION: TOOL — IMAGE METADATA ===
# Type: (path: str) -> dict
def image_metadata(path: str) -> dict:
    """Return basic metadata for an image file on disk.

    This is the lightest-touch tool: it avoids decoding the full image when
    Pillow is unavailable and simply reports file-level information.

    Args:
        path: Filesystem path to the image file (absolute or relative).

    Returns:
        A dictionary with the following keys on success:

        - ``status``       : Always ``"ok"`` on success.
        - ``path``         : Absolute path (normalised via ``os.path.abspath``).
        - ``size_bytes``   : File size in bytes.
        - ``format``       : File extension uppercased (e.g., ``"PNG"``).
        - ``width``        : Pixel width (only if Pillow is installed).
        - ``height``       : Pixel height (only if Pillow is installed).
        - ``mode``         : Colour mode, e.g. ``"RGB"``, ``"RGBA"``, ``"L"``.
        - ``note``         : Present only if Pillow is missing, explaining
                             the limitation.

        On failure returns the same error dict shape as `_validate_path`.

    Raises:
        This function does NOT raise exceptions; all errors are embedded
        in the returned dict under the ``"error"`` key.

    Examples:
        >>> image_metadata("/tmp/screenshot.png")
        {'status': 'ok', 'path': '/tmp/screenshot.png', 'size_bytes': 204800,
         'format': 'PNG', 'width': 1920, 'height': 1080, 'mode': 'RGB'}

    NOTE: The ``format`` field is derived from the file extension when Pillow
    is unavailable, which may differ from the actual encoding (e.g., a file
    named ``.jpg`` might actually be a progressive JPEG or even a rename).
    """
    # Step 1 — run shared validation; abort early on any error.
    ok = _validate_path(path)
    if ok["status"] != "ok":
        return ok

    # Step 2 — build the base metadata dict from filesystem info alone.
    info: Dict = {
        "status": "ok",
        "path": os.path.abspath(path),
        "size_bytes": ok["size"],
        "format": os.path.splitext(path)[1].lstrip(".").upper(),
    }

    # Step 3 — attempt pixel-level metadata if Pillow is present.
    if _PIL_OK:
        with Image.open(path) as im:  # type: ignore[arg-type]
            info["width"] = im.width
            info["height"] = im.height
            info["mode"] = im.mode
            # Use Pillow's detected format if available (more reliable than
            # extension guessing for mismatched files).
            info["format"] = (im.format or info["format"]).upper()
    else:
        info["note"] = "Pillow not installed; install `Pillow` for pixel-level metadata."

    return info


# === SECTION: TOOL — LOAD IMAGE ===
# Type: (path: str, max_dim: int = 1024) -> dict
def load_image(path: str, max_dim: int = 1024) -> dict:
    """Load an image, optionally downscale it, and return a base64 preview.

    This is the primary gateway for feeding image data into the LLM's
    multimodal context. When Pillow is installed, the image is decoded,
    resized if necessary, re-encoded, and base64-encoded. Without Pillow,
    raw bytes are read and base64-encoded as a fallback.

    Args:
        path:    Filesystem path to the image file.
        max_dim: Maximum width or height (in pixels) after resizing.
                 Defaults to 1024 to keep previews manageable for LLM context.
                 Set to ``0`` to skip resizing entirely.

    Returns:
        On success, a dict containing:

        - ``status``      : ``"ok"``
        - ``path``        : Absolute filesystem path.
        - ``size_bytes``  : Original file size on disk.
        - ``original``    : Dict with ``width``, ``height``, ``mode`` (Pillow only).
        - ``resized``     : Dict with post-resize ``width`` and ``height`` (Pillow only).
        - ``encoding``    : Always ``"base64"``.
        - ``mime_type``   : MIME string suitable for LLM prompt injection,
                            e.g. ``"image/png"`` or ``"image/jpeg"``.
        - ``data``        : Base64-encoded string of the (possibly resized) image.
        - ``note``        : Present only in fallback mode without Pillow.

        On failure returns an error dict consistent with `_validate_path`.

    Exceptions:
        No exceptions are raised. File I/O errors during the raw-bytes
        fallback path are not explicitly caught — they will propagate
        as standard Python exceptions (e.g., ``PermissionError``).

    Examples:
        >>> load_image("/tmp/photo.jpg")  # doctest: +SKIP
        {'status': 'ok', 'path': '/tmp/photo.jpg', ..., 'data': 'iVBORw0...'}

    TODO (v1.2.0): Support an optional `quality` parameter for JPEG re-encoding
       to reduce base64 payload size further.

    FIXME: GIF and BMP formats may lose transparency or colour depth during
       Pillow-based re-encoding; consider preserving original byte streams
       for those formats.
    """
    # Shared validation — prevents processing nonexistent or disallowed files.
    ok = _validate_path(path)
    if ok["status"] != "ok":
        return ok

    # FALLBACK PATH — Pillow is unavailable; return raw base64 bytes.
    if not _PIL_OK:
        with open(path, "rb") as f:
            data = f.read()
        # Map common extensions to proper MIME types for the LLM.
        mime = f"image/{ok['suffix'].lstrip('.').replace('jpg', 'jpeg')}"
        return {
            "status": "ok",
            "path": os.path.abspath(path),
            "size_bytes": ok["size"],
            "encoding": "base64",
            "mime_type": mime,
            "data": base64.b64encode(data).decode("ascii"),
            "note": "Pillow not installed; returning original bytes without resizing.",
        }

    # PRIMARY PATH — Pillow is available; decode, resize, and re-encode.
    with Image.open(path) as im:  # type: ignore[arg-type]
        # Snapshot original dimensions before any modification.
        original = {"width": im.width, "height": im.height, "mode": im.mode}

        # Resize only if the image exceeds max_dim on its longest side.
        # Using thumbnail() preserves aspect ratio in-place.
        if max_dim and max(im.size) > max_dim:
            im.thumbnail((max_dim, max_dim))

        # Prepare an in-memory buffer for re-encoding.
        buf = io.BytesIO()
        fmt = (im.format or "PNG").upper()

        # Determine the MIME type for downstream consumption.
        mime = "image/png" if fmt == "PNG" else f"image/{fmt.lower()}"

        # JPEG requires RGB mode; RGBA/RGBA-with-alpha must be flattened.
        if fmt == "JPEG" and im.mode != "RGB":
            im = im.convert("RGB")

        # Encode the image into the buffer.
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


# === SECTION: TOOL — DOMINANT COLORS ===
# Type: (path: str, n: int = 5) -> dict
def dominant_colors(path: str, n: int = 5) -> dict:
    """Return the most common colours in an image as hex codes.

    The algorithm works by:
    1. Resizing the image to 128×128 for speed (NOTE: see FIXME below).
    2. Quantising each pixel's RGB channels to 4 bits per channel (16 levels),
       reducing the colour space to 4096 possible bins.
    3. Counting occurrences per bin and returning the top ``n``.

    Args:
        path: Filesystem path to the image file.
        n:    How many dominant colours to return. Defaults to 5.
              Clamped to the range [1, 20] to prevent unreasonable requests.

    Returns:
        A dict with:

        - ``status`` : ``"ok"`` on success, or ``"error"`` if Pillow is missing.
        - ``colors`` : List of ``{"hex": str, "count": int}`` entries,
                       sorted by descending frequency. Each ``hex`` string
                       is in ``"#RRGGBB"`` format.

    Raises:
        No exceptions are raised; errors are returned in the dict.

    Examples:
        >>> dominant_colors("/tmp/landscape.png", n=3)  # doctest: +SKIP
        {'status': 'ok', 'colors': [
            {'hex': '#2A4B8D', 'count': 5231},
            {'hex': '#F5E6D3', 'count': 4112},
            {'hex': '#88CC44', 'count': 3087},
        ]}

    NOTE: The 128×128 resize means small images (e.g., icons < 128px) are
    upscaled, which can artificially blend distinct colours. For icon-sized
    images, results may be less meaningful.

    TODO (v1.2.0): Offer k-means or median-cut quantisation for higher-quality
       palette extraction at the cost of additional computation.
    """
    # Shared validation — ensures file exists and is an allowed image type.
    ok = _validate_path(path)
    if ok["status"] != "ok":
        return ok

    # Pillow is mandatory for pixel-level colour analysis.
    if not _PIL_OK:
        return {
            "status": "error",
            "error": "Pillow is required for color analysis. `pip install Pillow`.",
        }

    # Clamp n to [1, 20] to avoid empty lists or excessive memory usage.
    n = max(1, min(int(n), 20))

    # Decode and downscale for efficient processing.
    with Image.open(path) as im:  # type: ignore[arg-type]
        im = im.convert("RGB").resize((128, 128))
        pixels = list(im.getdata())

    # Count quantised colours using a 12-bit key (4 bits per channel).
    # This groups very similar colours together (e.g., #234567 → #245768 equivalent bin).
    counts: Dict[int, int] = {}
    for r, g, b in pixels:
        key = ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)
        counts[key] = counts.get(key, 0) + 1

    # Sort by frequency descending and take the top n entries.
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]

    # Convert quantised keys back to 8-bit hex strings.
    colors = []
    for key, count in top:
        r = ((key >> 8) & 0xF) * 17   # 17 = 255/15, maps 4-bit → 8-bit
        g = ((key >> 4) & 0xF) * 17
        b = (key & 0xF) * 17
        colors.append({"hex": f"#{r:02X}{g:02X}{b:02X}", "count": count})

    return {"status": "ok", "colors": colors}


# === SECTION: ADK ROOT AGENT ===
# The root_agent is the entry point for ADK sessions. It bundles all three
# tools and configures the multimodal model with a detailed system prompt.
# Type: Agent
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

# === END OF MODULE ===