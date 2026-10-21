# studio/

**Type `/tools` in Claude Code** to see every tool here (each folder is one, shown with its own emoji) and start the one you pick. 🔴 **That command holds the list itself, so it answers instantly. Whenever a tool folder is added, renamed or removed here, update the list in `.claude/commands/tools.md` in the same turn.**

Reusable tools. Not projects, not artworks. If a thing gets used again on a different job, it belongs here.

**Created 2026-08-12.** Everything here runs locally. No API keys, no per-minute cost, and **no audio or document ever leaves the machine**, which is the point when the material is a private creative session, a legal case, or an unreleased artwork.

---

## Audio transcription

Two tools (the first has two modes), and they answer different questions.

### 1. PT-Transcriber → `studio/PT-Transcriber/`
**Use when:** you have a whole WhatsApp chat export full of voice notes, in Portuguese, and you need one Markdown transcript with dates, times and who said what.

It reads `_chat.txt` to attribute speakers, so it needs a real WhatsApp export folder, not a loose file. Speaker names come from the chat log and nowhere else; an audio with no matching line is written `UNKNOWN` rather than guessed. Runs on MLX (Apple GPU) with `whisper-large-v3-mlx`, caches per audio, and flags recordings where Whisper may have invented or truncated content.

```bash
cd "/Users/edsonpavoni/Library/CloudStorage/Dropbox/0000 AI/studio/PT-Transcriber"
~/.venvs/pt-transcriber/bin/python transcribe.py "/path/to/WhatsApp Chat - Someone" --ui pt
```

Full flags, accuracy notes and the vocabulary-prompt explanation are in its own README. **Read the accuracy section before quoting any number, date or monetary value.**

Python env lives at `~/.venvs/pt-transcriber` (outside Dropbox on purpose, so it does not sync).

### 1b. PT-Transcriber `session.py` → loose recordings, cleaned first
**Use when:** a meeting or working session recorded on the DJI mic or a phone, one or several files, Portuguese with some English. It fixes level and noise before transcribing (quiet field recordings are where Whisper drops words), writes one timecoded `TRANSCRIPT.md` + `.vtt`, and keeps a small cleaned `.m4a` per file. Details in `PT-Transcriber/README.md`.

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

### trilha → `studio/trilha/`
*(named PCB-Maker until 2026-08-25)*
**Use when:** a sculpture needs a board and the fab house's shipping date does not fit. tscircuit source → hand-routed artwork on the iPad → one LightBurn file for the ComMarker B6 MOPA, so a board can be made in the studio on a Tuesday — and the traces are a drawing. The board's routing saves as a `.handroute` file next to its circuit.json.

**Status v0.1 (2026-08-24): proven end to end.** V4 (The Source P1b) cut with a fully
measured recipe: every laser number came off a coupon and lives in `B6-PCB-RECIPE.md`
and the converter defaults, not in anyone's memory. Start at `README.md`; open work
in `BACKLOG.md`; history in `PLAN.md`. The Gerber route (`gerber2lbrn.py`, pcb2gcode)
exists for boards from Flux/KiCad.

---

## iPad

### ipad → `studio/ipad/`
**Use when:** you pick up the iPad to draw or route a board and want it to just work. One app on the Mac (`~/Applications/iPadTools.app`, LaunchAgent `art.edsonpavoni.ipad`) runs every iPad tool from login, restarts what dies, and serves a hub page of tiles: **http://edsons-macbook-pro.local:8888** (rascunho 8880, trilha 8481). `tools.json` is the registry; adding an iPad tool is one entry there. It is an app bundle because macOS gates Dropbox per app and a plain launchd `zsh`/`python3` job is never allowed in. *(Built 2026-10-20; details, checks, undo in its README.)*

## Images

### heic2jpg → `studio/heic2jpg/`
**Use when:** an iPhone photo needs to reach Claude Code. It runs automatically — a `UserPromptSubmit` hook in `~/.claude/settings.json` converts any `.heic` path dragged into the terminal to a `.jpg` next to the original (macOS `sips`, no dependencies, zero tokens spent on figuring it out) and tells Claude to read the JPG. Also works standalone: `./heic2jpg.py photo.heic`. Details and uninstall in its README.

### photo-picker → `studio/photo-picker/`
**Use when:** choosing photos of the works for a grant, the press kit, a website, Instagram or a cover. One grid of every PR photo (Orbital Witnesses, Orbital Temple, Birth of a Temple, Inumeráveis; 1,445 on 2026-10-10), rated with stars, favorites, rejects, tags, notes and works (a photo can show several artworks), filtered and grouped by work, event, photographer, year, culled one by one ("Rate unrated"), sorted into ordered *moments* (Press kit, BAC work samples, orbitaltemple.art…) and exported as full paths + credits. `studio/photo-picker/serve.sh` → **http://127.0.0.1:8801**. Sources are the `SOURCE_ROOTS` list at the top of `server.py`; ratings live in `state.json`; thumbnails in `.cache/` (not synced). Details in its README. *(2026-10-10.)*

### grantHunter → `studio/grantHunter/`
**Use when:** it is Monday and MrGrants needs the week's new grant calls. launchd runs `run.sh` every **Monday 07:00**: Crawl4AI (local) reads 14 listing pages (ArtConnect, deadlinecalls, Colossal, NYFA, e-flux, ResArtis…) and diffs ~60 official pages we watch (Eyebeam, Creative Capital, LACMA Lab, Watermill…), remembers every item seen, drops the blocklist, and writes `runs/<date>/digest.md`. Then **`/grantHunter`** in Claude Code: filters by `PROFILE.md`, verifies on the official pages, writes `proposals/grants/hunts/<date>_hunt.md`. Browse runs: `studio/grantHunter/serve.sh` → **http://127.0.0.1:8802**. Instagram stays manual (screenshots into the Monday session). *(Built 2026-10-12; plan and build log in `PLAN.md`.)*

### claude-shot → `studio/claude-shot/`
**Use when:** a screenshot is meant for a Claude Code session. **Ctrl+Opt+Cmd+4** → drag an area → the PNG lands in `studio/claude-shot/shots/` (kept as history) and its path is pasted into the session that was in front, so Claude gets a real file instead of the thumbnail's vanishing temp file. Background app run by launchd; rebuilding it resets its macOS permissions. Details, install and undo in its README. *(2026-10-09, replaced `/shot`.)*

---

## Drawing

### rascunho → `studio/rascunho/`
**Use when:** you want to draw on the iPad with the Pencil, graphite-on-paper feel (Pencil draws, one finger smudges, two fingers pan and zoom), and hand the drawing to a Claude Code session by the session's name; or a session wants to put a picture on the iPad for you to draw over. One web page served from the Mac over the studio Wi-Fi (`studio/rascunho/serve.sh` → **http://localhost:8880**, iPad: `http://edsons-macbook-pro.local:8880`, add to Home Screen for a full-screen icon), a Python stdlib server, and our own open-source graphite engine (`studio/rascunho/graphite/`, MIT; the feel of *8bitpaint pencil*, studied, not copied). Drawings are PNG tiles in `sheets/`; sends land in the session through its inbox socket and `/rascunho` gives every session `latest`, `list`, `reply` and `place`. Start at its README. *(Built 2026-10-20.)*

---

## Studio equipment

### equipment → `studio/equipment/`
**Use when:** you need to know what Edson owns in the studio or how he uses it: camera + lenses, 3D printer, B6 MOPA, mini lathe, projector, Witness electronics and spares, travel router. **Check it before asking Edson what he owns.**

`README.md` is the index (device · model · what it's for · status · file); one file per device with specs, dated settings and their sources, how-tos, gotchas, spares and ❓ questions for Edson. Machines with their own toolchain (B6, instrument) keep their folders and get a short card there. *(Created 2026-10-02.)*

---

## Cutting and engraving metal

### B6 MOPA → `studio/B6-Mopa/`
**Use when:** anything goes on the ComMarker B6 MOPA fiber laser — cutting sheet metal, engraving lids, the rotary.

🔴 **`studio/B6-Mopa/` is the source of truth for this machine.** `MATERIAL-SETTINGS.md` holds every measured recipe by material and thickness — copper, brass, aluminium and stainless 304 — with the breakthrough pass counts and what was tried and failed. `R5-ROTARY.md` covers the rotary attachment. PCB work stays with its own toolchain in `trilha/`.

**Rules that keep it honest:** dial in on scrap, set production ~20 % above breakthrough, record the number, mark it LOCKED. A recipe without a thickness is not a recipe. *(Consolidated here 2026-09-21 from `projects/B6 Mopa Laser/`.)*

---

## Audiovisual instrument

### av-studio → `studio/av-studio/`
**Use when:** making or judging visuals for the SOURCE instrument / Birth of a Temple — scenes played by the two theremin hands, answering sound and sending MIDI. **Candidate default tool for Edson's AV work (2026-09-24).**

Two halves: `source-scenes/` is a copy of the group's git repo (shared through git — the live clone is `~/projects/source-scenes`; build and push from ONE place), and `pAVoni/` is ours and private — `STYLE-DIRECTION.md`, `INSTRUMENT.md` (the Source law: near = less, far = more), `INSIGHTS.md`, `LOOK-DEV.md` (technical playbook), `references/`. Claude loads it all via the `av-visuals` skill. Start at `studio/av-studio/README.md`.

### instrument → `studio/instrument/`
**Use when:** anything about the physical instrument itself (AV Theremin, Visual Theremin, The Source, the v1): firmware, flashing, sensors, motors, boards, settings, versions, the v1 plan. Visuals belong to av-studio above; the instrument is what the hands play.

Every version lives in `versions/` (with a README per version and flashable binaries in `versions/_binaries/`), the docs in `docs/`, the v1 plan in `plan/V1-PLAN.md`, the lab notebook in `explorations/`, show logs in `logs/`. Settings over USB: `studio/instrument/tools/serve.sh` → http://127.0.0.1:8795 (stop it before flashing: it holds the serial port). Start at `studio/instrument/README.md`.

### voice → `studio/voice/`
**Use when:** something should be said out loud to Edson. MsCurator is the only voice (the Oracle, cloned in local Voicebox); every other session sends her its news and she filters and bundles it. A Claude Code hook speaks her lines that start with 🔊. Start at `studio/voice/README.md`.

---

## Adding a tool here

One folder per tool, each with its own README covering: what it is for, how to run it, where its Python env or models live, and how it fails. Keep environments and large models **outside** Dropbox (`~/.venvs/`, `~/.cache/`) so they never sync.

---

## Project tools — `<project>/tools/`

**Convention (Edson, 2026-09-26).** A tool made *for one project* (a day timer, a live status page, a checklist) does not go here. It goes in a **`studio/` folder inside that project**, created the first time a tool is made there. Each one has:

- `README.md`: the list of that project's studio (what it is for, how to run it, its URL). **This is the check-before-you-build list.**
- `index.html`: a hub page linking to every tool of the project.
- `serve.sh`: starts one local server rooted in that `studio/` folder, plus any Python live pages. Running it twice is harmless.

**Before building any tool: read this section, then that project's `studio/README.md`, then the list above.** If something close exists, extend it instead of building a new one.

**When a tool is made:** save it in `<project>/tools/`, add a line to its README and a card to `index.html` in the same turn. For a new project, also add a row below.

| Project | Tools folder | Hub | Ports |
|---|---|---|---|
| First Witness series | `artworks/orbital-witnesses/tools/` | http://localhost:8777 | 8777 hub · 8788 base (8787 retired Sep 27, fleet_page.py deleted — base page replaces it) |
| Orbital Temple launch | `exhibitions/birth-of-a-temple/tools/` | http://127.0.0.1:8791 | 8791 hub + run of show |
| Instrument (AV Theremin) | `studio/instrument/tools/` | http://127.0.0.1:8795 | 8795 settings over USB (Source page, no WiFi) |
| Felix (Brian, commercial) | `commercial/felix/tools/` | http://127.0.0.1:8480 | 8480 hub + feel test · 8478 Felix Flasher (LaunchAgent) |
| Photo Picker (cross-project, `studio/` tool) | `studio/photo-picker/` | http://127.0.0.1:8801 | 8801 grid + API (`serve.sh`) |
| 2026 OKRs glance (`system/` tool) | `system/plans/tools/` | http://localhost:8810 | 8810 page + `okrs.json` (`serve.sh`) |
| Bambu P2S printing (`studio/equipment/` tool) | `studio/equipment/tools/p2s/` | none (CLI `p2s.py` + `/print`) | none · printer 192.168.204.181 (8883 MQTT, 990 FTPS, 322 camera) |
| rascunho, iPad graphite → Claude Code (`studio/` tool) | `studio/rascunho/` | http://localhost:8880 | 8880 page + API (always on via `studio/ipad`; iPad: `http://edsons-macbook-pro.local:8880`) |
| iPad tools hub + runner (`studio/` tool) | `studio/ipad/` | http://localhost:8888 | 8888 hub · runs rascunho 8880 and trilha 8481 from login (`install.sh`, LaunchAgent) |
| Orbital Temple, 12 artists deck v2 (Oct 16) | `artworks/orbital-temple/orbital-temple-chapel/deck/v2-2026-10-16/` | http://localhost:8816 | 8816 6-page deck (`index.html`) → PDF `Orbital-Temple-12-Artists-v2-2026-10-16.pdf` (`serve.sh`) |
| Failing Spectacularly study (report + notes) | `artworks/_studies/failing-spectacularly/tools/` | http://localhost:8840/tools/ | 8840 hub, pandoc-rendered pages (`serve.sh`) |
| Brazil Vegan Core deck (Vegan Trouble NY dinner) | `commercial/vegan-trouble/ny-event-oct-2026/presentation/` | http://127.0.0.1:8812 | 8812 deck · `/?presenter` notes + timer (`serve.sh`) |
| Vegan Trouble website draft (home + Brazil × US report) | `commercial/vegan-trouble/website/` | http://127.0.0.1:8813 | 8813 static (`serve.sh`) |
| Sunrise/Sunset (ribbon simulator v1 + v2 no-crossing, progress pages) | `artworks/sunrise-sunset/tools/` | http://localhost:8822/tools/ | 8822 static, rooted at `artworks/sunrise-sunset/` (`serve.sh`) |

**Ports in use (pick a free one for a new project):** 8765 av-studio · 8777 / 8788 First Witness · 8791 Orbital Temple launch · 8795 Instrument · 8480 Felix tools · 8478 Felix Flasher · 8801 Photo Picker · 8802 grantHunter · 8812 Brazil Vegan Core deck · 8813 Vegan Trouble website · 8840 Failing Spectacularly study · 8850 Grants files (`proposals/grants/tools/serve.sh`) · 8880 rascunho · 8481 trilha · 8888 iPad hub (`studio/ipad`).
