#!/usr/bin/env python3
"""
PT-Transcriber
Transcribes WhatsApp .opus voice notes (Brazilian Portuguese) into a single
Markdown file, with date, time and sender taken from the chat export.

Usage:
    ~/.venvs/pt-transcriber/bin/python transcribe.py "<chat export folder>" [options]

Options:
    --out PATH        Output .md path (default: transcripts/<folder name>.md)
    --title TEXT      H1 for the document (default: the folder name)
    --ui pt|en        Language of the document's own text (default: en).
                      Does not affect the transcription, only the headings,
                      labels and the accuracy section.
    --model REPO      MLX Whisper repo (default: mlx-community/whisper-large-v3-mlx)
    --language CODE   Spoken language of the audio (default: pt)
    --limit N         Only process the first N audio files (for a test run)
    --only NAME       Only process this exact filename (for a test run)
    --force           Re-transcribe even if a cached result exists

Transcripts are cached one JSON per audio file under transcripts/.cache/, so a
re-run only processes new audio.
"""

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

# WhatsApp exports are full of bidi / invisible marks. Strip them before regexing.
INVISIBLE = dict.fromkeys(
    [0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0xFEFF]
)

# Domain vocabulary. Whisper uses this to bias proper nouns and jargon.
# Put case- or project-specific terms (names, companies, jargon) in a
# vocab.txt next to this script — one phrase or a comma-separated list per
# line. vocab.txt is gitignored, so private vocabulary never leaves the repo.
_VOCAB_FILE = Path(__file__).resolve().parent / "vocab.txt"
INITIAL_PROMPT = "Conversa em portugues do Brasil."
if _VOCAB_FILE.exists():
    _terms = ", ".join(
        line.strip() for line in _VOCAB_FILE.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    if _terms:
        INITIAL_PROMPT += " Termos: " + _terms + "."

CHAT_LINE = re.compile(
    r"^\[(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),\s*(?P<time>[\d:]+\s*[APM]*)\]\s*"
    r"(?P<sender>[^:]+):\s*<attached:\s*(?P<file>[^>]+)>"
)
ANY_LINE = re.compile(r"^\[(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),")
OMITTED = re.compile(r"\b(omitted|omitida|omitido)\b", re.I)
FNAME_DT = re.compile(r"AUDIO-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})")

WEEKDAYS_PT = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
MONTHS_PT = [
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

TRUNCATION_TOLERANCE = 3.0  # seconds of unaccounted audio before we complain


def clean(s: str) -> str:
    return unicodedata.normalize("NFC", s.translate(INVISIBLE)).strip()


def num(x: float, places: int, ui: str) -> str:
    """Portuguese writes decimals with a comma."""
    s = f"{x:.{places}f}"
    return s.replace(".", ",") if ui == "pt" else s


def find_chat_log(folder: Path):
    """WhatsApp names it `_chat.txt`, but a folder that has been filed away
    somewhere often has it renamed. Fall back to any .txt whose first lines
    look like a WhatsApp chat log."""
    direct = folder / "_chat.txt"
    if direct.exists():
        return direct
    for cand in sorted(folder.glob("*.txt")):
        head = clean(cand.read_text(encoding="utf-8", errors="replace")[:4000])
        if any(ANY_LINE.match(line) for line in head.splitlines()[:20]):
            return cand
    return direct  # does not exist; callers handle that


def parse_chat(chat_path: Path) -> dict:
    """Map attachment filename -> {sender, datetime}. Attribution comes from
    the chat log only. A file with no matching line stays UNKNOWN.

    WhatsApp prefixes a sender with "~" when the name is the sender's own
    profile name rather than a contact saved on this phone. That distinction
    is kept, because a self-set name is a claim, not a verified identity."""
    meta = {}
    if not chat_path.exists():
        return meta
    for raw in chat_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = clean(raw)
        m = CHAT_LINE.match(line)
        if not m:
            continue
        stamp = None
        for fmt in ("%m/%d/%y %I:%M:%S %p", "%m/%d/%Y %I:%M:%S %p",
                    "%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
            try:
                stamp = datetime.strptime(f"{m['date']} {m['time']}", fmt)
                break
            except ValueError:
                continue
        raw_sender = clean(m["sender"])
        meta[clean(m["file"])] = {
            "sender": raw_sender.lstrip("~").strip(),
            "saved_contact": not raw_sender.startswith("~"),
            "datetime": stamp,
            "source": "chat log",
        }
    return meta


def chat_span(chat_path: Path) -> dict:
    """What the export actually contains, so the transcript can state its own
    limits. A reader needs to tell 'the audio stopped here' apart from 'the
    conversation stopped here', and 'this is every voice note' apart from
    'this is every voice note WhatsApp chose to include'."""
    if not chat_path.exists():
        return {}
    src = chat_path.parent
    dates, omitted, referenced, missing = [], 0, 0, []
    for raw in chat_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = clean(raw)
        m = ANY_LINE.match(line)
        if not m:
            continue
        for fmt in ("%m/%d/%y", "%m/%d/%Y"):
            try:
                dates.append(datetime.strptime(m["date"], fmt).date())
                break
            except ValueError:
                continue
        if OMITTED.search(line):
            omitted += 1
        att = re.search(r"<attached:\s*([^>]+)>", line)
        if att and att.group(1).strip().endswith(".opus"):
            referenced += 1
            if not (src / att.group(1).strip()).exists():
                missing.append(att.group(1).strip())
    if not dates:
        return {}
    return {
        "first": min(dates),
        "last": max(dates),
        "omitted": omitted,
        "referenced_audio": referenced,
        "missing_audio": missing,
    }


def datetime_from_name(name: str):
    m = FNAME_DT.search(name)
    if not m:
        return None
    return datetime(*(int(g) for g in m.groups()))


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def flags_for(text: str, segments: list, seconds: float) -> list:
    """Automatic quality checks. Two failure modes matter, in opposite
    directions: Whisper can loop on trailing silence and invent sentences, and
    it can stop early at a voice-activity boundary and silently drop the rest
    of the recording. The second one is the dangerous one, because a truncated
    transcript looks perfectly fine. Flagged files need a human listen before
    anything is quoted from them.

    Flags are stored as codes plus numbers, not as sentences, so the same
    cached result can be written out in either language."""
    notes = []
    words = len(text.split())
    if seconds > 0:
        wps = words / seconds
        if wps > 3.5:
            notes.append({"code": "fast", "wps": round(wps, 1)})
        if words < 2 and seconds > 5:
            notes.append({"code": "silent"})

    texts = [clean(s.get("text", "")) for s in segments]
    texts = [t for t in texts if t]
    if len(texts) >= 3:
        for i in range(len(texts) - 2):
            if texts[i] == texts[i + 1] == texts[i + 2]:
                notes.append({"code": "loop"})
                break

    # Coverage: did transcription reach the end of the audio?
    last_end = max((float(s.get("end", 0)) for s in segments), default=0.0)
    if seconds > 0 and (seconds - last_end) > TRUNCATION_TOLERANCE:
        notes.append({"code": "truncated", "end": last_end,
                      "dur": seconds, "gap": seconds - last_end})
    return notes


def render_flag(f, ui: str) -> str:
    if isinstance(f, str):  # cache written before flags became structured
        return f
    c = f.get("code")
    if ui == "pt":
        if c == "fast":
            return (f"velocidade implausível ({num(f['wps'], 1, ui)} palavras/s), "
                    "pode ser repetição em loop")
        if c == "silent":
            return "quase nenhum texto para um áudio longo, conferir manualmente"
        if c == "loop":
            return "três segmentos idênticos seguidos, provável alucinação em loop"
        if c == "truncated":
            gap = f.get("gap", f["dur"] - f["end"])
            return (f"a transcrição para em {f['end']:.0f}s de {f['dur']:.0f}s, "
                    f"{num(gap, 1, ui)}s sem cobertura, pode estar truncada")
        return str(f)
    if c == "fast":
        return f"unusually fast ({f['wps']} words/sec), possible looping"
    if c == "silent":
        return "almost no text for a long audio, check manually"
    if c == "loop":
        return "three identical consecutive segments, likely hallucination loop"
    if c == "truncated":
        gap = f.get("gap", f["dur"] - f["end"])
        return (f"transcript stops at {f['end']:.0f}s of {f['dur']:.0f}s, "
                f"{gap:.1f}s unaccounted for, possible truncation")
    return str(f)


# Short labels used around each entry and in the header block.
LABELS = {
    "en": {
        "default_title": "Audio transcripts: {name}",
        "source_folder": "Source folder",
        "transcribed": "Audios transcribed",
        "minutes": "minutes",
        "speakers": "Speakers",
        "model": "Model",
        "language": "language",
        "generated": "Generated",
        "unknown": "UNKNOWN",
        "unknown_note": "UNKNOWN (no matching line in the chat log)",
        "saved": "{name} (contact saved on this phone)",
        "selfset": '"{name}" (name self-set in WhatsApp by the other number, '
                   "not a saved contact)",
        "banner": "> Machine transcription, not verified by a human. Listen to the "
                  "source audio before quoting anything, especially numbers. Read "
                  "**Accuracy and verification** below for what was and was not checked.",
        "date_unknown": "## Date unknown",
        "from_chat": "chat log",
        "from_filename": "filename",
        "not_in_chat": "not found in chat log",
        "entry_meta": "`{file}` · {secs}s · timestamp from {stamp} · speaker from {attr}",
        "check": "> **CHECK THIS AUDIO:** {note}",
        "hand": "> **Checked by hand:** {note}",
        "no_speech": "_(no speech detected)_",
    },
    "pt": {
        "default_title": "Transcrições dos áudios: {name}",
        "source_folder": "Pasta de origem",
        "transcribed": "Áudios transcritos",
        "minutes": "minutos",
        "speakers": "Interlocutores",
        "model": "Modelo",
        "language": "idioma",
        "generated": "Gerado em",
        "unknown": "DESCONHECIDO",
        "unknown_note": "DESCONHECIDO (sem linha correspondente no log da conversa)",
        "saved": "{name} (contato salvo neste telefone)",
        "selfset": '"{name}" (nome definido pela própria conta no WhatsApp, '
                   "não é contato salvo)",
        "banner": "> Transcrição automática, não conferida por ninguém. Ouça o áudio "
                  "de origem antes de citar qualquer coisa, sobretudo números. Leia "
                  "**Precisão e verificação** abaixo para saber o que foi e o que não "
                  "foi conferido.",
        "date_unknown": "## Data desconhecida",
        "from_chat": "log da conversa",
        "from_filename": "nome do arquivo",
        "not_in_chat": "não encontrado no log da conversa",
        "entry_meta": "`{file}` · {secs}s · horário do {stamp} · remetente do {attr}",
        "check": "> **CONFERIR ESTE ÁUDIO:** {note}",
        "hand": "> **Conferido a ouvido:** {note}",
        "no_speech": "_(nenhuma fala detectada)_",
    },
}


def accuracy_section_en(rows, flagged, human_notes, span, args, chat_log_name) -> list:
    L = ["## Accuracy and verification", ""]
    L.append("**This is machine output. Nobody has listened to these recordings.** "
             "Read the rest of this section before quoting anything.")
    L.append("")
    L.append("### What is reliable and what is not")
    L.append("")
    L.append("The wording of ordinary speech comes out well. Numbers, monetary values, "
             "dates, percentages and proper nouns are the least reliable part of any "
             "Whisper transcript, and they are exactly the parts worth quoting. Listen "
             "to the source audio before relying on one. Every entry below carries its "
             "`.opus` filename so you can find the recording in one step.")
    L.append("")
    L.append("Date, time and speaker are **not** heard from the audio. They come from "
             f"`{chat_log_name}`, the chat log inside the WhatsApp export. An audio with "
             "no matching line in that log is labelled `UNKNOWN` rather than guessed.")
    L.append("")
    L.append("A speaker name in quotation marks is a name that account set for itself "
             "in WhatsApp, not a contact saved on this phone. WhatsApp marks those with "
             "a `~`. The phone number is the identifier; the name is a claim the account "
             "makes about itself.")
    L.append("")
    L.append("### The two ways this could be wrong")
    L.append("")
    L.append("Whisper fails in opposite directions, and both are checked automatically "
             "on every file.")
    L.append("")
    L.append("**It can invent.** On trailing silence it loops and repeats a fabricated "
             "sentence. Guarded by turning off conditioning on previous text, so one bad "
             "segment cannot contaminate the ones after it, plus a check for an "
             "implausible speaking rate or three identical consecutive segments.")
    L.append("")
    L.append("**It can stop early.** At a voice-activity boundary it drops the rest of a "
             "recording. This is the dangerous one, because a truncated transcript looks "
             "perfectly fine. Guarded by comparing where the transcript ends against the "
             "real audio duration measured separately, and flagging any gap over "
             f"{TRUNCATION_TOLERANCE:.0f} seconds.")
    L.append("")
    L.append("Anything flagged carries a **CHECK THIS AUDIO** warning on the entry "
             "itself. Once a human has listened, what they found is recorded as a "
             "**Checked by hand** note that stays with the entry.")
    L.append("")
    L.append("### Results for this run")
    L.append("")
    gaps = [(r["seconds"] - r.get("covered_to", 0.0)) for r in rows if r["seconds"] > 0]
    if gaps:
        L.append(f"- Coverage: every transcript reaches within {max(gaps):.1f}s of the end "
                 f"of its audio (median gap {sorted(gaps)[len(gaps)//2]:.1f}s). A gap of "
                 "about a second is normal trailing silence.")
    if flagged:
        L.append(f"- {len(flagged)} of {len(rows)} files tripped a check:")
        for r in flagged:
            state = ("checked by hand, see the note on the entry"
                     if r["file"] in human_notes else "**not yet checked by hand**")
            notes = "; ".join(render_flag(f, "en") for f in r["flags"])
            L.append(f"    - `{r['file']}` — {notes} ({state})")
    else:
        L.append("- No file tripped an automatic check. That is not the same as verified; "
                 "it means nothing looked wrong to the checks described above.")
    extra = [f for f in human_notes if any(r["file"] == f and not r["flags"] for r in rows)]
    if extra:
        n = len(extra)
        L.append(f"- {n} unflagged {'file was' if n == 1 else 'files were'} also checked "
                 "by hand as a precaution; the notes appear on the entries.")
    if span:
        ref, gone = span.get("referenced_audio", 0), span.get("missing_audio", [])
        if ref and not gone:
            L.append(f"- Completeness: the chat log references {ref} voice "
                     f"{'note' if ref == 1 else 'notes'}, and all {ref} are present in "
                     "the export and transcribed here.")
        elif ref:
            L.append(f"- Completeness: the chat log references {ref} voice "
                     f"{'note' if ref == 1 else 'notes'} but {len(gone)} "
                     f"{'is' if len(gone) == 1 else 'are'} missing from the export: "
                     + ", ".join(f"`{m}`" for m in gone))
        if span.get("omitted"):
            o = span["omitted"]
            L.append(f"- WhatsApp left {o} non-audio "
                     f"{'attachment' if o == 1 else 'attachments'} out of the export "
                     "entirely. Those are images and documents, not voice notes.")
    L.append("")
    L.append("### How it was produced")
    L.append("")
    L.append(f"Transcribed locally on this Mac with `{args.model}`, forced to language "
             f"`{args.language}`, seeded with a vocabulary prompt so domain terms and "
             "proper nouns come out right. No audio was uploaded anywhere. The process "
             "is repeatable: see the README in the project folder.")
    L.append("")
    return L


def accuracy_section_pt(rows, flagged, human_notes, span, args, chat_log_name) -> list:
    L = ["## Precisão e verificação", ""]
    L.append("**Isto é saída de máquina. Ninguém ouviu estas gravações.** "
             "Leia o resto desta seção antes de citar qualquer coisa.")
    L.append("")
    L.append("### O que é confiável e o que não é")
    L.append("")
    L.append("A fala corrente sai bem. Números, valores, datas, percentuais e nomes "
             "próprios são a parte menos confiável de qualquer transcrição automática, "
             "e são justamente o que se costuma citar. Ouça o áudio de origem antes de "
             "se apoiar em algum. Cada entrada abaixo traz o nome do arquivo `.opus`, "
             "para achar a gravação num passo só.")
    L.append("")
    L.append("Data, hora e remetente **não** são ouvidos do áudio. Vêm de "
             f"`{chat_log_name}`, o log da conversa dentro do export do WhatsApp. Áudio "
             "sem linha correspondente nesse log fica marcado como `DESCONHECIDO`, "
             "nunca adivinhado.")
    L.append("")
    L.append("Nome de interlocutor entre aspas é o nome que a própria conta definiu no "
             "WhatsApp, não um contato salvo neste telefone. O WhatsApp marca esses "
             "casos com um `~`. O número de telefone é o identificador; o nome é uma "
             "afirmação que a conta faz sobre si mesma.")
    L.append("")
    L.append("### Os dois jeitos de isto estar errado")
    L.append("")
    L.append("O Whisper erra em duas direções opostas, e as duas são checadas "
             "automaticamente em todos os arquivos.")
    L.append("")
    L.append("**Ele pode inventar.** No silêncio do fim da gravação ele entra em loop e "
             "repete uma frase fabricada. Contido desligando o condicionamento no texto "
             "anterior, para que um segmento ruim não contamine os seguintes, mais uma "
             "checagem de velocidade de fala implausível ou de três segmentos idênticos "
             "seguidos.")
    L.append("")
    L.append("**Ele pode parar cedo.** Numa fronteira de detecção de voz ele descarta o "
             "resto da gravação. Este é o perigoso, porque uma transcrição truncada "
             "parece perfeita. Contido comparando onde a transcrição termina com a "
             "duração real do áudio, medida à parte, e sinalizando qualquer diferença "
             f"acima de {TRUNCATION_TOLERANCE:.0f} segundos.")
    L.append("")
    L.append("O que for sinalizado leva um aviso **CONFERIR ESTE ÁUDIO** na própria "
             "entrada. Depois que alguém ouve, o que foi apurado fica registrado como "
             "nota **Conferido a ouvido**, junto da entrada.")
    L.append("")
    L.append("### Resultado desta rodada")
    L.append("")
    gaps = [(r["seconds"] - r.get("covered_to", 0.0)) for r in rows if r["seconds"] > 0]
    if gaps:
        L.append(f"- Cobertura: toda transcrição chega a no máximo {num(max(gaps), 1, 'pt')}s "
                 f"do fim do seu áudio (diferença mediana de "
                 f"{num(sorted(gaps)[len(gaps)//2], 1, 'pt')}s). Cerca de um segundo é "
                 "silêncio normal no fim da gravação.")
    if flagged:
        n = len(flagged)
        L.append(f"- {n} de {len(rows)} arquivos "
                 f"{'foi sinalizado' if n == 1 else 'foram sinalizados'}:")
        for r in flagged:
            state = ("conferido a ouvido, ver a nota na entrada"
                     if r["file"] in human_notes else "**ainda não conferido a ouvido**")
            notes = "; ".join(render_flag(f, "pt") for f in r["flags"])
            L.append(f"    - `{r['file']}`: {notes} ({state})")
    else:
        L.append("- Nenhum arquivo foi sinalizado. Isso não é o mesmo que verificado; "
                 "quer dizer apenas que nada pareceu errado às checagens descritas acima.")
    extra = [f for f in human_notes if any(r["file"] == f and not r["flags"] for r in rows)]
    if extra:
        n = len(extra)
        L.append(f"- {n} arquivo{'' if n == 1 else 's'} não sinalizado"
                 f"{'' if n == 1 else 's'} também "
                 f"{'foi conferido' if n == 1 else 'foram conferidos'} a ouvido por "
                 "precaução; as notas aparecem nas entradas.")
    if span:
        ref, gone = span.get("referenced_audio", 0), span.get("missing_audio", [])
        if ref and not gone:
            L.append(f"- Integridade: o log da conversa cita {ref} "
                     f"áudio{'' if ref == 1 else 's'}, e "
                     f"{'ele está presente' if ref == 1 else f'todos os {ref} estão presentes'} "
                     f"no export e {'transcrito' if ref == 1 else 'transcritos'} aqui.")
        elif ref:
            L.append(f"- Integridade: o log da conversa cita {ref} "
                     f"áudio{'' if ref == 1 else 's'}, mas {len(gone)} "
                     f"{'está faltando' if len(gone) == 1 else 'estão faltando'} no "
                     "export: " + ", ".join(f"`{m}`" for m in gone))
        if span.get("omitted"):
            o = span["omitted"]
            L.append(f"- O WhatsApp deixou {o} anexo{'' if o == 1 else 's'} que não "
                     f"{'é áudio' if o == 1 else 'são áudio'} fora do export. São imagens "
                     "e documentos, não mensagens de voz.")
    L.append("")
    L.append("### Como foi produzido")
    L.append("")
    L.append(f"Transcrito localmente neste Mac com `{args.model}`, forçado ao idioma "
             f"`{args.language}`, com um prompt de vocabulário para que termos do "
             "assunto e nomes próprios saiam certos. Nenhum áudio foi enviado para "
             "lugar nenhum. O processo é repetível: ver o README na pasta do projeto.")
    L.append("")
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out")
    ap.add_argument("--title", help="H1 for the document (default: the folder name)")
    ap.add_argument("--ui", choices=("en", "pt"), default="en",
                    help="language of the document's own text (default: en)")
    ap.add_argument("--model", default="mlx-community/whisper-large-v3-mlx")
    ap.add_argument("--language", default="pt")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    ui = args.ui
    S = LABELS[ui]

    src = Path(args.folder).expanduser()
    if not src.is_dir():
        sys.exit(f"Not a folder: {src}")

    project = Path(__file__).resolve().parent
    cache_dir = project / "transcripts" / ".cache" / re.sub(r"[^\w.-]", "_", src.name)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else project / "transcripts" / f"{src.name}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Optional sidecar of human verification notes, {audio filename: note}.
    # Kept outside the cache so it survives a --force re-run.
    notes_file = cache_dir.parent / (cache_dir.name + "-notes.json")
    human_notes = json.loads(notes_file.read_text()) if notes_file.exists() else {}

    chat_log = find_chat_log(src)
    meta = parse_chat(chat_log)
    audios = sorted(p for p in src.glob("*.opus"))
    if args.only:
        audios = [p for p in audios if p.name == args.only]
    if args.limit:
        audios = audios[: args.limit]
    if not audios:
        sys.exit("No .opus files found.")

    import mlx_whisper  # imported late so --help stays fast

    rows = []
    for i, audio in enumerate(audios, 1):
        cache_file = cache_dir / (audio.stem + ".json")
        if cache_file.exists() and not args.force:
            rec = json.loads(cache_file.read_text())
            print(f"[{i}/{len(audios)}] cached  {audio.name}", flush=True)
        else:
            seconds = duration_of(audio)
            print(f"[{i}/{len(audios)}] {audio.name} ({seconds:.0f}s) ...", flush=True)
            result = mlx_whisper.transcribe(
                str(audio),
                path_or_hf_repo=args.model,
                language=args.language,
                initial_prompt=INITIAL_PROMPT,
                condition_on_previous_text=False,
                verbose=False,
            )
            text = clean(result.get("text", ""))
            segments = result.get("segments", [])
            rec = {
                "file": audio.name,
                "seconds": seconds,
                "covered_to": max((float(s.get("end", 0)) for s in segments), default=0.0),
                "text": text,
                "flags": flags_for(text, segments, seconds),
                "model": args.model,
            }
            cache_file.write_text(json.dumps(rec, ensure_ascii=False, indent=1))

        info = meta.get(audio.name, {})
        stamp = info.get("datetime") or datetime_from_name(audio.name)
        rec["sender"] = info.get("sender", S["unknown"])
        rec["saved_contact"] = info.get("saved_contact", False)
        rec["attribution"] = S["from_chat"] if info.get("source") else S["not_in_chat"]
        rec["datetime"] = stamp
        rec["stamp_source"] = S["from_chat"] if info.get("datetime") else S["from_filename"]
        rows.append(rec)

    rows.sort(key=lambda r: (r["datetime"] or datetime.min, r["file"]))

    total = sum(r["seconds"] for r in rows)
    flagged = [r for r in rows if r["flags"]]

    # A "~" name in a WhatsApp export is the sender's own profile name, not a
    # contact saved on this phone. Say so, rather than asserting the identity.
    seen = {}
    for r in rows:
        seen.setdefault(r["sender"], r["saved_contact"])
    speakers = []
    for name in sorted(seen):
        if name == S["unknown"]:
            speakers.append(S["unknown_note"])
        else:
            speakers.append(S["saved" if seen[name] else "selfset"].format(name=name))

    L = []
    L.append(f"# {args.title}" if args.title
             else "# " + S["default_title"].format(name=clean(src.name)))
    L.append("")
    L.append(f"**{S['source_folder']}:** `{clean(str(src))}`  ")
    L.append(f"**{S['transcribed']}:** {len(rows)} "
             f"({num(total/60, 1, ui)} {S['minutes']})  ")
    L.append(f"**{S['speakers']}:** {'; '.join(speakers)}  ")
    L.append(f"**{S['model']}:** `{args.model}`, {S['language']} `{args.language}`  ")
    L.append(f"**{S['generated']}:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    span = chat_span(chat_log)
    if span and rows:
        last_audio = max((r["datetime"].date() for r in rows if r["datetime"]), default=None)
        if ui == "pt":
            line = (f"**Período da conversa:** {span['first']} a {span['last']}. "
                    "Todos os áudios do export estão transcritos aqui")
            if last_audio and last_audio < span["last"]:
                line += (f"; o último é de {last_audio}, e a partir daí a conversa segue "
                         "só por texto e chamadas")
            line += "."
            if span["omitted"]:
                o = span["omitted"]
                line += (f" O WhatsApp deixou {o} anexo{'' if o == 1 else 's'} que não "
                         f"{'é áudio' if o == 1 else 'são áudio'} fora do export.")
        else:
            line = (f"**Chat span:** {span['first']} to {span['last']}. "
                    "Every voice note in the export is transcribed here")
            if last_audio and last_audio < span["last"]:
                line += (f"; the last one is {last_audio}, after which the chat continues "
                         "in text and calls only")
            line += "."
            if span["omitted"]:
                o = span["omitted"]
                line += (f" WhatsApp left {o} non-audio "
                         f"{'attachment' if o == 1 else 'attachments'} out of the export.")
        L.append("")
        L.append(line)

    L.append("")
    L.append(S["banner"])
    L.append("")
    build = accuracy_section_pt if ui == "pt" else accuracy_section_en
    L.extend(build(rows, flagged, human_notes, span, args, chat_log.name))
    L.append("---")
    L.append("")

    current_day = None
    for r in rows:
        dt = r["datetime"]
        day = dt.date() if dt else None
        if day != current_day:
            current_day = day
            if dt:
                header = (f"## {dt.strftime('%Y-%m-%d')} "
                          f"({WEEKDAYS_PT[dt.weekday()]}, {dt.day} de "
                          f"{MONTHS_PT[dt.month-1]} de {dt.year})")
            else:
                header = S["date_unknown"]
            L.append(header)
            L.append("")
        time_str = dt.strftime("%H:%M:%S") if dt else "??:??:??"
        label = r["sender"] if r["saved_contact"] else f'"{r["sender"]}"'
        L.append(f"### {time_str} · {label}")
        L.append("")
        L.append(S["entry_meta"].format(file=r["file"], secs=f"{r['seconds']:.0f}",
                                        stamp=r["stamp_source"], attr=r["attribution"]))
        L.append("")
        for f in r["flags"]:
            L.append(S["check"].format(note=render_flag(f, ui)))
            L.append("")
        if r["file"] in human_notes:
            L.append(S["hand"].format(note=human_notes[r["file"]]))
            L.append("")
        L.append(r["text"] if r["text"] else S["no_speech"])
        L.append("")

    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(f"Hand-verification notes go in: {notes_file}")
    if flagged:
        print(f"{len(flagged)} file(s) flagged for manual review: "
              + ", ".join(r["file"] for r in flagged))


if __name__ == "__main__":
    main()
