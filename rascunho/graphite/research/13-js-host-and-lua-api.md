# 13 — 8bitpaint: the JS host and the Lua brush API (deep pass, 2026-10-20)

Study only. 8bitpaint pencil v1.5.0.0 and 8bitpaint web "latest" (settings v1.6.1.1) by minordaimyo. Closed source, no licence. Nothing below is copied code. It describes the technique with formulas, and cites the prettified sources so each claim can be checked.

- **P** = `reference/8bitpaint/8bitpaintpencil/app.pretty.js` (pencil host, 3759 lines)
- **PG** = `8bitpaintpencil/index.pretty.js` (pencil Emscripten glue)
- **W** = `8bitpaintweb_latest/app.pretty.js` (full app host)
- **WG** = `8bitpaintweb_latest/index.pretty.js`

This report builds on `studio/rascunho/research/08-8bitpaint-pencil-study.md` and does not repeat it. Corrections to that study are collected in §7.

---

## 1. Pointer pipeline

### 1.1 Listeners (P 1012–1058)
- **Device detection** uses the lower-cased UA:
  - `IPAD = /ipad/ || (/macintosh/ && document.ontouchstart !== undefined)`.
  - `IPHONE = /iphone|ipod/ || (/macintosh/ && ontouchstart)`.
  - **On iPadOS with the default desktop UA, both IPAD and IPHONE are true.** That UA also fires an alert asking the user to switch to the mobile website (P 1008–1011).
  - `MOBILE` = android+mobile; `ANDROID_TABLET` = android without "mobile".
- **The view canvas gets only pointer events.** `pointermove`, `pointerdown`, `pointerup` and `pointercancel` all go to `paint`, and `pointerover`/`pointerleave` go to `hover_on`/`hover_off`. Every listener uses `{passive:false}` (P 1024–1029).
- **Other listeners:**
  - iOS adds a `touchmove` handler on the canvas that calls `preventDefault()` (P 1046).
  - `keydown`, `keyup` and `wheel` go on document. Wheel deltaY>0 zooms out, <0 zooms in.
  - `document.oncontextmenu = () => false`.
  - `pagehide` (iOS) or `beforeunload` (others) saves settings.
- CSS `touch-action:none` is set on the canvas and the UI.
- **What it does not use:** no `getCoalescedEvents`, no `getPredictedEvents`, no `pointerrawupdate` listener, no `setPointerCapture` on the paint canvas. The only capture is on the selection overlay, P 1958.
- **No requestAnimationFrame anywhere.** Everything runs synchronously inside the event handler.

### 1.2 `paint(e)` (P 1557–1940), in order
1. Return if the wasm is not initialised. Then `preventDefault()`. If "Disable touch" is on and `pointerType=='touch'`, return: all touch is dropped.
2. On `pointerdown`, hide the brush menu.
3. **Barrel button:** `if (e.buttons & 2) && !tool_shift && group != eraser` → `tool_shift()` (P 1566). The pen side switch (or the E key) switches temporarily to the eraser group. `tool_shift` first sends one `TabletEvent(prev, p=0)` to end the stroke (P 3192–3199). On pointerup it switches back (P 1937).
4. Selection tools (kinds 15/16/17/18) also run `paint_selection`.
5. **down/move routing.** The predicate is `WAITING_FOR_ALL_POINTERS_UP || disable_touch || pointerType != 'touch'` (P 1578–1582).
   - **True** (pen, mouse, or touch while a gesture is draining): the space-key scroll code runs only if `ENABLE_SCROLL` is set (Space held, plus Ctrl for the rotate/zoom variant; desktop only). Otherwise the event falls through to drawing.
   - **False** (a touch, touch enabled, no gesture draining): the touch is registered in `POINTERID_COUNT[pointerId] = index`, with start/end recorded in a `TouchPoint`. While ≥2 touches are registered, every move becomes a CSS-transform preview and returns (P 1729–1755). With exactly one touch it falls through to drawing.
6. **Coordinates** (P 1760–1766):
   - `x = (pageX − (rect.left + pageXOffset)) · k`
   - `y = (pageY − (rect.top + pageYOffset)) · k`
   - `k = CANVAS.width / parseFloat(CANVAS.style.width)` (backing pixels per CSS pixel)
   - The result is in *view backing-store pixels*, not document pixels. The wasm owns the view transform (zoom, rotation, flip, pan) and maps view px to document px itself. JS never inverts a matrix.
7. **Tilt** (§1.4), then the **tilt-correction offset** (§1.5), then **pressure** (§1.3).
8. **pointerdown:** unless scrolling, send `TabletEvent(x, y, 0, alt, az)` with pressure forced to 0 (P 1807–1812). This is a "move the pen here without drawing" event that seeds the smoother at the touchdown point. Only Fill (kind 11) and Contour extraction (9999) also get a real-pressure `TabletEvent` on down (P 1813–1826).
9. `show_brush_ghost(e)` on every down/move: hover, drawing and touch alike.
10. **pointermove draws** only if all of these hold (P 1827–1844):
    - `p > 0`
    - not scrolling
    - kind is neither 11 nor 9999
    - **`Object.keys(POINTERID_COUNT).length < 2`**

    It then sends `TabletEvent(x, y, p, alt, az)` (signature: five f64 numbers).
11. Store `PREV_X/Y/alt/az`; the flush uses them.

### 1.3 Pressure per device (P 1790–1806)
- **Default** `p = 0`.
- **touch:** only when "Draw with touch" is on, touch is enabled, and exactly one touch is registered:
  - `p = 0.5`, `alt = π/2`, `az = 0` (finger = vertical pen).
  - If `e.pressure` is defined, `p = e.pressure`.
  - If the event is a `pointermove` with `pressure == 0`, `p = 0.5`. iOS reports 0 for finger moves, so finger strokes draw at a constant 0.5.
- **pen or mouse:** `p = e.pressure`, raw with no curve. A mouse gives 0.5 while a button is held and 0 while hovering, so mouse hover never draws.
- **The iOS touchdown ramp.** If `IPAD || IPHONE`: `IOS_STROKE_COUNTER++` runs on **every** down/move of **any** pointer type. Then `if pointerType=='pen' && counter < 10: p = p · counter/10`. The counter resets to 0 only on `pointerup`/`pointercancel` (P 1866).
  - The pointerdown event is sent with p = 0 anyway, so the first *drawing* move has counter 2.
  - **Ramped moves are counter 2…9, with factors 0.2, 0.3 … 0.9.** Full pressure starts at the 10th event. That is 8 moves; with no `getCoalescedEvents`, Safari delivers about one pointermove per display frame, so the ramp lasts about 67 ms at 120 Hz and about 133 ms at 60 Hz.
  - **The stroke attack has three ramps stacked:** the p=0 touchdown sample, this JS ×0.2…×0.9 ramp, and the wasm smoother's pressure ramp of about N/2 events (§8.3).
  - **Caveat (inferred from code):** Pencil hover events on M2+ iPads are `pointermove`s, so they also advance the counter. If the pen hovers for ≥9 events before touching, the ramp is already spent at touchdown. On hover-capable iPads the ramp mostly applies only to a fast stab. Worth testing on Edson's iPad.
  - Pressure is **not** smoothed or curved in JS. Any curve lives in the wasm.

### 1.4 Tilt (P 1767–1780, `tilt2spherical` P 3622–3643)
- **Native angles.** If `e.altitudeAngle` exists and is not exactly π/2, `alt = e.altitudeAngle` and `az = e.azimuthAngle` are passed straight through (radians, W3C convention).
- **tiltX/tiltY fallback.** When native angles are missing or report vertical, and tiltX/tiltY exist and are not both 0, it converts with `tilt2spherical(tiltX°, tiltY°)`. Let `tx`, `ty` be in radians.
  - **Azimuth:**
    - `tiltX==0`: az = π/2 if tiltY>0, 3π/2 if tiltY<0.
    - `tiltY==0`: az = π if tiltX<0, else 0.
    - Either at ±90: az = 0.
    - Otherwise `az = atan2(tan ty, tan tx)`, wrapped to [0, 2π).
    - This matches the W3C conversion exactly.
  - **Altitude:**
    - `A = |sin tx|`, `B = |sin ty|`, `C = |cos tx|·|cos ty| · (0.75·cos²(2·az) + 0.25)^0.25`
    - `alt = asin( C / sqrt(A² + B² + C²) )`
    - This is a home-made approximation. It is exact on the axes but **too low on the diagonals**. The W3C formula is `alt = atan(1/√(tan²tx + tan²ty))`. Computed comparison:

| tiltX, tiltY | 8bitpaint alt | W3C alt |
|---|---|---|
| 30, 0 | 60.0° | 60.0° |
| 0, 45 | 45.0° | 45.0° |
| 20, 20 | 52.2° | 62.8° |
| 30, 30 | 36.9° | 50.8° |
| 45, 45 | 19.5° | 35.3° |

  - Our build should use the W3C formula, or `Touch.altitudeAngle` where it exists. The fallback only matters on browsers that give tiltX/Y alone (e.g. Wacom on desktop Chrome).
- **No tilt data at all:** alt = π/2, az = 0.
- **The latest app** adds an altitude exaggeration on non-iOS only: `alt = max(π/2 − 1.3333·(π/2 − alt), 20°)` (W 1981–1985). The pencil app lacks it.

### 1.5 "Tilt correction" (傾き補正, slider 0–20, step 0.1, default 0) (P 1781–1789)
- iOS only.
- `x −= sin(tiltX°) · tc` and `y −= sin(tiltY°) · tc`, in view backing pixels. Written as code it is `r += sin(−tiltX)·tc` and `i −= sin(tiltY)·tc`.
- It shifts the contact point *against* the tilt direction by up to `tc` px, which compensates the Pencil's tip/parallax offset. It uses the raw `tiltX/tiltY` even when native altitude/azimuth exist.
- Only the position moves; the mark shape is unchanged. On a browser without tiltX it would give NaN, but iOS Safari always supplies tiltX/tiltY.

### 1.6 Viewport and sizing (`window_resize`, P 708–890)
- **iPad.** The static meta is `width=device-width,initial-scale=0.5`, and JS rewrites it to `width=<innerWidth>,initial-scale=0.5,minimum-scale=0.5,maximum-scale=0.5` (P 721–733).
  - At scale 0.5 one CSS px equals one physical pixel on a DPR-2 iPad. So `innerWidth` is in physical px and the canvas is sized `canvas.width = style.width = innerWidth` (k = 1), with height = innerHeight − menu bar.
  - Every UI panel is then CSS-scaled ×2 back up (`RATIO = 2`, P 752–753).
  - The trick gives a full-resolution backing store without relying on `devicePixelRatio` scaling.
  - A 200 ms post-init check reloads the page once if `innerWidth` changed: the meta rewrite only takes effect after a reload (P 680–707, reload at 686).
- **iPhone/Android phone:** CSS px = backing px (k = 1); menus ×1.5.
- **Android tablet:** k = 1; menus × min(DPR, 1.75).
- **Desktop:** `canvas.width = innerWidth · DPR` (k = DPR).
- **Default document size** (no saved canvas):
  - Restore path (`restore_canvas` P 1274–1336): `window_w · k · 4/n` by `window_h · k · 4/n`, where `n = RATIO`, or `RATIO/2` on iPad. On iPad that is 4× the physical screen in each direction.
  - `new_canvas()` (P 1337–1361) uses `4/RATIO`, i.e. 2× on iPad. The two paths disagree; either way the document is larger than the screen.
  - Presets: A3–A6 and B3–B6 at 600 dpi (`PAPER_DPI=600`, P 360–384).

### 1.7 Pointerup / pointercancel (P 1850–1939)
- **For touch:**
  - Record the end position and unregister the pointer.
  - When none are left, clear `WAITING_FOR_ALL_POINTERS_UP` and reset the TouchPoint.
- **Gesture end.** It counts as a gesture end if there is no waiting flag and either Space-scroll is on, or (≥2 touches were seen this gesture, fewer are now registered, and this is a touch):
  - **Tap test:** `distance == (0,0) && scale == 1 && angle == 0`, exactly (P 1875–1879), measured on touches 0 and 1 only.
    - **There is no timer and no tolerance.** Any `pointermove` that changed a coordinate turns the tap into a pinch.
    - Taps: 2 touches → `undo_clicked()`, 3 touches → `redo_clicked()`.
    - `WAITING_FOR_ALL_POINTERS_UP` stays set until the remaining fingers lift, so lifting 2 fingers one after the other fires only once.
  - **Otherwise it commits the pinch:**
    - Reset the CSS transform.
    - Compute the start and end midpoints in backing px.
    - `newScale = currentScale / pinchScale` (the scale is document px per view px, so spreading the fingers lowers it).
    - `SETTING.angle += pinchAngle·180/π`.
    - Call `ViewPinchEvent(sx, sy, ex, ey, newScale, −angle)` (P 1895–1915), which re-renders in the wasm.
- **Stroke flush** (pen, mouse, or a drawing finger; not kind 9999): **4 ×** `TabletEvent(PREV_X, PREV_Y, 0, PREV_alt, PREV_az)` (P 1925–1932). It then clears all touch tracking, so a pen-up also forgets any resting finger.
  - The latest app sends `2·brush_correction + 1` zero-pressure events instead (17 at the default 8; W 2170).
  - **Measured (§8.3): for the pencil engine, one zero-pressure event is enough.** It drains the smoother and draws the remaining tail with a pressure taper. Events 2…n change nothing.
  - **With no zero event at all, the tail is cut**: by about `corr·step/4` px, or 30 px at correction 30.
  - Our build must send at least one p=0 sample at pen-up (or drain explicitly).
- On iOS the ramp counter resets here.

### 1.8 Palm and touch rejection
- **No palm heuristic in JS** (no contact size, no timing). Rejection relies on:
  1. iPadOS's own palm rejection while the Pencil is in contact.
  2. The finger being a no-op unless "Draw with touch" is on.
  3. The "Disable touch" toggle (all touch ignored).
  4. Pen moves being suppressed while ≥2 fingers are down (`< 2` test, P 1833). A single resting palm does **not** block the pen.
- **One finger alone does nothing on iPad**, apart from the ghost: there is no one-finger pan. Two fingers pan, zoom and rotate together via one CSS transform `rotate(angle) scale(s) translate(dx,dy)` around the current midpoint (P 1736–1754).
  - Up to 4 touches are tracked (`maxTouches = 4`).
  - The latest app adds a rotation snap: rotation is ignored until |angle| ≥ 10°, and the committed angle is rounded to 5° (W 1931, 2146).

### 1.9 Hover
- `HOVER` is written but never read (P 1471, 1474, 1564, 1851).
- What matters is that `show_brush_ghost` runs on every move, including Pencil hover moves with pressure 0, so the ghost tracks the hovering pen.
- `pointerleave` hides the ghost (P 1473–1481).
- Hover never draws, because of the `p > 0` gate.

### 1.10 Keyboard and desktop (`key_down` P 1132–1171; manual)
The manual (manual_pencil.html, "8bitpaint web operating manual ver. 1.3.3.0") is only a shortcut table. Translated:

| Action | Shortcut |
|---|---|
| Scroll | Space + left-drag |
| Zoom in / out | Wheel up / down |
| Open | Ctrl+O |
| Save | Ctrl+S, Ctrl+Shift+S |
| Undo / Redo | Ctrl+Z / Ctrl+Y |
| Zoom in | Ctrl+; or Ctrl+Num+ |
| Zoom out | Ctrl+- or Ctrl+Num- |
| Flip horizontally | H |
| Rotate 15° left / right | Shift+PageUp / Shift+PageDown |
| Reset view | Home |
| Eraser while held | E |
| Brush size up / down | ] / [ |

- The code also maps numpad 0 (ctrl+space), 1 (space), 2 (undo) and 3 (redo).
- `[`/`]` step through `1,2,3,4,5,6,7,8,9,10,12,14,16,20,25,30,35,40,50,60,70,80,100,120,160,200,250,300,350,400,450,500` (`brush_size_down/up` P 1194–1253).
- Zoom in/out multiply the scale by 1/√2 or √2, clamped to [1/16, 16] (P 1254–1273).

---

## 2. Ghost cursor = the dab footprint the wasm computes

- The pencil family (kinds 6, 27, 28, 29) and Smudge (23) call `ShowBrushGhostPencilEvent()` (no args, P 1547–1551; dispatch `show_brush_ghost` P 1482–1507). The kneaded erasers (8, 10) have their own event. Other tools use a plain circle of radius `size/2/scale` (P 1508–1538).
- The wasm calls back the import **`DrawGhostBrushPencil(shift_x, shift_y, a, b, angle)`**, five **f32** values (wasm type 74). The values are in document pixels, with angle in radians.
- **JS draws it as follows (PG 26–74):**
  - `s = GetViewCanvasScaleEvent()` (document px per view backing px).
  - Ghost canvas side = `4·(max(a,b) + |shift_y|)/s + 10` backing px.
    - Bug: it uses `max(|shift_y|, |shift_y|)`, so shift_x is ignored in the bounds.
  - Centred at `offsetX/offsetY` (the CSS position of the pointer).
  - Then `ctx.ellipse(cx + shift_x/s, cy + shift_y/s, a/s, b/s, angle, 0, 2π)`, plus a ±5 px crosshair at the unshifted centre.
  - **The stroke() call sits only inside the `b/s ≥ 6` branch.** For `2 ≤ b/s < 6` the path is built but never stroked, so small brushes show no ghost (the round ghost `show_brush_ghost_standard` has the same quirk, P 1508–1538).
- **What this tells us about the dab model:**
  - The footprint is an ellipse with semi-axes **a** (along `angle`) and **b**, centred **(shift_x, shift_y)** away from the pen point, in document px.
  - The crosshair marks the pen point.
  - Measured values from the wasm are in §8.1:
    - `angle` = azimuth.
    - `b` = size/2.
    - `a` = b + L(alt), with the centre shifted by L(alt) along the azimuth. So **the round dab's back edge stays fixed at pen − b, and the patch extends forward along the azimuth by 2L**: the far tip is at pen + b + 2L.
    - L = 0 above ~31.5° altitude.

---

## 3. Blit path

- **`DrawCanvasRectFromArray(ptr, len, w, h, dst_x, dst_y, src_x, src_y, dirty_w, dirty_h)`**, ten i32 (PG 2–25):
  - `new ImageData(new Uint8ClampedArray(HEAP.buffer, ptr, len), w, h)` is a zero-copy view of the wasm heap.
  - Then `ctx.putImageData(img, dst_x, dst_y, src_x, src_y, dirty_w, dirty_h)`.
  - There is no scaling, no `drawImage` and no compositing in JS. The wasm hands over an already composited, already view-transformed RGBA frame of the view size, plus the dirty sub-rectangle.
  - The latest app copies first (`bytes.slice()`, WG 15). That is safer if the heap grows, since a view over a detached buffer would throw, but it costs a full-frame copy each call.
- **View canvas:** one `<canvas id=view_canvas>` with a 2D context. Its backing size is set in §1.6, and `ctx.scale(1,1)` (or DPR on desktop) is set but irrelevant to `putImageData`.
- **Zoom, rotate and flip are re-rendered by the wasm** (`ViewZoomChangeEvent`, `ViewAngleChangeEvent`, `ViewPinchEvent`, `HFlipEvent`).
  - While a slider is dragged (`oninput`), JS previews with CSS: zoom resizes and recentres the canvas element (P 2722–2734), and rotation sets `style.transform = rotate(Δdeg)` (P 2680–2687).
  - On `onchange` it resets CSS and calls the wasm.
  - The pinch gesture works the same way (§1.8).
  - Zoom slider: `scale = 16^(2(1−t) − 1)`, t ∈ [0,1] → scale ∈ [1/16, 16] (P 2755–2757). The inverse is P 2547–2550.
- **No requestAnimationFrame.** Every `TabletEvent` that changes pixels triggers a synchronous `putImageData` of the dirty rect inside the pointer handler. Safari already delivers pointer events once per frame, so this ends up frame-paced in practice.
- **The other imports:**
  - `LoadMaterialJS()` just calls `paper_texture_clicked(SETTING.paper_texture)`, which re-uploads the current paper (PG 398–400).
  - **`DrawCanvasWideLine`, `DrawCanvasRectangle` and `SaveCanvasToIndexedDB` have no implementation in the pencil glue.** Only the auto-generated `missing function → abort()` stubs exist (PG 1530, 1526, 1562). The app's own `SaveCanvasToIndexedDB()` (P 3738) is a different global, without the leading underscore, so it is not wired up. The pencil wasm evidently never calls them.
  - In the latest app, `_SaveCanvasToIndexedDB(ptr,len)` is real (WG 502).
- **Paper upload:** the PNG is drawn into a 512×512 canvas, read with `getImageData`, malloc'd and passed to `LoadMaterialEvent(ptr, 512·512·4)` (P 2886–2929). It is RGBA and never freed (a small leak per switch). The grey value is used by the wasm.

---

## 4. Tools and parameters (pencil app)

**Kind ids** (P 385–415). Pencil build:

| id | Tool | id | Tool |
|---|---|---|---|
| 0 | Pen | 15 | Selection |
| 1, 2 | Gray-scale pens | 16 | Lasso |
| 3 | Marker | 17 | Selection(all) |
| 4 | Tex | 18 | Lasso(all) |
| 5 | Analog | 19 | Custom |
| 6 | Pencil | 20 | Lasso paint |
| 7 | Eraser | 21 | Lasso eraser |
| 8 | Kneaded eraser | 22 | Lasso eraser(all) |
| 9 | Eraser(all) | 23 | Smudge1 |
| 10 | Kneaded eraser(all) | 24 | Script |
| 11 | Bucket | 25 | Erase-and-draw |
| 12 | Line | 26 | Smudge2 |
| 13 | Rectangle | 27 | **Pencil 4B** |
| 14 | Ellipse | 28 | **Pencil HB** |
| | | 29 | **Pencil 2H** |
| | | 9999 | Contour |

**Brush slots and defaults** (`init_setting_data`, P 2240–2305; slot → kind, size, hardness):

| Slot | Kind | Tool | Size | Hardness | In menu? |
|---|---|---|---|---|---|
| 26 | 27 | Pencil 4B | 16 | 40 | yes, **default drawing tool** |
| 27 | 28 | Pencil HB | 16 | 40 | yes |
| 28 | 29 | Pencil 2H | 16 | 50 | yes |
| 0 | 6 | Pencil | 16 | 40 | not exposed in the pencil menu |
| 1 | 8 | Kneaded eraser | 100 | 40 | yes, default eraser |
| 9 | 9 | Eraser(all) | 100 | 50 | yes |
| 12 | 22 | Lasso eraser(all) | 20 | 50 | yes |
| 8 | 17 | Selection(all) | 50 | 50 | yes |
| 15 | 18 | Lasso(all) | 50 | 50 | yes |
| 2 | 23 | Smudge1(all) | 200 | 50 | yes |
| 3 | 26 | Smudge2 | 200 | 50 | **not exposed** |

- The menu is in index.html: `brush_clicked(26/27/28/1/9/12/8/15/2)`.
- The migration block that would set 200/40 for missing slots 24–28 (P 2399–2432) dereferences undefined, throws, and falls back to the defaults, so it never applies. **The effective defaults are 16/40, 16/40 and 16/50.**
- On init, all 29 slots are pushed to the wasm: `BrushSelectionEvent(i)`, `KindOfPenChangeEvent`, `BrushSizeChangeEvent(size)`, `BrushHardnessChangeEvent(hardness)` (P 537–557).

**Mappings:**
- **Size:** slider t ∈ [0,1], step 0.001 → `size = round(500^t)`, inverse `t = ln(size)/ln 500` (P 2677–2679, 2536). Range 1–500 **document px, diameter**. Menu presets: 1, 3, 6, 16, 40, 100, 250, 500 (P 365).
- **Hardness:** slider t ∈ [0,1] → `round(100·t)` (P 2674–2676). Range 0–100, linear.
- **Brush correction (手振れ補正, "shake correction"):** integer slider 0–99, step 1 (`MAX_BRUSH_CORRECTION = 99`). The setting default is **8**; the HTML default `value=2` is overwritten on init. A single global value for all brushes, sent with `SetBrushCorrection(n)` (P 2766–2778, 640–646).
- **Tilt correction:** 0–20, step 0.1, default 0 (§1.5).
- **Paper texture (用紙質感):**
  - Ids: 0 none, **1 noise (default)**, 2 paper, 3 cotman, 4 langton, 5 monval_tradition, 6 muse_touch, 7 mermaid2, 8 wargman (P 2893–2903).
  - **There is no texture-strength, scale or contrast control in JS.** The only paper parameter is which image. Strength must be implicit in the image contrast, or fixed in the wasm.
- **Layers:** 9 entries, all `multiply`, opacity 255. Colours in order: #000000, #4747cc, #59a560, #7bd8d2, #dc474d, #e839e7, #f3cf46, #808080, plus #ffffff for the background (`init_layer_parameter` P 2305–2389).

**Persisted settings.** localStorage key `8bitpaintpencil_setting`, the whole `SETTING` JSON at version "1.0.0.0" (`load_setting_from_localstorage`/`save_setting_to_localstorage` P 2393–2443). It is saved:
- on each slider change, tool click and paper change,
- on pagehide/beforeunload,
- in auto_save every ≥30 s once there has been ≥5 s of inactivity.

It holds `disable_touch`, `draw_with_touch`, `brush_correction`, `tilt_correction`, `paper_texture`, all 29 brush {size, hardness, kind}, the 9 layers, 8 brush scripts, `new_canvas_size`, `display_ppi` 264 and `selection_mode`. The view angle is reset to 0 on load. The canvas itself goes to IndexedDB `8bitpaint_pencil_db`, via a Worker for the PNG encode.

---

## 5. The Lua brush-script API

**Sources.** No API document ships in the download. The evidence is:
- the four samples (`lua/sample1/2/4/5.lua`; the site index labels them "sample code 1", "sample code 2", "a brush whose width changes with the pen's speed" (4) and "**G-pen style**" (5));
- the default script in each host (P 2390 = W 2958);
- the default script compiled into both wasms;
- the registered function names in the wasm string table.

**How scripts load.** There is **no in-app editor**, contrary to the brief. The latest app has eight slots (brush slots 16–23, kind 24). `load_brush_script` copies the text into the heap byte-by-byte with `charCodeAt` (W 1197–1216), so **non-ASCII characters are corrupted. Keep scripts ASCII.** It then calls `LoadBrushScriptEvent(slot, ptr, len)`, where 0 = ok. In the pencil host `load_brush_script` is an empty stub (P 1108), although the pencil wasm still contains Lua and the export.

**Registered globals, from the wasm string table, both builds:**
`bs_pixel_set, bs_line, bs_circle, bs_ellipse, bs_canvas_width, bs_canvas_height, bs_width, bs_stylus_rotate, bs_stylus_tilt, bs_width_max, bs_width_min, bs_distance, bs_atan, bs_canvas_angle, bs_dir, bs_normal`. The standard `math` library is available (`math.random`, `math.cos`, `math.pi`).

**The contract:**
- The script body runs once at load and initialises globals (`lastDrawX = 0`, `firstDraw = true`, tables).
- `main(x, y, p)` is called by the engine along the stroke. It returns **1 if it drew, 0 if it skipped.** All samples update `lastDraw*` only on the drawing path, so the return value most plausibly tells the engine to treat this sample as the new "last dab" for undo/dirty or tail logic (inferred).
- `last(x, y, p)` is called at stroke end. Every sample leaves it empty.
- Globals persist across calls. `firstDraw` is never reset in the samples, so either the engine re-runs the chunk per stroke or `firstDraw` matters only for the very first stroke. See §8.

**Meaning of each call.** Measured in the latest app's wasm (§8.4) unless marked *usage*:

| Function | Meaning |
|---|---|
| `main(x, y, p)` | x, y in **document px** (sub-pixel floats; zoom changes the view, not these). p = pressure 0–1, **after** the brush-correction smoother |
| `bs_width()` | `size · p`, **linear** in pressure for script brushes |
| `bs_width_min()` | 0 |
| `bs_width_max()` | `size` (the slider value: a diameter, despite sample usage as radius-like) |
| `bs_distance(dx, dy)` | √(dx²+dy²); (3,4) → 5 |
| `bs_dir()` | Unit stroke direction in document px, y down: rightward stroke → (1, 0) |
| `bs_normal()` | Unit normal: rightward → (0, 1), i.e. dir rotated +90° in y-down screen space |
| `bs_atan(x, y)` | `atan2(−y, x)`: (1,0) → 0, (0,1) → −π/2. The y-down vector becomes a math-convention angle |
| `bs_stylus_tilt()` | **10 × altitude in radians** (π/2 → 15.708, 45° → 7.854, 5° → 0.873). Odd scale, but that is what the engine gives |
| `bs_stylus_rotate()` | **2π − azimuth** (az 0 → 6.2832, 45° → 5.4978, 90° → 4.7124). The y-down azimuth mirrored to y-up |
| `bs_canvas_width()`, `bs_canvas_height()` | Document size in px |
| `bs_canvas_angle()` | View rotation (0 unrotated) |
| `bs_circle(x, y, r, mode)` | Hard-edged filled disc, radius r in doc px. **mode 1 = erase**, any other value (0, 0.5, 2, 255) = paint in the layer colour. Exactly 4 args are required |
| `bs_ellipse(x, y, a, b, rad, mode)` | Filled ellipse, semi-axes a, b, rotated by rad; mode as for circle. 6 args |
| `bs_line(x1, y1, x2, y2, mode)` | 1 px line; the 5th arg is mode, not width. 5 args |
| `bs_pixel_set(x, y, mode)` | One pixel. 3 args |

The C side reads arguments by **negative stack index**, from the top. Too few arguments raises `bad argument #-k … got function`; extra leading arguments silently shift the meaning. Pass exactly the arity.

**Sandbox.** The script runs with **only the `math` library**: no base library (`print`, `tostring`, `error`, `pcall` are nil), no `string`, no `table`.

**Call cadence (measured):**
- `main` is called **exactly 4 times per `TabletEvent`**, at t = 0, ¼, ½, ¾ along a spline segment from the previous smoothed point to the current one. Positions are not equally spaced when the input steps vary, so it is a curve and not a lerp.
- The script's distance test is therefore the only spacing control.
- The pen-down event yields nothing. The first move yields 4 calls at the touchdown point.
- `last()` was **never called** in any probe (pen-up included). Treat it as a no-op hook.

**What the samples reveal:**
- **Spacing is the script's job.** The engine calls `main` far more often than the script wants to draw, and the script skips by distance.
  - The pencil wasm's built-in default script (strings dump) is: `distance < w → return 0`, then `bs_circle(x, y, w·0.5)`. Spacing is 1 diameter.
  - sample1 uses `< 0.2·w` (scatter brush).
  - sample5 and the host default use **`< 0.05·w`**, i.e. 5 % of width, for a smooth ellipse nib.
  - So the brief's "`distance < w·0.2`" is sample1's scatter spacing only. The smooth default is 0.05·w.
- **sample2 and sample4 use tiny distances.** sample2 skips when `distance < 0.002·bs_width()`; sample4 uses `r = w/2 − 200·distance`.
  - The engine calls `main` 4× per event (measured), so the distance between calls is ¼ of the per-event pointer travel. At slow iPad speeds (1–2 px per event) that is 0.25–0.5 px.
  - sample4 therefore clamps to r = 1 at any normal speed. It is a toy.
  - sample2's threshold is effectively "draw every call".
- **sample5, "G-pen style", is a flat calligraphy nib, not a pencil tilt model.**
  - `a = width_max/10` (a fixed thin semi-axis), `b = w` (a pressure-driven semi-axis, so the full nib length is 2w), rotated by `bs_stylus_rotate()`, drawn every 0.05·w.
  - It shows the ellipse primitive and that azimuth is available. It is **not** evidence of how the built-in pencils shape their dab; that comes from the ghost data in §8.

---

## 6. Pencil app vs latest full app (what changes the feel)

| | Pencil 1.5.0.0 | Latest web (1.6.1.1) |
|---|---|---|
| Stroke-end flush | 4 × p=0 (P 1926) | 2·brush_correction+1 × p=0 (W 2170): full drain, tapered tail |
| Altitude on non-iOS | raw | `max(π/2 − 1.3333(π/2−alt), 20°)` (W 1983) |
| Pinch rotation | free | dead zone until 10°, committed rounded to 5° (W 1931, 2146) |
| Blit | zero-copy view | `bytes.slice()` copy (WG 15) |
| `pointerrawupdate` | — | handled in `paint`, but **no listener registers it**, so it is dead code |
| Coalesced or predicted events | none | none |
| Pencils | 4B/HB/2H (kinds 27/28/29) + hidden Pencil (6) | single Pencil (6). Kinds 27/28/29 mean line eraser / contour / filled rectangle |
| Default drawing tool | 4B, 16 px, h 40 | Pencil, 16 px, h 40 |
| Kneaded eraser hardness | 40 | 50 |
| Default paper | 1 = noise | 0 = none |
| Smudge2 | hidden | exposed |
| Brush scripts | stub | 8 slots (file load only) |
| Settings key | `8bitpaintpencil_setting` | `8bitpaint_setting` |
| Same in both | iOS ramp, tilt correction, tilt2spherical, the 2-/3-finger tap rule, putImageData per event, brush correction default 8 | |

---

## 7. Corrections to study 08

1. **"Undo snapshot before first dab"** is wrong as a JS fact. `AddLayerToHistoryEvent` fires only if `LAYER_MODIFIED` is set, and that flag is set only by layer-panel changes (visibility, lock, clip, mode, order: P 3013–3048) and by new canvas. Per-stroke undo is handled inside the wasm.
2. **The pressure ramp** is not "the first 10 pen events". The counter counts all iOS down/move events, including hover and touch, and the effective ramp is 8 drawing moves at ×0.2…×0.9 (§1.3).
3. **"Pointerup sends four events"** holds only for the pencil app; latest sends 2N+1. The pencil engine needs only the first one, which drains the smoother and draws the tapered tail (§8.3).
4. **sample5 is a G-pen, not the pencil.** The pencils' tilt footprint is native: an ellipse whose back edge stays fixed and which grows forward toward the lean once altitude drops below ~31.5° (§8.1).
10. **4B/HB/2H** differ by a density ceiling (black / ~62 % / ~25 %) plus default hardness, not by separate kernels (§8.2).
9. **"Pressure arrives raw"** is true for JS. Inside the wasm, the brush-correction smoother filters **pressure as well as position**, so every stroke gets a start ramp and an end taper of about N/2 events (§8.3). Pressure maps to **width** (`size·p^0.4` for the pencils) and to a **hardness-dependent contact threshold**, not to opacity alone (§8.2).
5. **The spacing rule** "distance < width → skip" belongs to the wasm's built-in default script. The host and sample5 defaults use 0.05·w.
6. **Ghost:** the wasm passes `(shift_x, shift_y, a, b, angle)` as f32 in document px, and JS divides by the view scale. Small ghosts (< 6 view px) are invisible because of the stroke() placement.
7. **"Zoom/rotate rendered by the wasm"** is confirmed. The CSS preview happens both during a pinch and during slider drags.
8. **Coordinates** sent to the wasm are view backing pixels, not document pixels.

---

## 8. Measured from the wasm

**Method.** The vendor glue and wasm ran in a Node `vm` sandbox with stubbed host imports (`ctx.putImageData`, the ghost canvas, ImageData). There was no require/fs or network inside the context. The harness is in the session scratchpad and is not kept in the repo.
- Pencil wasm: `InitData(512,512,512..1024,…, ratio 2)`, a flat-grey paper loaded through `LoadMaterialEvent`, all 29 brush slots pushed as the host does, `SetBrushCorrection(0)` unless stated.
- Frames were rebuilt from the dirty-rect `putImageData` calls and measured.
- The Lua probes used the latest app's wasm, because the pencil wasm's `LoadBrushScriptEvent` traps since its Lua state is never initialised.
- Values were read out through error messages (only `math` is loaded).

### 8.1 Pencil footprint (`DrawGhostBrushPencil` args, identical for 4B/HB/2H, Pencil (6) and Smudge (23))

Settled tilt, any pressure, any zoom (0.5…8) and any document size give the same values:

- `angle = azimuth` (radians, W3C/screen convention: 0 = +x, π/2 = +y down).
- `b = size/2`. Tiny brushes grow b at very low altitude, e.g. size 2: b = 1.14 at 21°, 4.25 at 10°, 8.46 at 0°.
- `a = b + L`, `shift = L·(cos az, sin az)`. The back extreme is at pen + L − (b + L) = **pen − b**, the round dab's own back edge, which does not move. The far tip is at **pen + b + 2L**, so the patch grows forward along the lean by 2L. The measured top of the alt-20° mark is 247–248 = 256 − 8 ✓.
- **L depends on altitude and is nearly independent of brush size.** It is an absolute length in document px, not a multiple of the size. It is not affected by zoom.

| altitude | 31.5°+ | 30° | 28° | 25° | 22° | 20° | 15° | 10° | 5° | 0° |
|---|---|---|---|---|---|---|---|---|---|---|
| L, size 16 | 0 | 0.80 | 2.88 | 8.79 | 18.2 | 25.6 | 51.2 | 83.1 | 122 | 166 |
| L, size 100 | 0 | 0.74 | 2.68 | 8.17 | 16.9 | 23.8 | 47.6 | 77.2 | 113 | 154 |
| L, size 500 | 0 | 0.47 | 1.70 | 5.20 | 10.8 | 15.1 | 30.3 | 49.1 | 72.1 | 98.3 |

- The shape is a smooth onset at ~31.5°, roughly quadratic near the threshold and close to linear (~8 px/°) below 10°. No closed form was fitted.
- **Ghost = the drawn mark at p = 1.** At alt 20°, az 90°, size 16, the ghost predicts a span of y = 248…315. The stroke measured 247…308 (the faint tip falls under the threshold).
- **Elongation scales with pressure.** At alt 10°, p 0.3 the extent is 0.52× that at p 1.
- At size 100 the measured span was 205…347 against a predicted 206…354.

### 8.2 Pressure, width, hardness, paper

- **4B / HB / 2H are one engine with different darkness ceilings.** The contact thresholds are nearly identical (pmin within ~5–10 %, harder grades very slightly higher). But a fully saturated mark on white paper settles at luminance **0 for 4B (and for Pencil, kind 6), 96 for HB, 192 for 2H**: maximum density 100 %, ~62 % and ~25 %.
  - Repeated passes build up toward that ceiling. With p 0.2, paper 220, 1/2/4/8 passes, edge-pixel luminance went: 4B 231/203/127/0, HB 235/213/156/96, 2H 245/235/213/192.
  - This is a graphite burnish limit: a hard lead cannot reach black however often it is layered.
  - It answers study 08's open "4B/HB/2H differences": **cap density per grade + the default hardness (40/40/50)**.
- **Width.** Size 40, vertical pen, white paper: mark width 39/36/31/25/21/16/12 px at p = 1/.75/.5/.3/.2/.1/.05. That fits **`width ≈ size · p^0.4`** within ±1 px.
  - The ghost does not show this. It always draws the p = 1 footprint.
- **Contact threshold.** Flat paper of height u = grey/255. Size 20, overlapping stroke, minimum p that leaves any ink:

| hardness \ u | 1.00 | 0.86 | 0.71 | 0.50 | 0.25 |
|---|---|---|---|---|---|
| 0 | 0 | 0 | .003 | .048 | .335 |
| 20 | 0 | .002 | .018 | .119 | .465 |
| 40 (4B/HB) | .001 | .029 | .100 | .297 | .646 |
| 60 | .076 | .249 | .407 | .622 | .843 |
| 80 | .229 | .452 | .598 | .762 | .907 |
| 100 | .356 | .574 | .698 | .827 | .934 |

  - **The table factorises exactly:** `ln pmin(h,u) = ln pmin(100,u) / e(h)`, with e(100) = 1, e(80) = 0.70, e(60) = 0.40, e(40) = 0.156, e(20) = 0.089, e(0) = 0.062. The ratios are constant to ±0.002 across all five heights.
  - So **the lead touches paper of height u when `p^{e(h)} ≥ T(u)`**, with T(1) = .356, T(.86) = .574, T(.71) = .698, T(.50) = .827, T(.25) = .934 (taken from the hardness-100 row).
  - In words: hardness is an exponent on pressure, and the paper height map sets a per-pixel pressure threshold. Soft leads reach the valleys at light pressure; hard leads touch only the peaks.
  - This is the core of the grain behaviour. Above the threshold, overlapping dabs saturate to full colour (multiply black → 0).
  - **Hardness has no effect at p = 1 on white paper.** Every hardness gave an identical mark.
  - The per-dab density curve was not isolated: strokes saturate under the 4 px overlap.

### 8.3 Brush correction (smoother)

- **Scope.** The smoother filters position *and* pressure over a window of events.
- **Position lag** with no pen-up event:
  - Ink stops short of the last point by about **(N/4) events × step** (N = correction).
  - N 8: 2 / 4 / 8 / 20 / 44 px at input steps of 1 / 2 / 4 / 8 / 16 px.
  - N 30: 8 / 15 / 30 / 64 / 132 px.
  - N 99: 25 / 50 / ~100 px.
  - Corners are cut accordingly (N 99: the corner is rounded about 12 px inward on the diagonal).
- **Pen-up (first p=0 event)** drains the filter: the stroke reaches the endpoint (−1…−4 px), and further zeros change nothing.
- **Pressure ramps.** Seen in the script engine, where the p passed to main is smoothed:
  - The start ramps up linearly from 0.25 over about N/2 events (N 8: 16 samples ≈ 4 events; N 30: about 15 events).
  - Pen-up emits the tail with p falling linearly to 0 over the same length (N 8: 16 extra main() calls; N 30: 60).
  - With N = 0 the first segment still ramps (0.25 → 0.75) and there is no tail.
- **Pencil engine equivalent.** Measured as mark width at size 40:

| N | start width (x = 100 / 104 / 108) | end width (x = 396 / 400 / 404) |
|---|---|---|
| 0 | 36 / 39 / 39 | flat to the end |
| 8 | 36 / 37 / 39 | 36 / 34 / 29 |
| 30 | 29, reaching 39 by x = 130 | 36 → 16 over the last ~25 px |

  - Without the pen-up event, the N 30 stroke ends abruptly at x ≈ 385.
- **Takeaway.** The 8bitpaint "feel" of soft ends comes from this smoother (pressure averaged together with the p = 0 touchdown and pen-up samples), not from an explicit taper. Default N = 8 gives a short taper of about 2–4 events.

### 8.4 Lua sampling (latest app wasm)

- The values are in the §5 table.
- The x positions per `main()` call for a uniform 16 px input are 100,102.5,106,110.5 | 116,120,124,128 | 132,… The first segment eases in from a duplicated start point; after that the four samples per event are evenly spaced.
- For inputs at steps of 1, 2, 4, 8, 16, 32 the samples are spaced non-uniformly inside each segment (e.g. 107, 108.75, 110.5, 112.75), so it is spline interpolation.

---

## Confidence

**High (read directly in the JS, line-cited):**
- the listeners and options, `paint` branches, pressure substitution, the iOS ramp conditions, `tilt2spherical` maths (with the computed table), tilt correction, coordinate transform, viewport trick;
- the pointerup flush counts, the tap-undo/redo rule (exact-zero, no timer), pinch commit, ghost drawing code, blit implementation, no rAF, missing imports;
- tool ids, defaults, slider mappings, paper ids, localStorage contents;
- the differences in §6.

**High (measured by running the vendor wasm):**
- ghost parameters vs altitude, azimuth, size, zoom; footprint = ghost at p = 1; the per-grade darkness ceilings (4B 0, HB 96, 2H 192);
- width ≈ size·p^0.4; the factorised hardness/paper threshold table;
- smoother lag and drain-on-first-zero; the Lua call cadence (4/event), units and scalings (tilt ×10, rotate = 2π − az, atan2(−y, x), width = size·p); `math`-only sandbox; `last()` never called; primitive arity and mode 1 = erase.

These are measurements of black-box behaviour on synthetic input (flat paper, straight strokes). The exact closed forms of L(alt), e(h) and T(u) were not derived.

**Medium:**
- Whether Pencil hover moves exhaust the iOS ramp before touchdown. The logic is certain; whether iPadOS Safari emits hover `pointermove`s on Edson's hardware is unverified.
- Whether iPad Safari supplies native `altitudeAngle`, which decides whether the fallback ever runs on iPad.
- That the pencil smoother is the same filter as the script engine's (the shapes agree, the window sizes differ slightly: lag about N/4 vs a ramp about N/2).

**Low / not established:**
- Per-dab density/opacity curve (only the build-up toward the ceiling was seen), smudge and kneaded-eraser kernels, how paper texture (not flat grey) modulates within the threshold, the real-paper behaviour of hardness at p = 1.

**Sources missing:** `8bitpaintweb/manual.html` is not in the download. The two pencil-folder manual files are identical and contain only the v1.3.3.0 shortcut table translated in §1.10. No Lua API document exists in the download; the API above is reconstructed from the samples, the wasm strings and measurement.
