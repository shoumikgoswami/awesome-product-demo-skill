import React from 'react';
import {useCurrentFrame} from 'remotion';
import type {Timeline} from './types';
import {Logo} from './Logo';
import {hexToRgba, ramp} from './utils';

export const Header: React.FC<{timeline: Timeline; dir: string}> = ({timeline, dir}) => {
  const f = useCurrentFrame();
  const {theme, chapters, scenes, stageLabel} = timeline;
  const c = theme.colors;

  // Current chapter = chapter of the scene whose narration is on screen.
  const scene = [...scenes].reverse().find((s) => f >= s.start) ?? scenes[0];
  const chapter = chapters.find((ch) => ch.id === scene.chapter) ?? chapters[0];
  const steps = chapters.filter((ch) => ch.step !== null);
  const chapterIdx = chapters.indexOf(chapter);
  const swap = ramp(f, chapter.start, chapter.start + 10);
  const total = steps.length;

  const eyebrow = chapter.step !== null ? `Step ${chapter.step} of ${total}` : `${theme.product} · ${stageLabel}`;

  return (
    <>
      <div style={{position: 'absolute', left: 40, top: 40, height: 76, display: 'flex', alignItems: 'center', gap: 28}}>
        <Logo theme={theme} dir={dir} height={54} />
        <div style={{width: 2, height: 52, background: hexToRgba(c.text, 0.18)}} />
        <div style={{opacity: swap, transform: `translateY(${(1 - swap) * 8}px)`}}>
          <div style={{fontSize: 20, fontWeight: 600, color: c.accent, letterSpacing: 1.2, textTransform: 'uppercase'}}>{eyebrow}</div>
          <div style={{fontSize: 38, fontWeight: 600, lineHeight: 1.15}}>{chapter.title}</div>
        </div>
      </div>
      {total > 0 ? (
        <div style={{position: 'absolute', right: 40, top: 56, display: 'flex', gap: 10}}>
          {steps.map((ch) => {
            const state = chapters.indexOf(ch) < chapterIdx ? 'done' : ch.id === chapter.id ? 'active' : 'todo';
            return (
              <div
                key={ch.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  height: 44,
                  padding: state === 'active' ? '0 20px 0 12px' : '0 14px',
                  borderRadius: 22,
                  fontSize: 20,
                  fontWeight: 600,
                  background: state === 'active' ? c.accent : state === 'done' ? hexToRgba(c.text, 0.12) : 'transparent',
                  color: state === 'active' ? c.onAccent : c.text,
                  border: state === 'todo' ? `2px solid ${hexToRgba(c.text, 0.28)}` : '2px solid transparent',
                }}
              >
                <span
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: 13,
                    display: 'grid',
                    placeItems: 'center',
                    fontSize: 16,
                    background: state === 'active' ? hexToRgba(c.onAccent, 0.2) : 'transparent',
                    color: state === 'done' ? c.accent : 'inherit',
                  }}
                >
                  {state === 'done' ? '✓' : ch.step}
                </span>
                {state === 'active' ? <span>{ch.title}</span> : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </>
  );
};
