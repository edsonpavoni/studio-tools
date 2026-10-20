#!/usr/bin/env python3
"""Put a picture under a sheet on the iPad, for Edson to draw over: POST /underlay on the sketch server.

    python3 tools/place.py IMAGE [--sheet SHEET_ID] [--from NAME] [--note TEXT]

IMAGE is a PNG or JPEG on this Mac. Without --sheet a new sheet is made and the iPad opens it
(unless a hand is on the glass: then it waits in the gallery). With --sheet the picture goes under
that sheet, e.g. the id a sketch arrived with. Prints the server's answer: {"sheet", "url", ...}.
"""
import argparse
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = "http://localhost:8880/underlay"

ap = argparse.ArgumentParser(description="Place a picture under a sheet on the iPad.")
ap.add_argument("image", metavar="IMAGE", help="PNG or JPEG path")
ap.add_argument("--sheet", metavar="SHEET_ID", default=None, help="an existing sheet; default: a new sheet")
ap.add_argument("--from", dest="sender", metavar="NAME",
                default=os.environ.get("CLAUDE_SESSION_NAME") or "claude")
ap.add_argument("--note", metavar="TEXT", default="", help="shown on the iPad; names a new sheet")
args = ap.parse_args()

path = os.path.abspath(os.path.expanduser(args.image))
if not os.path.isfile(path):
    sys.exit(f"no such image: {path}")
with open(path, "rb") as handle:
    data = handle.read()
if data.startswith(b"\x89PNG"):
    mime = "image/png"
elif data.startswith(b"\xff\xd8\xff"):
    mime = "image/jpeg"
else:
    sys.exit("the image must be a PNG or JPEG")

url = URL + (f"?{urllib.parse.urlencode({'sheet': args.sheet})}" if args.sheet else "")
headers = {"Content-Type": mime, "X-From": args.sender}
if args.note:
    headers["X-Note"] = args.note.encode("ascii", "replace").decode()   # HTTP headers are ASCII
req = urllib.request.Request(url, data=data, method="POST", headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(r.read().decode())
except urllib.error.HTTPError as e:
    sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')}")
except urllib.error.URLError as e:
    sys.exit(f"not placed: sketch server not reachable ({e.reason}). Start it: studio/sketch/serve.sh")
