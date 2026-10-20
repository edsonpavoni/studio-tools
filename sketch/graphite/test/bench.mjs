// bench.mjs — microseconds per dab and per pointer event, per tool.
//   node test/bench.mjs
import { performance } from "node:perf_hooks";
import { createEngine } from "../engine/engine.js";

const eng = createEngine({ width: 2732, height: 2048, paper: "noise" });
const DEG = Math.PI / 180;
const cases = [
  ["HB", 0.5, 90], ["HB", 1.0, 90], ["HB", 0.5, 25], ["4B", 0.8, 90], ["4B", 0.6, 20],
  ["2H", 0.5, 90], ["eraser", 0.7, 90], ["kneaded", 0.7, 90], ["smudge", 0.6, 90],
];
console.log("tool   p   alt   µs/dab   µs/event(29px)   dabs/event");
for (const [tool, p, alt] of cases) {
  eng.setTool(tool);
  // 2000 px of travel in 29 px events (one 120 Hz event at ~3.5 km/h), 10 lines
  let dabs = 0, t = 0;
  for (let k = 0; k < 10; k++) {
    const y = 200 + k * 150;
    const t0 = performance.now();
    eng.strokeBegin(100, y, p, alt * DEG, 0);
    for (let x = 129; x <= 2100; x += 29) eng.strokeMove(x, y, p, alt * DEG, 0);
    eng.strokeEnd(2100, y, 0, alt * DEG, 0);
    t += performance.now() - t0;
  }
  // count dabs by replaying the stroke module's counter: approximate via spacing
  const tl = eng.tool;
  const r = tl.kind === "pencil" ? tl.size * (1 + Math.pow(p, tl.k)) / 4 : tl.kind === "smudge" ? tl.size / 2
    : tl.kind === "kneaded" ? tl.size / 4 : tl.size * p / 2;
  const stretch = 1; // along-path spacing uses r, not the stretched axis
  dabs = 10 * 2000 / Math.max(0.5, eng.tool.spacing * r * stretch);
  const events = 10 * 69;
  console.log(`${tool.padEnd(7)}${p.toFixed(1)} ${String(alt).padStart(3)}   ${(t * 1000 / dabs).toFixed(1).padStart(6)}   ${(t * 1000 / events).toFixed(1).padStart(10)}   ${(dabs / events).toFixed(1).padStart(8)}`);
  eng.clear();
}
