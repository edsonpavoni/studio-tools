// client.js — the page's contract with server.py. Any UI (the current sketch.js or the one in design/) imports this.
// Everything fails soft: callers get a thrown Error with a readable message, never a hang.

const json = async (url, init) => {
  const r = await fetch(url, init);
  const body = await r.json().catch(() => ({}));
  if (!r.ok && body.ok !== true) throw new Error(body.detail || `${r.status} ${r.statusText}`);
  return body;
};
const q = (obj) => Object.entries(obj).filter(([, v]) => v !== undefined && v !== null && v !== '')
  .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');

export const api = {
  // running Claude Code sessions: [{name, pid, sessionId, cwd, status, nameSource}]
  sessions: (all = false) => json(`/sessions${all ? '?all=1' : ''}`),

  // send a PNG blob to a session by name. Resolves {ok, id, path, session, delivered, detail}.
  send: (blob, session, { note, sheet } = {}) => json('/send', {
    method: 'POST',
    headers: { 'Content-Type': 'image/png', 'X-Session': session, ...(note ? { 'X-Note': note } : {}), ...(sheet ? { 'X-Sheet': sheet } : {}) },
    body: blob,
  }),
  sendStatus: (id) => json(`/send-status?${q({ id })}`),
  sends: (limit = 20) => json(`/sends?${q({ limit })}`),

  // replies from sessions: [{id, time, from, sheet, text, image}] newest first; image is a URL or null
  replies: (limit = 20) => json(`/replies?${q({ limit })}`),

  // sheets
  sheets: () => json('/sheets'),
  sheet: (id) => json(`/sheet?${q({ sheet: id })}`),
  // tiles are one density PNG per colour layer: `layer` is the colour hex without '#'
  tileUrl: (id, tx, ty, layer) => `/tile?${q({ sheet: id, tx, ty, layer })}`,
  putTile: (id, tx, ty, blob, layer) => json(`/tile?${q({ sheet: id, tx, ty, layer })}`, { method: 'POST', headers: { 'Content-Type': 'image/png' }, body: blob }),
  deleteTile: (id, tx, ty, layer) => json(`/tile?${q({ sheet: id, tx, ty, layer })}`, { method: 'DELETE' }),
  putThumb: (id, blob) => json(`/thumb?${q({ sheet: id })}`, { method: 'POST', headers: { 'Content-Type': 'image/png' }, body: blob }),
  thumbUrl: (id) => `/sheets/${encodeURIComponent(id)}/thumb.png`,
  renameSheet: (id, name) => json(`/sheet-meta?${q({ sheet: id })}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) }),
  deleteSheet: (id) => json(`/sheet?${q({ sheet: id })}`, { method: 'DELETE' }),
};

// Long-poll /events and call handler(event) for each one. Events: {seq, time, type: 'sent'|'seen'|'reply', ...}.
// Starts from "now" (events already on the server are skipped) unless `since` is given. Returns a stop() function.
export function subscribe(handler, { since = null } = {}) {
  let stopped = false, seq = since;
  (async () => {
    if (seq === null) {
      try { seq = (await json('/events?since=0&timeout=0')).seq; } catch { seq = 0; }
    }
    let delay = 0;
    while (!stopped) {
      try {
        const { seq: next, events } = await json(`/events?${q({ since: seq, timeout: 25 })}`);
        seq = next; delay = 0;
        for (const e of events) if (!stopped) { try { handler(e); } catch (err) { console.error('event handler', err); } }
      } catch {
        delay = Math.min(15000, delay ? delay * 2 : 1000);          // server down: back off, keep trying
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  })();
  return () => { stopped = true; };
}
