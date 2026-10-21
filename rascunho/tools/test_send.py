#!/usr/bin/env python3
"""Post one test line into a running Claude Code session by name (same wire format as server.py).

    python3 tools/test_send.py <session-name> [text...]

Prints the registry entry it resolved and whatever the socket replies.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import post_line, public, resolve_session  # noqa: E402

if len(sys.argv) < 2:
    sys.exit(__doc__)
name = sys.argv[1]
text = " ".join(sys.argv[2:]) or "Test message from rascunho/tools/test_send.py. Reply with one word: received."

matches = resolve_session(name)
if len(matches) != 1:
    sys.exit(f"{len(matches)} user-named running sessions called {name!r}: "
             + json.dumps([public(m) for m in matches], indent=1))
session = matches[0]
print("resolved:", json.dumps(public(session), indent=1))
print("socket:  ", session["socket"])
delivered, detail = post_line(session["socket"], text)
print("delivered:", delivered, "| reply:", detail)
