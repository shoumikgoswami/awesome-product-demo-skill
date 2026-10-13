import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Words} from './Intro';
import {MONO_STACK} from './font';
import type {Timeline} from './types';
import {Logo} from './Logo';
import {hexToRgba, lin, ramp} from './utils';

export const Outro: React.FC<{timeline: Timeline; dir: string}> = ({timeline, dir}) => {
  const f = useCurrentFrame();
  const {theme, outro, outroFrames} = timeline;
  const c = theme.colors;
  if (!outro) return null;
  const k = Math.min(lin(f, 0, 14), 1 - lin(f, outroFrames - 12, outroFrames));
  const cards = (outro.cards ?? []).slice(0, 3);
  const pills = (outro.pills ?? []).slice(0, 4);
  return (
    <AbsoluteFill style={{opacity: k}}>
      <div style={{position: 'absolute', left: 80, top: 64}}>
        <Logo theme={theme} dir={dir} />
      </div>
      <div style={{position: 'absolute', left: 80, right: 80, top: 150, bottom: 90, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 56}}>
      <div>
        <Words text={outro.headline} highlight={outro.highlight} accent={c.accent} start={4} size={92} />
        {outro.subhead ? (
          <div style={{marginTop: 26, fontSize: 32, color: c.textMuted, opacity: ramp(f, 30, 46), maxWidth: 1300, lineHeight: 1.35}}>{outro.subhead}</div>
        ) : null}
        {pills.length ? (
          <div style={{marginTop: 34, display: 'flex', gap: 18, flexWrap: 'wrap'}}>
            {pills.map((p, i) => {
              const kk = ramp(f, 40 + i * 6, 56 + i * 6);
              return (
                <div
                  key={i}
                  style={{
                    fontFamily: MONO_STACK,
                    fontSize: 28,
                    padding: '12px 26px',
                    borderRadius: 40,
                    background: hexToRgba(c.accent, 0.14),
                    border: `1.5px solid ${hexToRgba(c.accent, 0.7)}`,
                    opacity: kk,
                    transform: `translateY(${(1 - kk) * 16}px)`,
                  }}
                >
                  {p}
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
      {cards.length ? (
        <div style={{display: 'flex', gap: 28}}>
          {cards.map((cd, i) => {
            const kk = ramp(f, 58 + i * 8, 76 + i * 8);
            return (
              <div
                key={i}
                style={{
                  flex: 1,
                  padding: '28px 32px',
                  borderRadius: 18,
                  background: theme.mode === 'dark' ? '#ffffff' : c.card,
                  color: theme.mode === 'dark' ? '#111827' : c.text,
                  boxShadow: `0 20px 50px ${hexToRgba('#000', 0.3)}`,
                  opacity: kk,
                  transform: `translateY(${(1 - kk) * 30}px)`,
                }}
              >
                <div style={{fontSize: 30, fontWeight: 700, marginBottom: 10, color: theme.mode === 'dark' ? '#111827' : c.text}}>{cd.title}</div>
                <div style={{fontSize: 24, lineHeight: 1.4, opacity: 0.8}}>{cd.body}</div>
              </div>
            );
          })}
        </div>
      ) : null}
      {outro.closing ? <div style={{fontSize: 34, fontWeight: 600, opacity: ramp(f, 84, 100)}}>{outro.closing}</div> : null}
      </div>
    </AbsoluteFill>
  );
};
