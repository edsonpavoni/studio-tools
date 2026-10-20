# 14 · Paper textures in 8bitpaint pencil: analysis and procedural recipe (2026-10-20)

Source: the 9 height maps in `studio/graphite/reference/8bitpaint/8bitpaintpencil/img/` (© minordaimyo, not shippable). This note covers their statistics only, plus our own procedural equivalents. Scripts live in `research/13-textures/scripts/` (Python 3.14 venv with numpy, Pillow and scipy).

## 0. Format and conventions

- All nine files are 512×512 **8-bit RGBA**, with alpha = 255 everywhere. Only the R channel matters.
  - `none` and `noise` have R = G = B exactly.
  - The 7 scanned papers differ by at most 2 levels between channels (colour-conversion jitter, not information).
- **Polarity (assumed):** `none.png` is 255 everywhere, so 255 means "full deposit, tooth top" and low values are pits that stay white. "Peaks" below means high values.
- **Units:** I assume 1 texel = 1 device pixel at 100% zoom on an iPad Pro 12.9 (264 ppi, DPR 2). That gives **0.0962 mm/px**, so a 512 tile is **49.3 mm**. The mapping is unverified (it sits inside the wasm).
- **Angles** are in screen convention: y points down, degrees run clockwise from +x, so 40° is a line running down to the right. Checked by eye on wargman and mermaid2 in the contact sheet. "Grain elongation" = spectral peak + 90°.
- **Feature size** = half-period = 256 / f, where f is in cycles per 512 px. That is the width of one bump.

## 1. Statistics of the originals (R channel)

| metric | noise | paper | cotman | langton | mermaid2 | monval_trad. | muse_touch | wargman |
|---|---|---|---|---|---|---|---|---|
| grey levels used | 19 (step 8) | 13 (step ~16) | 95 (step 3) | 95 | 95 | 86 | 127 (step 2) | 95 |
| mean | 219.3 | 181.7 | 208.3 | 220.2 | 211.7 | 233.7 | 198.4 | 180.7 |
| std | 45.8 | 37.7 | 39.2 | 51.7 | 46.9 | 25.5 | 51.5 | 37.7 |
| min / max | 108 / 252 | 65 / 255 | 1 / 253 | 1 / 253 | 1 / 253 | 4 / 253 | 1 / 254 | 1 / 253 |
| p1 / p5 | 108 / 108 | 89 / 122 | 87 / 133 | 1 / 103 | 49 / 111 | 138 / 181 | 43 / 95 | 76 / 114 |
| p25 / p50 / p75 | 196 / 252 / 252 | 158 / 190 / 207 | 186 / 218 / 240 | 213 / 243 / 253 | 192 / 229 / 245 | 226 / 243 / 253 | 170 / 212 / 240 | 159 / 184 / 208 |
| p95 / p99 | 252 / 252 | 239 / 255 | 253 / 253 | 253 / 253 | 253 / 253 | 253 / 253 | 254 / 254 | 237 / 253 |
| skew / excess kurtosis | −1.29 / 0.40 | −0.45 / 0.00 | −1.17 / 1.44 | −2.33 / 5.51 | −1.64 / 2.68 | −2.16 / 5.88 | −1.10 / 0.81 | −0.63 / 0.63 |
| pixels at max level | **51%** | 2.5% | 10% | **32%** | 15% | 27% | 11% | 1.2% |
| histogram shape | clipped half-Gaussian, spike at 252 | ~Gaussian, slight left skew | unimodal, left tail, white clip | strongly clipped white + black pits | left skew + clip | narrow, clipped | broad, left skew | ~Gaussian |
| ac lag 1 x / y | 0.00 / 0.00 | 0.49 / 0.34 | 0.65 / 0.40 | 0.56 / 0.35 | 0.81 / 0.52 | 0.71 / 0.54 | 0.82 / 0.44 | 0.79 / 0.76 |
| half-width ac=0.5, x / y (px) | 0.5 / 0.5 | 1.0 / 0.8 | 1.4 / 0.8 | 1.1 / 0.8 | 2.2 / 1.0 | 1.6 / 1.1 | 2.9 / 0.9 | 1.9 / 1.7 |
| dominant f (cyc/512), peak of f·P(f) | 254 (Nyquist, flat) | none (1/f + scan gradient) | 59 | 88 | 40 | 74 | 69 | 22 |
| feature size px / **mm** | 1 / **0.10** | 1–32 / 0.1–3 (no single scale) | 4.3 / **0.42** | 2.9 / **0.28** | 6.4 / **0.62** | 3.5 / **0.33** | 3.7 / **0.36** | 11.6 / **1.12** |
| spectral slope, f 4–128 / 128–255 | −0.05 / −0.12 (white) | −1.19 / −1.45 | −0.24 / −3.1 | −0.30 / −3.1 | −0.69 / −3.7 | −0.26 / −4.2 | −0.78 / −3.4 | −1.13 / −5.2 |
| energy f<16 / 16–64 / ≥64 | 0.5 / 4 / 95% | 12 / 19 / 69% | 2 / 23 / 75% | 2 / 15 / 84% | 3 / 37 / 60% | 1 / 29 / 70% | 5 / 29 / 67% | 5 / 52 / 43% |
| anisotropy (max/min angular power) | 1.2 (isotropic) | 1.9 | 7.1 | 3.4 | 9.5 | 7.3 | **16.0** | **13.1** |
| grain elongation direction | n/a | ~horizontal (pixel scale) | ~150° | ~160° | ~20° | ~0° (horizontal) | ~0° (horizontal streaks) | ~40° (diagonal) |
| local contrast σ1 / σ2 / σ4 / σ8 | 40 / 44 / 45 / 46 | 26 / 31 / 34 / 36 | 25 / 34 / 38 / 39 | 35 / 46 / 50 / 51 | 25 / 37 / 44 / 46 | 14 / 21 / 25 / 25 | 28 / 41 / 48 / 51 | 16 / 25 / 32 / 36 |
| seam corr L–R / T–B (interior x / y) | −0.08 / 0.07 (0 / 0) | **0.02 / 0.11** (0.49 / 0.35) | 0.59 / 0.30 (0.66 / 0.41) | 0.50 / 0.17 (0.56 / 0.33) | **−0.13 / −0.07** (0.78 / 0.52) | **0.03 / −0.01** (0.73 / 0.57) | 0.66 / 0.26 (0.82 / 0.43) | 0.73 / 0.63 (0.80 / 0.76) |
| tiles? | yes (trivially, white) | **no** | ~yes (T–B weak) | L–R yes, T–B weak | **no** | **no** | L–R yes, T–B weak | **yes** |
| peaks (≥ mean+1σ, or the max plateau): fraction | 51% (plateau) | 19% | 16% | 32% (plateau) | 15% (plateau) | 27% (plateau) | 16% | 14% |
| peak blob mean px (shuffled baseline) | 8.3 (8.3) | 2.9 (1.6) | 2.5 (1.4) | 3.4 (2.5) | 2.5 (1.4) | 5.3 (2.1) | 3.3 (1.4) | 6.7 (1.4) |
| largest peak component, 4-conn / 8-conn | 0.5% / 99% | 0.6% / 2% | 0.1% / 0.1% | 0.1% / 3% | 0.1% / 0.2% | 0.2% / 0.3% | 0.2% / 0.2% | 0.4% / 0.5% |
| pit blob mean px (< mean−1σ; shuffled) | 1.6 (1.5) | 3.0 (1.6) | 3.9 (1.4) | 3.3 (1.3) | 6.6 (1.4) | 5.6 (1.4) | 6.3 (1.5) | 8.8 (1.4) |

How to read the tiling row: a seamless tile has a seam correlation close to the interior lag-1 correlation. A non-tiling one drops to about 0, the value for unrelated columns.

How to read the peaks rows: noise percolates under 8-connectivity only because 51% of its pixels sit at 252, and its 4-connectivity numbers equal the shuffled baseline, so it has no spatial structure. Every scanned paper has peak and pit blobs 2–6× larger than shuffled, but no component exceeds 0.6% of the peak area. They are **isolated islands (specks / short streaks), not a connected ridge network**, even for cold-press names like Cotman and Langton. In the scans the pits are larger than the peaks (mean 3.9–8.8 px against 2.5–6.7 px): dark, elongated valleys sit inside a mostly bright, often clipped field.

## 2. Interpretation

- **`noise` (the pencil default) is plain i.i.d. white noise, not blue noise and not value noise with octaves.**
  - Lag-1 autocorrelation is 0.000 in both axes, the spectrum is flat (slope ≈ 0, 95% of the energy above f = 64), and it is isotropic.
  - Its histogram is a 19-step staircase, 252 − 8k for k = 0…18.
    - 51% of pixels sit at 252, where the tooth is untouched.
    - The rest decays like a half-Gaussian down to 108, with 6.8% clipped at 108.
    - Closed-form approximation (checked): v = 252 − 8·clamp(round(max(0, X)), 0, 18) with X ~ N(0, 10.5). Its total L1 histogram error is 0.08 and it puts 4.8% at the 108 floor against the observed 6.8%, so the real tail is heavier. Use the exact table (section 4) and treat the formula only as a description.
  - In use (if the modulation is multiplicative, which is unverified), half the pixels are fully receptive and the other half scale the deposit by 0.42–0.97. The result is a fine, 1-device-pixel (≈0.1 mm) "salt" grain that only shows in light, low-pressure strokes. It does not read as a paper structure.
  - One artefact: vertical autocorrelation is 0.108 at lags 8, 16, 24… and −0.035 at the even lags in between. Rows 8 apart are 4096 samples apart in raster order, so this is a weak PRNG with a short low-bit period (an LCG). The bands are invisible and we do not reproduce them.
- **`paper` is the odd one out.** It is the only non-scan texture: a heavily posterised (13 levels, about 4-bit), near-Gaussian field with a 1/f spectrum.
  - It has pixel-scale noise on top of soft blotches up to 2–3 mm, plus a whole-tile brightness gradient (f = 1 holds a large share of the low band, typical of an uneven scan or render).
  - It is mildly anisotropic at the pixel scale (ac1x 0.49 against ac1y 0.34).
  - **It does not tile:** its seam correlation is 0.02 against 0.49 inside.
  - Visually it is a mottled "drawing paper / newsprint" tooth.
- **The 7 named scans** (Cotman, Langton, Mermaid, Montval, Muse Touch, Wargman, i.e. watercolour and pastel papers) share a profile:
  - 3-level quantisation (about 85–95 levels in use) and white clipping at 253, covering 10–32% of pixels.
  - A long dark tail of pits.
  - Spectra flat to about f = 60–90, then a steep fall (slope −3 to −5). They are band-limited at 0.3–1.1 mm bump size, which matches real watercolour tooth at 1:1.
  - All of them are smoother along x than y at the pixel scale, probably from the scanner. On top of that, Muse Touch, Monval, Mermaid and Wargman have strong real grain direction: Muse Touch has horizontal streaks, Wargman a diagonal felt at about 40°.
  - Only Wargman tiles cleanly. Cotman, Langton and Muse Touch tile left to right; Mermaid and Monval do not tile, so a seam grid would show at about 49 mm.
- **For our engine:** the default feel comes from a white-noise salt layer (noise). The scans add a band-limited, anisotropic tooth at 0.3–1 mm with clipped tops.
  - A better model than any single PNG: a band-limited anisotropic field plus a tone curve that clips the tops (a "receptive plateau"), plus an optional fine white layer.
  - Generate everything tileable through wrap-around filtering. Most of their scans fail that.

## 3. Procedural recipes and verification

Both recipes use the same algorithm in Python (`scripts/synth.py`, `gen.py`) and in the JS below:

1. Mulberry32 seeded uniform noise.
2. Separable Gaussian blur with **wrap-around indexing** (so the result tiles).
3. Weighted sum of unit-variance octaves.
4. **Rank-based tone map** onto the original's exact level/probability table, which matches the histogram exactly.

**noise:** per-pixel i.i.d. uniform, then an inverse-CDF lookup into the 19-entry table. No spatial filtering.

**paper:** h = Σ aₖ·norm(blur(white, σx,k, σy,k)), with these octaves:

| σx | σy | amplitude |
|---|---|---|
| 0 (raw white) | 0 | 0.12 |
| 0.58 | 0.45 | 0.85 |
| 1.1 | 1 | 0.15 |
| 2.2 | 2 | 0.28 |
| 4.4 | 4 | 0.20 |
| 8.8 | 8 | 0.20 |
| 17 | 16 | 0.17 |

Then rank-map h onto the 13-level table. Octave weights were seeded by a log-spectrum least-squares fit (`fit_paper.py`) and then tuned by hand over 6 iterations against the autocorrelation lags and band energies.

### Original vs generated (`scripts/final_compare.txt`)

| metric | noise orig | noise gen | paper orig | paper gen |
|---|---|---|---|---|
| mean / std | 219.33 / 45.78 | 219.33 / 45.78 | 181.70 / 37.68 | 181.70 / 37.68 |
| p1 / p5 / p25 / p50 / p75 / p95 / p99 | 108/108/196/252/252/252/252 | identical | 89/122/158/190/207/239/255 | identical |
| skew | −1.292 | −1.292 | −0.448 | −0.448 |
| ac1 x / y | 0.000 / 0.002 | −0.001 / 0.000 | 0.494 / 0.343 | 0.523 / 0.334 |
| ac2 x / y | −0.002 / −0.036 | 0.001 / 0.000 | 0.219 / 0.155 | 0.226 / 0.187 |
| ac4 x / y | 0.002 / −0.040 | −0.002 / 0.007 | 0.149 / 0.134 | 0.139 / 0.133 |
| ac8 x / y | −0.002 / 0.108 (PRNG artefact) | 0.004 / −0.001 | 0.078 / 0.102 | 0.086 / 0.073 |
| dominant f, peak of f·P(f) over f ≥ 2 (cyc/512) | 254 | 255 | 9 (57 px period) | 7 (73 px) |
| spectral centroid over f ≥ 2 | 112 | 124 | 39.6 | 33.9 |
| spectral orientation peak / anisotropy | (isotropic) | (isotropic) | 67.5° / 1.86 | 107.5° / 1.74 |
| slope 4–128 / 128–255 | −0.05 / −0.12 | −0.05 / 0.03 | −1.19 / −1.45 | −1.25 / −1.40 |
| energy lo / mid / hi | 0.5 / 4.2 / 95.3% | 0.4 / 4.7 / 95.0% | 12.1 / 19.1 / 68.8% | 11.0 / 18.2 / 70.9% |
| local contrast σ1 / σ2 / σ4 / σ8 | 39.96 / 44.45 / 45.48 / 45.71 | 39.96 / 44.40 / 45.44 / 45.70 | 25.67 / 31.32 / 34.01 / 35.51 | 25.80 / 31.57 / 34.14 / 35.59 |
| anisotropy ratio | 1.23 | 1.07 | 1.86 | 1.74 |
| peak blob mean px / pit blob mean px | 8.25 / 1.56 | 8.14 / 1.55 | 2.93 / 3.03 | 3.25 / 3.18 |
| seam corr L–R / T–B | −0.08 / 0.07 | −0.01 / 0.08 | 0.02 / 0.11 (no tile) | **0.56 / 0.35 (tiles)** |

How close the match is:

- Histogram, mean, std and all percentiles match exactly, by construction.
- Local contrast at every scale is within 1%.
- Band energies are within 1–2 points.
- Dominant frequency for paper: the f·P(f) curve is almost flat (0.56–0.87 of its max from f = 4 to 128, because slope ≈ −1), so its argmax is weakly defined. The peaks are 9 vs 7 and the centroids 39.6 vs 33.9 (−14%). The generated tile has slightly less mid-band (f 16–128) energy relative to f ≈ 4. The scale metric that is well defined, the ac = 0.5 half-width, agrees: 1.08 / 0.75 px vs 0.99 / 0.76 px. Removing a best-fit plane from the original changes none of these numbers.
- Orientation for paper: the original's weak spectral peak sits at 67.5°, ours at 107.5° (mirrored about vertical). At an anisotropy ratio under 2 the angle is poorly defined, and our octaves are axis-aligned only (σx > σy). Rotating the two smallest octaves would match it if it matters.
- Autocorrelation is within ±0.03, except paper ac8y (0.073 against 0.102). The missing low-frequency energy is mostly the scan gradient in the original, which we deliberately leave out.
- Our paper tiles; theirs does not.

### Image files

All in `studio/graphite/research/13-textures/`:

- `gen_noise.png`, `gen_paper.png`: the generated 512² tiles. They are ours and can ship.
- `gen_noise_tilecheck.png`, `gen_paper_tilecheck.png`: 2×2 tiled, centre crop with the seams in the middle.
- `comparison_noise_paper.png`: original | generated | original 4× crop | generated 4× crop.
- `contact_sheet.png`: 256² crops of all 8 originals plus both generated textures. It contains their material, so it is for research only and must not ship.

## 4. JavaScript (untested)

```js
// Tileable paper height map. Returns Float32Array(size*size), 0..1 (1 = tooth top, full deposit).
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);
  t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}

const TONES = {
  // level (0..255) and probability, measured from the reference histograms
  noise: { L:[108,116,124,132,140,148,156,164,172,180,188,196,204,212,220,228,236,244,252],
           P:[.068,.0076,.0099,.0109,.0129,.0157,.0168,.0193,.0203,.022,.0273,.0267,.0334,.0396,.0403,.0432,.0386,.0379,.5096] },
  paper: { L:[65,73,89,105,122,138,158,174,190,207,223,239,255],
           P:[.0041,.0055,.0128,.0259,.0493,.0847,.1243,.1644,.178,.1602,.1102,.0555,.025] },
};
const OCTAVES = { // [sigmaX, sigmaY, amplitude]
  noise: [[0,0,1]],
  paper: [[0,0,.12],[.58,.45,.85],[1.1,1,.15],[2.2,2,.28],[4.4,4,.2],[8.8,8,.2],[17,16,.17]],
};

function blur1D(src, dst, n, sigma, horizontal){
  if (sigma <= 0) { dst.set(src); return; }
  const R = Math.ceil(3*sigma), k = new Float32Array(2*R+1); let s = 0;
  for (let i=-R;i<=R;i++){ k[i+R]=Math.exp(-i*i/(2*sigma*sigma)); s+=k[i+R]; }
  for (let i=0;i<k.length;i++) k[i]/=s;
  for (let y=0;y<n;y++) for (let x=0;x<n;x++){
    let acc=0;
    for (let i=-R;i<=R;i++){
      const xx = horizontal ? ((x+i)%n+n)%n : x, yy = horizontal ? y : ((y+i)%n+n)%n; // wrap => tileable
      acc += k[i+R]*src[yy*n+xx];
    }
    dst[y*n+x]=acc;
  }
}

function paperHeightMap(kind='paper', seed=1, n=512){
  const rnd = mulberry32(seed), N = n*n, h = new Float32Array(N);
  const a = new Float32Array(N), b = new Float32Array(N), c = new Float32Array(N);
  for (const [sx, sy, amp] of OCTAVES[kind]){
    for (let i=0;i<N;i++) a[i]=rnd()-0.5;
    blur1D(a,b,n,sx,true); blur1D(b,c,n,sy,false);
    let m=0,v=0; for (let i=0;i<N;i++){m+=c[i];v+=c[i]*c[i];} m/=N; const sd=Math.sqrt(v/N-m*m)||1;
    for (let i=0;i<N;i++) h[i]+=amp*(c[i]-m)/sd;
  }
  // rank-based tone map: exact histogram match (for i.i.d. noise this equals an inverse-CDF lookup)
  const {L,P} = TONES[kind], idx = new Uint32Array(N);
  for (let i=0;i<N;i++) idx[i]=i;
  idx.sort((i,j)=>h[i]-h[j]);
  const out = new Float32Array(N); let start=0, cum=0, tot=P.reduce((s,p)=>s+p,0);
  for (let l=0;l<L.length;l++){
    cum += P[l]; const end = l===L.length-1 ? N : Math.round(cum/tot*N);
    for (let r=start;r<end;r++) out[idx[r]] = L[l]/255;
    start = end;
  }
  return out;
}
```

Notes for our engine:

- The naive blur above costs about 75 M multiply-adds for σ = 17, which is fine once at load. Generating the σ ≥ 8 octaves at 1/4 resolution and upsampling would be faster.
- For a "better than theirs" paper:
  - Drop the 13-level posterisation and keep `h` continuous through a smooth tone curve. The 4-bit steps in `paper` can band in light shading.
  - Add a band-limited anisotropic tooth octave at 0.3–1 mm (σ ≈ 2–5 px at 264 ppi, σx/σy ≈ 1.5–3 at a chosen angle) with a clipped top plateau of 10–30%. That reproduces the scanned watercolour family.
  - Our own scans should be made tileable (wrap blending) and scaled to 0.096 mm/px.
