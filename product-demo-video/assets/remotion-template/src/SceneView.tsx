import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, useCurrentFrame} from 'remotion';
import type {Focus, Scene, Theme} from './types';
import {asset, ease, fitInside, hexToRgba, lin, ramp} from './utils';

type Card = {x: number; y: number; w: number; h: number};

// Where the pointer rests inside a focus box: a little right of and below the centre so it does not cover the label.
export const clickPoint = (fo: {x: number; y: number; w: number; h: number}) => ({x: fo.x + fo.w * 0.58, y: fo.y + fo.h * 0.66});

const focusWeight = (f: number, fo: Focus, fps: number) => {
  const inF = Math.round(0.7 * fps);
  const outF = Math.round(0.7 * fps);
  return ramp(f, fo.frame, fo.frame + inF) * (1 - ramp(f, fo.frame + inF + fo.hold, fo.frame + inF + fo.hold + outF));
};

export const SceneView: React.FC<{
  scene: Scene;
  index: number;
  lead: number; // frames this Sequence starts before scene.start (incoming transition)
  card: Card;
  dir: string;
  theme: Theme;
  fps: number;
  next?: {transition: Scene['transition']; frames: number} | null; // how the following scene arrives (drives this scene's exit)
}> = ({scene, lead, card, dir, theme, fps, next}) => {
  const local = useCurrentFrame();
  const f = local - lead; // scene-relative frame, negative while transitioning in
  const c = theme.colors;
  const cw = card.w;
  const ch = card.h;

  // Transition in/out ----------------------------------------------------------------
  const T = scene.transitionFrames;
  const inP = lead > 0 ? lin(local, 0, T) : 1;
  let opacity = 1;
  let tx = 0;
  if (lead > 0) {
    if (scene.transition === 'crossfade') opacity = ease(inP);
    if (scene.transition === 'push') {
      tx = (1 - ease(inP)) * cw;
      opacity = 1;
    }
  }

  if (next && next.transition === 'push' && next.frames > 0) {
    const exitP = ease(lin(f, scene.duration - next.frames, scene.duration));
    tx = -exitP * cw * 0.28;
    opacity = Math.min(opacity, 1 - 0.7 * exitP);
  }

  // Image placement ---------------------------------------------------------------------
  const isImage = scene.kind === 'image' && scene.image && scene.imageSize;
  const box = isImage ? fitInside(scene.imageSize!.w, scene.imageSize!.h, cw, ch) : {x: 0, y: 0, w: cw, h: ch};
  const letterboxed = isImage && (Math.abs(box.w - cw) > 2 || Math.abs(box.h - ch) > 2);

  // Zoom / pan from the focus list ---------------------------------------------------------
  const weights = scene.focus.map((fo) => focusWeight(f, fo, fps));
  const wsum = weights.reduce((a, b) => a + b, 0);
  const norm = wsum > 1 ? 1 / wsum : 1;
  let z = 1;
  let fx = cw / 2;
  let fy = ch / 2;
  scene.focus.forEach((fo, i) => {
    const w = weights[i];
    z += w * (fo.zoom - 1);
    fx += w * norm * (box.x + (fo.x + fo.w / 2) * box.w - cw / 2);
    fy += w * norm * (box.y + (fo.y + fo.h / 2) * box.h - ch / 2);
  });
  const halfW = cw / (2 * z);
  const halfH = ch / (2 * z);
  const clampAxis = (v: number, half: number, o: number, len: number) => {
    const lo = o + half;
    const hi = o + len - half;
    return lo > hi ? o + len / 2 : Math.min(hi, Math.max(lo, v));
  };
  fx = clampAxis(fx, halfW, box.x, box.w);
  fy = clampAxis(fy, halfH, box.y, box.h);
  const tX = cw / 2 - fx * z;
  const tY = ch / 2 - fy * z;

  // Cursor (screen space) ------------------------------------------------------------------
  const cursorFocus = scene.focus.filter((fo) => fo.click || fo.cursor);
  const toLayer = (px: number, py: number) => ({x: box.x + px * box.w, y: box.y + py * box.h});
  const toScreen = (px: number, py: number) => {
    const p = toLayer(px, py);
    return {x: tX + p.x * z, y: tY + p.y * z};
  };
  let cursor: {x: number; y: number; vis: number; press: number; ripple: number; rx: number; ry: number} | null = null;
  if (cursorFocus.length) {
    const moveF = Math.round(0.9 * fps);
    const first = cursorFocus[0];
    const target0 = clickPoint(first);
    const start = scene.cursorStart ?? {
      x: Math.min(0.95, target0.x + 0.14),
      y: Math.min(0.95, target0.y + 0.16),
    };
    let pos = start;
    let arrive = -1e9;
    let prevEnd = 0;
    let press = 1;
    let ripple = 0;
    let rx = 0;
    let ry = 0;
    cursorFocus.forEach((fo) => {
      const tgt = clickPoint(fo);
      const arrF = fo.frame + Math.round(0.7 * fps); // arrives when the zoom lands
      const startF = Math.max(prevEnd, arrF - moveF);
      const u = ramp(f, startF, arrF);
      if (f >= startF) {
        const dx = tgt.x - pos.x;
        const dy = tgt.y - pos.y;
        const bow = Math.sin(Math.PI * u) * 0.035;
        // perpendicular bow gives a natural curved glide
        const len = Math.hypot(dx, dy) || 1;
        const cx = pos.x + dx * u - (dy / len) * bow;
        const cy = pos.y + dy * u + (dx / len) * bow;
        if (f >= arrF) pos = tgt;
        else pos = {x: cx, y: cy};
      }
      if (fo.click) {
        const d = f - arrF;
        if (d >= 0 && d < 0.5 * fps) {
          ripple = lin(d, 0, 0.5 * fps);
          rx = tgt.x;
          ry = tgt.y;
        }
        if (d >= 0 && d < 0.2 * fps) press = 1 - 0.18 * Math.sin((Math.PI * d) / (0.2 * fps));
      }
      prevEnd = arrF;
      arrive = arrF;
    });
    const vis = scene.cursorStart ? 1 : lin(f, cursorFocus[0].frame - moveF, cursorFocus[0].frame - moveF + 6);
    const sp = toScreen(pos.x, pos.y);
    cursor = {x: sp.x, y: sp.y, vis, press, ripple, rx, ry};
    void arrive;
  }

  const borderW = 6 / z;

  return (
    <AbsoluteFill style={{opacity, transform: `translateX(${tx}px)`, background: c.card}}>
      {letterboxed ? (
        <Img
          src={asset(dir, scene.image!)}
          style={{position: 'absolute', inset: 0, width: cw, height: ch, objectFit: 'cover', filter: 'blur(42px) brightness(0.65)', transform: 'scale(1.25)'}}
        />
      ) : null}
      <div style={{position: 'absolute', left: 0, top: 0, width: cw, height: ch, transformOrigin: '0 0', translate: `${tX}px ${tY}px`, scale: String(z)}}>
        {isImage ? (
          <Img src={asset(dir, scene.image!)} style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h}} />
        ) : scene.clip ? (
          <OffthreadVideo
            src={asset(dir, scene.clip.src)}
            trimBefore={scene.clip.fromFrame}
            trimAfter={scene.clip.toFrame}
            muted
            style={{position: 'absolute', left: 0, top: 0, width: cw, height: ch, objectFit: 'contain'}}
          />
        ) : null}

        {/* privacy blur */}
        {scene.blur.map((b, i) => {
          const p = toLayer(b.x, b.y);
          return (
            <div
              key={`b${i}`}
              style={{
                position: 'absolute',
                left: p.x,
                top: p.y,
                width: b.w * box.w,
                height: b.h * box.h,
                backdropFilter: 'blur(24px) brightness(0.8)',
                WebkitBackdropFilter: 'blur(24px) brightness(0.8)',
              }}
            />
          );
        })}

        {/* typed text */}
        {scene.type.map((t, i) => {
          const p = toLayer(t.x, t.y);
          const chars = Math.floor(Math.max(0, f - t.frame) / (fps / 18));
          const shown = t.text.slice(0, chars);
          const caret = Math.floor(f / (fps / 2)) % 2 === 0 || chars < t.text.length;
          return f >= t.frame - 4 ? (
            <div
              key={`t${i}`}
              style={{
                position: 'absolute',
                left: p.x,
                top: p.y,
                width: t.w * box.w,
                height: t.h * box.h,
                background: t.fill,
                color: t.color,
                fontSize: t.size,
                display: 'flex',
                alignItems: 'center',
                paddingLeft: 12,
                fontWeight: 500,
                whiteSpace: 'pre',
                overflow: 'hidden',
              }}
            >
              {shown}
              <span style={{opacity: caret ? 1 : 0, marginLeft: 2}}>|</span>
            </div>
          ) : null;
        })}

        {/* callouts: a cropped copy of a region pops forward */}
        {isImage
          ? scene.callouts.map((co, i) => {
              const inP = ramp(f, co.frame, co.frame + 10);
              const outP = 1 - ramp(f, co.frame + 10 + co.hold, co.frame + 20 + co.hold);
              const k = Math.min(inP, outP);
              if (k <= 0) return null;
              const p = toLayer(co.x, co.y);
              const w = co.w * box.w;
              const h = co.h * box.h;
              return (
                <div
                  key={`c${i}`}
                  style={{
                    position: 'absolute',
                    left: p.x,
                    top: p.y,
                    width: w,
                    height: h,
                    overflow: 'hidden',
                    borderRadius: 10,
                    opacity: k,
                    transformOrigin: 'center',
                    transform: `scale(${1 + (co.scale - 1) * k})`,
                    boxShadow: `0 18px 50px ${hexToRgba('#000', 0.45)}, 0 0 0 ${borderW}px ${c.accent}`,
                  }}
                >
                  <Img
                    src={asset(dir, scene.image!)}
                    style={{position: 'absolute', left: -co.x * box.w, top: -co.y * box.h, width: box.w, height: box.h, maxWidth: 'none'}}
                  />
                </div>
              );
            })
          : null}

        {/* highlight boxes */}
        {scene.focus.map((fo, i) => {
          if (fo.highlight === false || fo.w <= 0 || fo.h <= 0) return null;
          const w = weights[i];
          if (w <= 0.01) return null;
          const p = toLayer(fo.x, fo.y);
          const pulse = 0.5 + 0.5 * Math.sin((f / fps) * Math.PI * 2 * 1.2);
          return (
            <div
              key={`h${i}`}
              style={{
                position: 'absolute',
                left: p.x - 6 / z,
                top: p.y - 6 / z,
                width: fo.w * box.w + 12 / z,
                height: fo.h * box.h + 12 / z,
                borderRadius: 16 / Math.max(1, z * 0.7),
                border: `${borderW}px solid ${c.accent}`,
                opacity: Math.min(1, w * 1.4),
                boxShadow: `0 0 ${(14 + 18 * pulse) / z}px ${hexToRgba(c.accent, 0.35 + 0.35 * pulse)}`,
              }}
            />
          );
        })}
      </div>

      {/* cursor */}
      {cursor ? (
        <>
          {cursor.ripple > 0 ? (
            <div
              style={{
                position: 'absolute',
                left: toScreen(cursor.rx, cursor.ry).x - 50,
                top: toScreen(cursor.rx, cursor.ry).y - 50,
                width: 100,
                height: 100,
                borderRadius: 50,
                border: `4px solid ${c.accent}`,
                opacity: 0.7 * (1 - cursor.ripple),
                transform: `scale(${0.2 + 0.8 * ease(cursor.ripple)})`,
              }}
            />
          ) : null}
          <svg
            width="44"
            height="44"
            viewBox="0 0 24 24"
            style={{
              position: 'absolute',
              left: cursor.x - 4,
              top: cursor.y - 2,
              opacity: cursor.vis,
              transform: `scale(${cursor.press})`,
              transformOrigin: '4px 2px',
              filter: 'drop-shadow(0 3px 5px rgba(0,0,0,0.45))',
            }}
          >
            <path d="M4 2 L4 19 L8.6 14.8 L11.6 21.6 L14.4 20.4 L11.4 13.7 L17.6 13.5 Z" fill="#ffffff" stroke="#111827" strokeWidth="1.3" strokeLinejoin="round" />
          </svg>
        </>
      ) : null}

      {/* chips */}
      {scene.chips.map((chip, i) => {
        const k = Math.min(lin(f, chip.start, chip.start + 9), 1 - lin(f, chip.end - 9, chip.end));
        if (k <= 0) return null;
        return (
          <div
            key={`chip${i}`}
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: 28,
              display: 'flex',
              justifyContent: 'center',
              opacity: k,
              transform: `translateY(${(1 - k) * 14}px)`,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                padding: '12px 28px',
                borderRadius: 40,
                fontSize: 30,
                fontWeight: 600,
                color: theme.mode === 'dark' ? c.text : c.bgDeep,
                background: hexToRgba(theme.mode === 'dark' ? c.bgDeep : c.text, 0.92),
                border: `1.5px solid ${c.accent}`,
              }}
            >
              <span style={{width: 12, height: 12, borderRadius: 6, background: c.accent}} />
              {chip.text}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

