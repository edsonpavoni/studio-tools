# tools/

Reusable tools. Not projects, not artworks. If a thing gets used again on a different job, it belongs here.

**Created 2026-08-12.** Everything here runs locally. No API keys, no per-minute cost, and **no audio or document ever leaves the machine**, which is the point when the material is a private creative session, a legal case, or an unreleased artwork.

---

## Audio transcription

Two tools, and they answer different questions.

### 1. PT-Transcriber → `tools/PT-Transcriber/`
**Use when:** you have a whole WhatsApp chat export full of voice notes, in Portuguese, and you need one Markdown transcript with dates, times and who said what.

It reads `_chat.txt` to attribute speakers, so it needs a real WhatsApp export folder, not a loose file. Speaker names come from the chat log and nowhere else; an audio with no matching line is written `UNKNOWN` rather than guessed. Runs on MLX (Apple GPU) with `whisper-large-v3-mlx`, caches per audio, and flags recordings where Whisper may have invented or truncated content.

```bash
cd "/Users/edsonpavoni/Library/CloudStorage/Dropbox/0000 AI/tools/PT-Transcriber"
~/.venvs/pt-transcriber/bin/python transcribe.py "/path/to/WhatsApp Chat - Someone" --ui pt
```

Full flags, accuracy notes and the vocabulary-prompt explanation are in its own README. **Read the accuracy section before quoting any number, date or monetary value.**

Python env lives at `~/.venvs/pt-transcriber` (outside Dropbox on purpose, so it does not sync).

### 2. whisper.cpp → single files, any language
**Use when:** you have one audio or video file and just need the words. Interviews, creative sessions, voice memos, meeting recordings.

Installed 2026-08-12 via Homebrew. Model at `~/.cache/whisper-models/ggml-large-v3-turbo.bin` (1.5 GB).

```bash
# convert to 16 kHz mono wav first (whisper.cpp needs this)
ffmpeg -y -i "input.m4a" -ar 16000 -ac 1 -c:a pcm_s16le out.wav

# transcribe: -otxt plain text, -ovtt timecoded captions
whisper-cli -m ~/.cache/whisper-models/ggml-large-v3-turbo.bin \
  -f out.wav -l en -otxt -ovtt -of output-basename -pp
```

Use `-l pt` for Portuguese, `-l auto` to detect. Roughly 35x realtime on this Mac: a 9-minute recording took about 16 seconds.

### ⚠️ Neither tool separates speakers inside one recording
Whisper transcribes words, not voices. For a two-person conversation in a single file, **any speaker label is inference and must be marked as such.** Label only lines that are unambiguous from content, leave the rest unattributed, and never quote an attributed line publicly without checking the audio. Diarization would need WhisperX or pyannote on top; not installed.

### Working rule: the transcript lives next to its audio
A transcript filed away from its source drifts from it. Write the output into the same folder as the recording, and keep the `.vtt` alongside the `.md` so any sentence can be traced back to a timecode in one step.

---

## Making circuit boards

### PCB-Maker → `tools/PCB-Maker/` · git: https://github.com/edsonpavoni/pcb-maker (private)
**Use when:** a sculpture needs a board and the fab house's shipping date does not fit. tscircuit source → hand-routed artwork on the iPad → one LightBurn file for the ComMarker B6 MOPA, so a board can be made in the studio on a Tuesday — and the traces are a drawing.

**Status v0.1 (2026-08-24): proven end to end.** V4 (The Source P1b) cut with a fully
measured recipe: every laser number came off a coupon and lives in `B6-PCB-RECIPE.md`
and the converter defaults, not in anyone's memory. Start at `README.md`; open work
in `BACKLOG.md`; history in `PLAN.md`. The Gerber route (`gerber2lbrn.py`, pcb2gcode)
exists for boards from Flux/KiCad.

---

## Images

### heic2jpg → `tools/heic2jpg/`
**Use when:** an iPhone photo needs to reach Claude Code. It runs automatically — a `UserPromptSubmit` hook in `~/.claude/settings.json` converts any `.heic` path dragged into the terminal to a `.jpg` next to the original (macOS `sips`, no dependencies, zero tokens spent on figuring it out) and tells Claude to read the JPG. Also works standalone: `./heic2jpg.py photo.heic`. Details and uninstall in its README.

---

## Adding a tool here

One folder per tool, each with its own README covering: what it is for, how to run it, where its Python env or models live, and how it fails. Keep environments and large models **outside** Dropbox (`~/.venvs/`, `~/.cache/`) so they never sync.
