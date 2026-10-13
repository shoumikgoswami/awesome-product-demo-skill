import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import type {Timeline} from './types';
import {Captions} from './Captions';
import {Header} from './Header';
import {SceneView} from './SceneView';
import {cardLayout, hexToRgba, lin} from './utils';

export const Stage: React.FC<{timeline: Timeline; dir: string}> = ({timeline, dir}) => {
  const f = useCurrentFrame();
  const {stageFrames, scenes, theme} = timeline;
  const c = theme.colors;
  const sizes = scenes.map((s) => s.imageSize ?? {w: 1920, h: 1080});
  const card = cardLayout(sizes);

  // The window fades/scales in over 16 frames and out over the last 14.
  const enter = lin(f, 0, 16);
  const exit = 1 - lin(f, stageFrames - 14, stageFrames);
  const k = Math.min(enter, exit);
  const scale = 0.97 + 0.03 * k;

  return (
    <AbsoluteFill>
      <div style={{opacity: k}}>
        <Header timeline={timeline} dir={dir} />
      </div>
      <div
        style={{
          position: 'absolute',
          left: card.x,
          top: card.y,
          width: card.w,
          height: card.h,
          borderRadius: 18,
          overflow: 'hidden',
          background: c.card,
          boxShadow: `0 30px 80px ${hexToRgba('#000000', theme.mode === 'dark' ? 0.55 : 0.22)}, 0 0 0 1px ${hexToRgba(c.text, 0.08)}`,
          opacity: k,
          transform: `scale(${scale})`,
          transformOrigin: 'center top',
        }}
      >
        {scenes.map((s, i) => {
          const t = i === 0 ? 0 : s.transition === 'none' ? 0 : s.transitionFrames;
          const from = s.start - t;
          const end = s.start + s.duration;
          return (
            <Sequence key={s.id} from={from} durationInFrames={end - from} layout="none">
              <SceneView
                scene={s}
                index={i}
                lead={t}
                card={card}
                dir={dir}
                theme={theme}
                fps={timeline.fps}
                next={scenes[i + 1] ? {transition: scenes[i + 1].transition, frames: scenes[i + 1].transitionFrames} : null}
              />
            </Sequence>
          );
        })}
      </div>
      <div style={{opacity: k}}>
        <Captions timeline={timeline} card={card} />
      </div>
      <div
        style={{
          position: 'absolute',
          left: 0,
          bottom: 0,
          height: 5,
          width: `${(f / Math.max(1, stageFrames)) * 100}%`,
          background: c.accent,
        }}
      />
    </AbsoluteFill>
  );
};
