# heic2jpg

Converts iPhone HEIC photos to JPG locally, so Claude Code never spends tokens figuring out how to open one. Uses macOS's built-in `sips` — no dependencies, nothing leaves the Mac, the original HEIC is untouched.

## How it's wired

A `UserPromptSubmit` hook in `~/.claude/settings.json` runs `heic2jpg.py` on every prompt, before the model sees anything. If the prompt contains a path to an existing `.heic` file (dragged into the terminal, quoted, or @-mentioned), the script converts it to a `.jpg` next to the original and injects one line of context telling Claude to read the JPG instead. Prompts with no HEIC cost nothing and print nothing.

Re-sending the same HEIC is free: if the JPG already exists and is newer than the HEIC, it's reused.

## Standalone use

```
./heic2jpg.py photo.heic [more.heic ...]
```

Prints the JPG path(s). Two knobs at the top of the script:

- `QUALITY` (85) — JPEG quality percent. Affects file size only, never token cost.
- `MAX_DIM` (1568) — long-edge pixel cap. Claude's API downscales anything larger to ~1568 px before the model sees it, so 1568 loses nothing versus sending the 12 MP original. Image tokens ≈ width × height / 750, so lowering this to ~1024 cuts a photo from ~1,600 to ~1,000 tokens if maximum detail isn't needed. Images already smaller than the cap are never upscaled.

## Uninstall

Remove the heic2jpg entry from `hooks.UserPromptSubmit` in `~/.claude/settings.json`.
