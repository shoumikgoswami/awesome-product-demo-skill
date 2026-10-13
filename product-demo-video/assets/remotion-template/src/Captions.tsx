import React from 'react';
import {useCurrentFrame} from 'remotion';
import type {Timeline} from './types';
import {hexToRgba, lin} from './utils';

export const Captions: React.FC<{timeline: Timeline; card: {x: number; y: number; w: number; h: number}}> = ({timeline, card}) => {
  const f = useCurrentFrame();
  const c = timeline.theme.colors;
  const cap = timeline.captions.find((x) => f >= x.start - 2 && f <= x.end);
  if (!cap) return null;
  const op = Math.min(lin(f, cap.start - 2, cap.start + 2), 1 - lin(f, cap.end - 3, cap.end));
  return (
    <div
      style={{
        position: 'absolute',
        left: (1920 - 1600) / 2,
        width: 1600,
        top: Math.min(card.y + card.h + 34, 1080 - 110),
        textAlign: 'center',
        fontSize: 42,
        fontWeight: 500,
        lineHeight: 1.25,
        opacity: op,
        textShadow: timeline.theme.mode === 'dark' ? `0 2px 12px ${hexToRgba('#000', 0.5)}` : 'none',
      }}
    >
      {cap.words.map((w, i) => {
        const active = f >= w.start && f < w.end;
        return (
          <span key={i} style={{color: active ? c.accent : c.text}}>
            {w.text}
            {i < cap.words.length - 1 ? ' ' : ''}
          </span>
        );
      })}
    </div>
  );
};
