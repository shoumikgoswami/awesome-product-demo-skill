import {Easing, interpolate, staticFile} from 'remotion';

export const ease = Easing.bezier(0.4, 0, 0.2, 1);

export const ramp = (f: number, a: number, b: number) =>
  interpolate(f, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});

export const lin = (f: number, a: number, b: number) =>
  interpolate(f, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

export const asset = (dir: string, p: string) => staticFile(`${dir}/${p}`);

export const hexToRgba = (hex: string, a: number) => {
  const h = hex.replace('#', '');
  const n = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const r = parseInt(n.slice(0, 2), 16);
  const g = parseInt(n.slice(2, 4), 16);
  const b = parseInt(n.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
};

// Layout of the window card, derived from the most common screenshot aspect ratio so the card never jumps between scenes.
export const CARD_MAX_W = 1840;
export const CARD_MAX_H = 790;
export const CARD_Y = 150;

export const cardLayout = (sizes: {w: number; h: number}[]) => {
  const counts = new Map<number, {n: number; exact: number}>();
  sizes.forEach((s) => {
    const k = Math.round((s.w / s.h) * 20) / 20;
    const cur = counts.get(k);
    counts.set(k, {n: (cur?.n ?? 0) + 1, exact: cur?.exact ?? s.w / s.h});
  });
  let aspect = 16 / 9;
  let best = 0;
  counts.forEach((c) => {
    if (c.n > best) {
      best = c.n;
      aspect = c.exact; // exact aspect of the most common size, so same-size screenshots fill the card with no letterbox
    }
  });
  let w = Math.min(CARD_MAX_W, CARD_MAX_H * aspect);
  let h = w / aspect;
  w = Math.round(w);
  h = Math.round(h);
  return {x: Math.round((1920 - w) / 2), y: CARD_Y, w, h};
};

export const fitInside = (iw: number, ih: number, cw: number, ch: number) => {
  const s = Math.min(cw / iw, ch / ih);
  const w = iw * s;
  const h = ih * s;
  return {w, h, x: (cw - w) / 2, y: (ch - h) / 2};
};
