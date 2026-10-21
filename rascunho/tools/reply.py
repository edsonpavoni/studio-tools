#!/usr/bin/env python3
"""Answer the iPad from a Claude Code session: POST /reply on the rascunho server.

    python3 tools/reply.py [--from NAME] [--sheet SHEET_ID] [--image PATH] "text"
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

URL = "http://localhost:8880/reply"

ap = argparse.ArgumentParser(description="Send a reply to the iPad rascunho page.")
ap.add_argument("--from", dest="sender", metavar="NAME",
                default=os.environ.get("CLAUDE_SESSION_NAME") or "claude")
ap.add_argument("--sheet", metavar="SHEET_ID", default=None, help="sheet id the reply belongs to")
ap.add_argument("--image", metavar="PATH", default=None, help="PNG to show on the iPad")
ap.add_argument("text")
args = ap.parse_args()

image = os.path.abspath(os.path.expanduser(args.image)) if args.image else None
if image and not os.path.isfile(image):
    sys.exit(f"no such image: {image}")
body = {"from": args.sender, "sheet": args.sheet, "text": args.text, "image": image}
req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                             headers={"Content-Type": "application/json"})


def not_sent(why):
    print(f"not sent ({why}). Request it would have sent:")
    print(f"POST {URL}\n{json.dumps(body, indent=1)}")
    sys.exit(0)


try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(r.read().decode())
except urllib.error.HTTPError as e:
    if e.code == 404:
        not_sent("server has no /reply route yet")
    sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')}")
except urllib.error.URLError as e:
    not_sent(f"rascunho server not reachable: {e.reason}")
