import React from 'react';
import {AbsoluteFill, Img, useCurrentFrame} from 'remotion';
import type {Timeline} from './types';
import {Logo} from './Logo';
import {asset, hexToRgba, lin, ramp} from './utils';

export const Words: React.FC<{text: string; highlight?: string; accent: string; start: number; size: number; weight?: number; gap?: number}> = ({
  text,
  highlight,
  accent,
  start,
  size,
  weight = 700,
  gap = 3,
}) => {
  const f = useCurrentFrame();
  const words = text.split(/\s+/);
  const hl = (highlight ?? '').toLowerCase().split(/\s+/).filter(Boolean);
  const norm = (w: string) => w.toLowerCase().replace(/[^a-z0-9]/g, '');
  const hlSet = new Set(hl.map(norm));
  return (
    <div style={{fontSize: size, fontWeight: weight, lineHeight: 1.08, letterSpacing: -1.5, display: 'flex', flexWrap: 'wrap', columnGap: size * 0.27}}>
      {words.map((w, i) => {
        const k = ramp(f, start + i * gap, start + i * gap + 14);
        return (
          <span key={i} style={{opacity: k, transform: `translateY(${(1 - k) * 34}px)`, color: hlSet.has(norm(w)) ? accent : undefined}}>
            {w}
          </span>
        );
      })}
    </div>
  );
};

export const Intro: React.FC<{timeline: Timeline; dir: string}> = ({timeline, dir}) => {
  const f = useCurrentFrame();
  const {theme, intro, introFrames, scenes} = timeline;
  const c = theme.colors;
  if (!intro) return null;
  const out = 1 - lin(f, introFrames - 10, introFrames);
  const hero = intro.hero ?? scenes.find((s) => s.image)?.image ?? null;
  const heroSize = scenes.find((s) => s.image === hero)?.imageSize ?? {w: 16, h: 9};
  const heroW = 820;
  const heroH = Math.min(620, (heroW * heroSize.h) / heroSize.w);
  const heroK = ramp(f, 14, 44);
  const float = Math.sin(f / 22) * 6;
  const points = (intro.points ?? []).slice(0, 3);

  return (
    <AbsoluteFill style={{opacity: out}}>
      <div style={{position: 'absolute', left: 80, top: 64}}>
        <div style={{opacity: ramp(f, 0, 12)}}>
          <Logo theme={theme} dir={dir} />
        </div>
      </div>
      <div style={{position: 'absolute', left: 80, top: hero ? 250 : 300, width: hero ? 880 : 1500}}>
        {intro.eyebrow ? (
          <div
            style={{
              fontSize: 24,
              fontWeight: 600,
              letterSpacing: 2.4,
              textTransform: 'uppercase',
              color: c.accent,
              marginBottom: 26,
              opacity: ramp(f, 4, 18),
              transform: `translateX(${(1 - ramp(f, 4, 18)) * -24}px)`,
            }}
          >
            {intro.eyebrow}
          </div>
        ) : null}
        <Words text={intro.headline} highlight={intro.highlight} accent={c.accent} start={10} size={hero ? 82 : 96} />
        {intro.subhead ? (
          <div style={{marginTop: 34, fontSize: 32, lineHeight: 1.35, color: c.textMuted, opacity: ramp(f, 46, 64), transform: `translateY(${(1 - ramp(f, 46, 64)) * 16}px)`, maxWidth: 780}}>
            {intro.subhead}
          </div>
        ) : null}
      </div>
      {hero ? (
        <div
          style={{
            position: 'absolute',
            right: 80,
            top: 190 + float,
            width: heroW,
            height: heroH,
            borderRadius: 20,
            overflow: 'hidden',
            opacity: heroK,
            transform: `translateX(${(1 - heroK) * 120}px) scale(${0.95 + 0.05 * heroK})`,
            boxShadow: `0 40px 100px ${hexToRgba('#000', theme.mode === 'dark' ? 0.55 : 0.25)}, 0 0 0 1px ${hexToRgba(c.text, 0.1)}`,
            background: c.card,
          }}
        >
          <Img src={asset(dir, hero)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </div>
      ) : null}
      {points.length ? (
        <div style={{position: 'absolute', left: 80, right: 80, bottom: 70, display: 'flex', gap: 24}}>
          {points.map((p, i) => {
            const k = ramp(f, 70 + i * 8, 86 + i * 8);
            return (
              <div
                key={i}
                style={{
                  flex: 1,
                  padding: '22px 28px',
                  borderRadius: 16,
                  fontSize: 26,
                  fontWeight: 500,
                  lineHeight: 1.3,
                  background: hexToRgba(c.text, 0.07),
                  border: `1px solid ${hexToRgba(c.text, 0.14)}`,
                  borderLeft: `5px solid ${c.accent}`,
                  opacity: k,
                  transform: `translateY(${(1 - k) * 24}px)`,
                }}
              >
                {p}
              </div>
            );
          })}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
