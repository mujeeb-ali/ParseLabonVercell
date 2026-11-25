// Generates src/dark.css from style.css + extra.css.
//
// The light theme hard-codes a few hundred colors, so instead of maintaining a
// second hand-written palette, every color declaration is re-emitted under
// :root[data-theme="dark"] with its lightness flipped (hue kept, light tints
// become dark tints). Saturated accents (orange, lime, olive) are kept, and
// components that are already dark in the light theme are left alone.
// Runs automatically before `npm run dev` and `npm run build`.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const src = join(dirname(fileURLToPath(import.meta.url)), '..', 'src');
const INPUTS = ['style.css', 'extra.css'];
const SCOPE = ':root[data-theme="dark"]';
// Already-dark components: keep them as they are in both themes.
const KEEP_AS_IS = /pipeline|flow-|brand-mark|live-mark|toast/;
const COLOR_PROPS = /^(--|color$|background|border|outline|fill$|stroke$|caret-color$|accent-color$|text-decoration-color$|column-rule)/;

// ---- color math -----------------------------------------------------------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
function parseHex(h) {
  h = h.slice(1);
  if (h.length === 3 || h.length === 4) h = [...h].map((c) => c + c).join('');
  const n = (i) => parseInt(h.slice(i, i + 2), 16);
  return { r: n(0), g: n(2), b: n(4), a: h.length === 8 ? n(6) / 255 : 1 };
}
function rgbToHsl({ r, g, b }) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2;
  if (max === min) return { h: 0, s: 0, l };
  const d = max - min, s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return { h: h / 6, s, l };
}
function hslToRgb({ h, s, l }) {
  if (s === 0) return { r: l * 255, g: l * 255, b: l * 255 };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  const f = (t) => { t = (t + 1) % 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p; };
  return { r: f(h + 1 / 3) * 255, g: f(h) * 255, b: f(h - 1 / 3) * 255 };
}
const hex2 = (v) => Math.round(clamp(v, 0, 255)).toString(16).padStart(2, '0');
function toDark(rgba) {
  const hsl = rgbToHsl(rgba);
  const accent = hsl.s >= 0.45 && hsl.l >= 0.3 && hsl.l <= 0.75;
  let out = hsl;
  if (!accent) {
    // Map lightness 1 → 0.10 (page) and 0 → 0.92 (text), slightly compressed.
    const l = 0.1 + (1 - hsl.l) * 0.82;
    const s = hsl.l > 0.8 ? Math.min(hsl.s * 0.45, 0.1) : Math.min(hsl.s, 0.4);
    out = { h: hsl.h, s, l };
  }
  const { r, g, b } = hslToRgb(out);
  return { r, g, b, a: rgba.a };
}
const fmt = ({ r, g, b, a }) => (a >= 1 ? `#${hex2(r)}${hex2(g)}${hex2(b)}` : `rgba(${Math.round(r)},${Math.round(g)},${Math.round(b)},${+a.toFixed(3)})`);

function transformValue(v) {
  return v
    .replace(/#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b/g, (m) => fmt(toDark(parseHex(m))))
    .replace(/rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)(?:[ ,/]+([\d.]+))?\s*\)/g, (_, r, g, b, a) => fmt(toDark({ r: +r, g: +g, b: +b, a: a === undefined ? 1 : +a })))
    .replace(/\b(white|black)\b/g, (m) => fmt(toDark(m === 'white' ? { r: 255, g: 255, b: 255, a: 1 } : { r: 0, g: 0, b: 0, a: 1 })));
}

// ---- tiny CSS parser --------------------------------------------------------
function splitTop(s, sep) {
  const out = []; let depth = 0, cur = '', quote = null;
  for (const ch of s) {
    if (quote) { cur += ch; if (ch === quote) quote = null; continue; }
    if (ch === '"' || ch === "'") { quote = ch; cur += ch; continue; }
    if (ch === '(') depth++; else if (ch === ')') depth--;
    if (ch === sep && depth === 0) { out.push(cur); cur = ''; } else cur += ch;
  }
  if (cur.trim()) out.push(cur);
  return out;
}
function parse(css) {
  css = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const nodes = []; let i = 0;
  while (i < css.length) {
    while (i < css.length && /\s/.test(css[i])) i++;
    if (css.startsWith('@import', i) || css.startsWith('@charset', i)) {
      // Statement at-rule: skip to the first ';' outside parentheses / quotes.
      let depth = 0, quote = null, j = i;
      for (; j < css.length; j++) {
        const ch = css[j];
        if (quote) { if (ch === quote) quote = null; continue; }
        if (ch === '"' || ch === "'") quote = ch;
        else if (ch === '(') depth++;
        else if (ch === ')') depth--;
        else if (ch === ';' && depth === 0) break;
      }
      i = j + 1;
      continue;
    }
    const open = css.indexOf('{', i);
    if (open === -1) break;
    const head = css.slice(i, open).trim();
    let depth = 1, j = open + 1;
    while (j < css.length && depth) { if (css[j] === '{') depth++; else if (css[j] === '}') depth--; j++; }
    const body = css.slice(open + 1, j - 1);
    if (head.startsWith('@media') || head.startsWith('@supports')) nodes.push({ at: head, children: parse(body) });
    else if (!head.startsWith('@')) nodes.push({ selector: head, body });
    i = j;
  }
  return nodes;
}
function scopeSelector(sel) {
  return splitTop(sel, ',').map((s) => {
    s = s.trim();
    if (s.startsWith(':root')) return SCOPE + s.slice(5);
    if (/^html\b/.test(s)) return SCOPE + s.slice(4);
    return `${SCOPE} ${s}`;
  }).join(',');
}
function emit(nodes) {
  let out = '';
  for (const n of nodes) {
    if (n.at) { const inner = emit(n.children); if (inner) out += `${n.at}{${inner}}\n`; continue; }
    if (KEEP_AS_IS.test(n.selector)) continue;
    const decls = [];
    for (const d of splitTop(n.body, ';')) {
      const k = d.indexOf(':'); if (k === -1) continue;
      const prop = d.slice(0, k).trim(), val = d.slice(k + 1).trim();
      if (!COLOR_PROPS.test(prop) || /shadow/.test(prop)) continue;
      const nv = transformValue(val);
      // Re-emit every colour declaration, changed or not (e.g. accents), so the
      // dark rules keep the same relative cascade order as the light ones.
      if (nv !== val || /#[0-9a-fA-F]{3,8}\b|rgba?\(|\b(white|black)\b|var\(--/.test(val)) decls.push(`${prop}:${nv}`);
    }
    if (decls.length) out += `${scopeSelector(n.selector)}{${decls.join(';')}}\n`;
  }
  return out;
}

let output = '/* GENERATED by scripts/gen-dark-theme.mjs from style.css and extra.css. Do not edit by hand. */\n';
output += `${SCOPE}{color-scheme:dark}\n`;
for (const f of INPUTS) output += `/* from ${f} */\n` + emit(parse(readFileSync(join(src, f), 'utf8')));

// Hand-tuned exceptions where a pure lightness flip reads badly.
const S = SCOPE;
output += `/* manual dark-theme adjustments */
${S} .nav-item.active{background:#3a3932;color:#f3f2ec;box-shadow:inset 2px 0 0 #df553a}
${S} .nav-item.active svg{color:#cce36d}
${S} .button.primary{color:#fff}
${S} .theme-toggle button.on,${S} .seg button.on,${S} .mode-toggle button.on,${S} .view-toggle button.on{background:#e9e7de!important;color:#1d1c18!important}
${S} .automata-graph-scroll,${S} .tree-canvas{background:#1d1c18;border-color:#3a3932}
${S} .tree-svg .tn.nt rect{fill:#3b4223;stroke:#a7b56a}
${S} .tree-svg .tn.nt text{fill:#e4ebc4}
${S} .tree-svg .tn.term rect{fill:#262520;stroke:#a9a79a}
${S} .tree-svg .tn.term text{fill:#efeee6}
${S} .tree-svg .tn.eps text{fill:#9d9b90}
${S} .tree-svg .tn.matched rect{fill:#2e3420;stroke:#a7b56a}
${S} .tree-svg .tn.pending rect{fill:#22211c!important;stroke:#6d6b61!important}
${S} .tree-svg .tn.pending text{fill:#9d9b90!important}
${S} .tree-svg .te{stroke:#8f8d80}
${S} .tree-svg .te.pending{stroke:#55534b!important}
${S} .tree-svg .tn.hot rect{fill:#df553a;stroke:#ff8a6b}
${S} .tree-svg .tn.hot text{fill:#fff}
${S} .automata-graph .ag-node circle{fill:#262520;stroke:#cfcdc2}
${S} .automata-graph .ag-node text{fill:#f0efe8}
${S} .automata-graph .ag-node.accept circle{fill:#2e3420;stroke:#b5c46f}
${S} .automata-graph .ag-node .ring{stroke:#b5c46f!important}
${S} .automata-graph .ag-node.on circle{fill:#4a2a20;stroke:#ff8a6b}
${S} .automata-graph .ag-node.end circle{fill:#df553a;stroke:#ff8a6b}
${S} .automata-graph .ag-node.end text{fill:#fff}
${S} .automata-graph .ag-edge path{stroke:#b9b7ab}
${S} .automata-graph .mk{fill:#b9b7ab}
${S} .automata-graph .ag-edge.eps path{stroke:#7e7c71}
${S} .automata-graph .mk.eps{fill:#7e7c71}
${S} .automata-graph .ag-edge.hot path{stroke:#ff7a57}
${S} .automata-graph .mk.hot{fill:#ff7a57}
${S} .automata-graph .ag-label{fill:#f0efe8;stroke:#1d1c18}
${S} .automata-graph .ag-edge.eps .ag-label{fill:#a9a79a}
${S} .automata-graph .ag-edge.hot .ag-label{fill:#ff9b7f}
${S} .ag-legend i{background:#262520;border-color:#cfcdc2}
${S} .ag-legend i.lg-start{background:#df553a;border:0}
${S} .ag-legend i.lg-accept{border-color:#b5c46f;background:#2e3420;box-shadow:inset 0 0 0 2px #2e3420,inset 0 0 0 3.5px #b5c46f}
${S} .ag-legend i.lg-eps{background:transparent;border-top-color:#7e7c71}
${S} .ag-legend i.lg-hot{border-color:#ff8a6b;background:#df553a}
${S} .ag-legend i.lg-nt{border-color:#a7b56a;background:#3b4223}
${S} .ag-legend i.lg-t{border-color:#a9a79a;background:#262520}
${S} .ag-legend i.lg-pend{border-color:#6d6b61;background:transparent}
${S} .ag-legend b{color:#f0efe8}
`;
writeFileSync(join(src, 'dark.css'), output);
console.log(`dark.css: ${output.split('\n').length} rules`);
