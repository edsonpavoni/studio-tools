# PT-Transcriber

> ⚠️ **`transcripts/` is gitignored and must stay that way.** Transcripts, caches, and hand-verification notes routinely contain private conversations; they live only on the machine that made them. Hand-verification notes are human work and cannot be regenerated — never delete a `.cache/` you have annotated.

Turns WhatsApp voice notes (`.opus`) in Brazilian Portuguese into a single Markdown transcript, with the date, time and speaker of each audio.

Everything runs locally on the Mac's GPU (MLX). No audio leaves the machine, no API key, no cost per minute.

## Setup (already done, here for the record)

The Python environment lives outside Dropbox so it does not get synced:

```bash
uv venv ~/.venvs/pt-transcriber --python 3.12
VIRTUAL_ENV=$HOME/.venvs/pt-transcriber uv pip install mlx-whisper
```

`ffmpeg` is also required and is already installed via Homebrew.

## Use

Export a chat from WhatsApp with "Attach Media", unzip it, then point the script at the unzipped folder:

```bash
cd "/Users/edsonpavoni/Library/CloudStorage/Dropbox/0000 AI/tools/PT-Transcriber"
~/.venvs/pt-transcriber/bin/python transcribe.py "/path/to/WhatsApp Chat - Someone"
```

The result lands in `transcripts/<folder name>.md`.

**Put the transcript next to the audio it describes.** If the recordings are filed somewhere as evidence or archive, point the script at that folder and write the output into it:

```bash
~/.venvs/pt-transcriber/bin/python transcribe.py "/path/to/case/11-whatsapp-someone" \
  --out "/path/to/case/11-whatsapp-someone/TRANSCRICOES.md" \
  --title "Transcrições dos áudios" \
  --ui pt
```

A transcript that lives away from its audio drifts from it. The script finds the chat log even when it has been renamed from `_chat.txt`.

Useful flags:

| Flag | What it does |
|---|---|
| `--out PATH` | Write the Markdown somewhere else |
| `--title TEXT` | Set the document's H1 (default: the folder name) |
| `--ui pt` | Write the document's own text in Portuguese (default `en`). Does not touch the transcription, only headings, labels and the accuracy section. Use it when the transcript is filed among Portuguese documents or will be read by someone who works in Portuguese. |
| `--limit N` | Only the first N audios, for a quick test |
| `--only FILE.opus` | Only one audio |
| `--language en` | Another language (default `pt`) |
| `--model REPO` | Another Whisper model |
| `--force` | Re-transcribe even if cached |

## How it works

1. Reads `_chat.txt` from the export and builds a map of audio filename to speaker and timestamp. **Speaker attribution comes only from the chat log.** If an audio has no matching line, the speaker is written as `UNKNOWN` rather than guessed.
2. Gets each audio's duration with `ffprobe`.
3. Transcribes with `mlx-community/whisper-large-v3-mlx`, forced to Portuguese, seeded with the domain vocabulary prompt (see below) so proper nouns and jargon come out right.
4. Writes one Markdown file grouped by day, each entry carrying its source `.opus` filename and duration so any sentence can be traced back to the audio in one step.

Results are cached one JSON per audio in `transcripts/.cache/`, so re-running only processes new audio.

## Accuracy notes

The transcripts are machine-generated and nobody has listened to them. Whisper fails in two opposite directions, and the script guards against both:

- **It invents.** On trailing silence it can loop and repeat a fabricated sentence. Guarded by `condition_on_previous_text=False`, so a bad segment cannot contaminate the ones after it, plus a check for an implausible words-per-second rate or three identical consecutive segments.
- **It stops early.** At a voice-activity boundary it can quietly drop the rest of a recording. This is the dangerous one, because a truncated transcript looks perfectly fine. Guarded by comparing the last transcribed segment's end time against the real audio duration from `ffprobe`, and flagging any gap over 3 seconds.

Flagged audios get a **CHECK THIS AUDIO** warning inline in the Markdown.

Once you have listened to a flagged audio, record what you found in `transcripts/.cache/<chat>-notes.json`, a flat `{"filename.opus": "what you verified"}` map. It renders as a **Checked by hand** note under the entry and survives a `--force` re-run, so nobody redoes the check. The note is copied through verbatim, so write it in the same language as the document (`--ui`).

Flags are cached as codes rather than sentences, so the same transcription renders in either language without re-running Whisper.

Numbers, dates and monetary values are the least reliable part of any Whisper transcript. Listen to the source before quoting one.

## Who is speaking

Speaker names come from `_chat.txt` and nowhere else. If an audio has no matching line in the chat log, the speaker is written `UNKNOWN` rather than guessed.

WhatsApp puts a `~` before a sender's name when that name is the account's own profile name rather than a contact saved on this phone. The script keeps that distinction: those names appear in quotes in the Markdown, and the header spells out that the name is self-set and not a verified identity. The phone number in the folder name is the actual identifier.

## Changing the vocabulary prompt

Whisper biases toward vocabulary given in its initial prompt, and it measurably improves proper-noun accuracy. Put your domain terms — names, companies, jargon — in a `vocab.txt` next to `transcribe.py`, one phrase or comma-separated list per line. The file is gitignored, so private vocabulary (people's names, case terms) never leaves your machine. Without it the prompt is just "Conversa em portugues do Brasil."

## A faster, slightly less accurate model

For casual transcription where accuracy matters less, `mlx-community/whisper-large-v3-turbo` runs roughly 5x faster:

```bash
~/.venvs/pt-transcriber/bin/python transcribe.py "/path/to/folder" --model mlx-community/whisper-large-v3-turbo
```

## Not included

Speaker diarization (who is speaking inside a single recording). WhatsApp voice notes are one speaker each and the chat log already says who, so it is not needed here. A group recording or a meeting would need WhisperX or pyannote on top.
