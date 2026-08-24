#!/usr/bin/env python3
"""heic2jpg — convert HEIC to JPG locally, zero tokens.

Two modes:
  CLI:   heic2jpg.py photo.heic [more.heic ...]   → writes photo.jpg next to each
  Hook:  no args, reads Claude Code UserPromptSubmit JSON on stdin,
         finds .heic paths in the prompt, converts them, and prints a
         one-line context note telling Claude which .jpg to read instead.

Conversion is done with macOS's built-in `sips` — no dependencies.
The .heic original is never modified or deleted.
"""
import json
import os
import re
import subprocess
import sys

QUALITY = "85"  # formatOptions percent for sips
# Claude's API downscales images to ~1568px on the long edge before the model
# sees them, so anything larger is upload weight with zero extra detail.
# Lower to ~1024 to trade some detail for ~35% fewer image tokens.
MAX_DIM = 1568


def convert(heic_path):
    """Convert one HEIC file to JPG next to it. Returns jpg path or None."""
    jpg_path = os.path.splitext(heic_path)[0] + ".jpg"
    if os.path.exists(jpg_path) and os.path.getmtime(jpg_path) >= os.path.getmtime(heic_path):
        return jpg_path  # already converted
    cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", QUALITY]
    if _long_edge(heic_path) > MAX_DIM:  # never upscale small images
        cmd += ["--resampleHeightWidthMax", str(MAX_DIM)]
    result = subprocess.run(cmd + [heic_path, "--out", jpg_path], capture_output=True)
    return jpg_path if result.returncode == 0 else None


def _long_edge(path):
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
        capture_output=True, text=True,
    )
    dims = [int(m) for m in re.findall(r"pixel(?:Width|Height): (\d+)", result.stdout)]
    return max(dims) if dims else 0


def find_heic_paths(text):
    """Extract existing .heic file paths from prompt text.

    Handles terminal drag-and-drop escaping (backslash-space), quoted
    paths, and @-mentions.
    """
    candidates = set()
    # Quoted paths: '...' or "..."
    for m in re.finditer(r"""['"]([^'"]+?\.heic)['"]""", text, re.IGNORECASE):
        candidates.add(m.group(1))
    # Unquoted, possibly backslash-escaped: take runs of non-whitespace
    # (allowing escaped spaces) ending in .heic
    for m in re.finditer(r"((?:\\.|\S)+?\.heic)\b", text, re.IGNORECASE):
        raw = m.group(1).lstrip("@")
        candidates.add(re.sub(r"\\(.)", r"\1", raw))  # unescape \  \( etc.
    return [p for p in candidates if os.path.isfile(os.path.expanduser(p))]


def main():
    if len(sys.argv) > 1:  # CLI mode
        ok = True
        for path in sys.argv[1:]:
            jpg = convert(os.path.expanduser(path))
            if jpg:
                print(jpg)
            else:
                print(f"failed: {path}", file=sys.stderr)
                ok = False
        sys.exit(0 if ok else 1)

    # Hook mode: UserPromptSubmit JSON on stdin
    try:
        prompt = json.load(sys.stdin).get("prompt", "")
    except Exception:
        sys.exit(0)
    heics = find_heic_paths(prompt)
    if not heics:
        sys.exit(0)
    converted = [(h, convert(os.path.expanduser(h))) for h in heics]
    lines = []
    for heic, jpg in converted:
        if jpg:
            lines.append(f"HEIC already converted locally: read {jpg} instead of {heic}. Do not attempt to convert it yourself.")
        else:
            lines.append(f"Local HEIC conversion failed for {heic} (sips error).")
    print("\n".join(lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
