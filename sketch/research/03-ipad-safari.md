# iPad Safari + Apple Pencil web sketch app — verified constraints (2026-10-20)

Versions matter: everything below is for Safari/iPadOS 18.2+ unless stated.

## 1. Pointer Events with Apple Pencil

- **pointerType "pen", pressure, tiltX/tiltY**: shipped with Pointer Events in Safari 13 — https://raw.githubusercontent.com/mdn/browser-compat-data/main/api/PointerEvent.json
- **azimuthAngle / altitudeAngle**: Safari 18.2 — https://webkit.org/blog/16301/webkit-features-in-safari-18-2/
- **twist**: always 0 for Pencil Pro; barrel-roll exposure is an open bug (iPadOS 26.4.1, iPad Pro M4) — https://bugs.webkit.org/show_bug.cgi?id=296943 and https://bugs.webkit.org/show_bug.cgi?id=298276
- **Hover (M2+ iPad Pro)**: Safari 16.1 added Pencil hover (https://www.macrumors.com/2022/10/24/apple-safari-16-1-launch/); WebKit dispatches hover events for Pencil, but tilt/roll are not reported while hovering. Expect `pointermove` with `buttons === 0`.
- **Pencil Pro squeeze / double-tap**: not exposed to the web (https://developer.apple.com/forums/thread/760238, https://developer.apple.com/forums/thread/776468). Double-tap still works as the OS-level tool switch, but the page never sees it.
- **Sampling rate**: `pointermove` delivers 240 Hz on iPad Pro (120 Hz in Low Power Mode), but events are dropped on slow frames — https://developer.apple.com/forums/thread/689375. A 2025 report of segmented pointermove curves with Pencil Pro: https://developer.apple.com/forums/thread/776468
- **Fractional pointer coordinates**: Safari 26.2.

## 2. Coalesced / predicted / raw events

- `getCoalescedEvents()` and `getPredictedEvents()`: Safari 18.2 (WebKit bug 264002 fixed Aug 2024 https://bugs.webkit.org/show_bug.cgi?id=264002).
- **Known bug**: in iOS 18.2 the coalesced events lacked `pointerId` and `target` (Flutter workaround https://github.com/flutter/engine/pull/56903). Read only x/y/pressure/tilt/timeStamp from coalesced events; take identity from the parent event.
- 18.2: `click` events became PointerEvents, but taps report `pointerType "mouse"` on click — https://bugs.webkit.org/show_bug.cgi?id=282988
- **`pointerrawupdate`**: not supported in any Safari through 27.2 — https://caniuse.com/mdn-api_element_pointerrawupdate_event

## 3. Latency and rendering

- **`desynchronized: true`**: Safari accepts the 2D option since 15 (WebGL: not supported) (https://bugs.webkit.org/show_bug.cgi?id=225173). No WebKit source documents a low-latency path like Chrome's; treat it as harmless, not a guaranteed win.
- **OffscreenCanvas**: 2D in Safari 16.4 (https://webkit.org/blog/13966/webkit-features-in-safari-16-4/); WebGL in workers 17+ (https://bugs.webkit.org/show_bug.cgi?id=253431).
- **rAF rate**: capped near 60 fps by default on ProMotion. 120 fps only if the user turns off Settings > Safari > Advanced > Feature Flags > "Prefer Page Rendering Updates Near 60fps" — https://bugs.webkit.org/show_bug.cgi?id=294338 (how-to: https://www.iphone-ticker.de/promotion-im-web-freischalten-so-nutzt-safari-die-volle-bildrate-271471/). Edson can flip this on his own iPad.
- **WebGL vs 2D latency**: no measured iPad comparison found. Safari 26 adds WebGPU — https://webkit.org/blog/17333/webkit-features-in-safari-26-0/. Chrome's write-up on the extra compositing frame: https://developer.chrome.com/blog/desynchronized
- Practical: consume all coalesced points per `pointermove`, draw the live stroke immediately (not in rAF), commit to the tile layer on `pointerup`.

## 4. Palm rejection, gestures, Safari chrome

- **Palm rejection is OS-level and aggressive**: while the Pencil is on screen, no new finger touches fire in Safari, and vice-versa — https://developer.apple.com/forums/thread/89773. Still guard in code: while a `pen` pointer is down, ignore `touch` pointers. Touch API exposes `touchType` "stylus"/"direct" and `radiusX/radiusY` (iOS 14.5+).
- **Two-finger pan/zoom**: handle it yourself from two `touch` pointers; `touch-action: none` on the canvas disables Safari's pan/pinch (https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events/Using_Pointer_Events, https://wwdcnotes.com/notes/wwdc19/203/). `user-scalable=no` is ignored since iOS 10 — https://webkit.org/blog/7367/new-interaction-behaviors-in-ios-10/. Also `preventDefault()` on `gesturestart/gesturechange`.
- **Long-press loupe / callout**: open bug "Safari loupe can't be disabled with CSS" — https://bugs.webkit.org/show_bug.cgi?id=296492. `-webkit-touch-callout: none` reported not working on iOS 26.1 — https://developer.apple.com/forums/thread/808606. Reliable fallback: non-passive `touchstart` `preventDefault()` on the canvas.
- **Scribble**: swallowed Pencil pointer events on web pages (fixed 2021 — https://bugs.webkit.org/show_bug.cgi?id=217430). Workaround still worth keeping: a `touchmove` listener calling `preventDefault()` — https://developer.apple.com/forums/thread/662874. Keep no focusable inputs under the drawing area.

## 5. Home-screen web app over plain http

- Since iOS 26 "every website added to the Home Screen opens as a web app" by default — https://webkit.org/blog/17333/webkit-features-in-safari-26-0/. For 16.4–18 use a manifest with `display: standalone` (or `apple-mobile-web-app-capable` meta); no HTTPS requirement.
- **Service workers need a secure context**; only `localhost` is exempt, so none over `http://edson-mac.local`. Not needed.
- **Wake Lock**: secure-context API, so `navigator.wakeLock` is undefined over http; use Settings > Auto-Lock > Never instead — https://bugs.webkit.org/show_bug.cgi?id=254545

## 6. Networking iPad → Mac

- `.local` two-label names resolve via mDNS on iOS — https://support.apple.com/TS3389
- Local-network privacy does not gate Safari — https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy
- No documented POST size cap; a 4–20 MB PNG via `fetch` is fine; send `canvas.toBlob()` as the body, not base64.
- No HTTPS needed for pointer events, canvas, fetch, or Home Screen install.

## 7. Other bites

- Canvas: per-canvas area cap 16,777,216 px — https://pqina.nl/blog/canvas-area-exceeds-the-maximum-limit/; total canvas memory ~384 MB, device-dependent — https://www.pqina.nl/blog/total-canvas-memory-use-exceeds-the-maximum-limit/. Infinite canvas must be tiled (e.g. 2048² tiles × DPR).
- Viewport: use `100dvh`/`svh`; `viewport-fit=cover` + `env(safe-area-inset-*)`.
- Desktop-mode on iPad still fires pointer events normally; no evidence it changes `pointerType`.

## Do / Don't

**Do**
- Use Pointer Events; branch on `pointerType === "pen"`; read `pressure`, `tiltX/Y`, `altitudeAngle/azimuthAngle` (18.2+).
- Loop over `e.getCoalescedEvents()` (fallback `[e]`); feed `getPredictedEvents()` only into the live overlay stroke.
- `touch-action: none; -webkit-user-select: none; -webkit-touch-callout: none` on the canvas, plus non-passive `touchstart/touchmove` `preventDefault()` and `gesturestart` `preventDefault()`.
- Ignore `touch` pointers while a pen pointer is active; drive pan/zoom from two touch pointers.
- Tile the world canvas; scale by `devicePixelRatio`; draw the live stroke on a small overlay canvas and commit on `pointerup`.
- Ship a manifest with `display: standalone`, `viewport-fit=cover`, `apple-touch-icon`; test with the 60 fps feature flag off for 120 Hz.
- POST PNG as a Blob; `.local` hostname is fine.

**Don't**
- Don't rely on `pointerrawupdate`, `twist`, squeeze, double-tap, Wake Lock, service workers, or `desynchronized` doing anything on Safari.
- Don't trust `pointerId`/`target` on coalesced events or `pointerType` on `click`.
- Don't use `user-scalable=no` as your pinch defence, `100vh` for layout, or any single canvas > 16.7 M px.
- Don't put inputs/contenteditable near the drawing surface (Scribble), and don't base64-encode large exports.
