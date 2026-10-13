import React from 'react';
import {AbsoluteFill, Audio, Sequence, interpolate} from 'remotion';
import type {DemoProps} from './Root';
import {FONT_STACK, loadFont} from './font';
import {Intro} from './Intro';
import {Outro} from './Outro';
import {Stage} from './Stage';
import {asset, hexToRgba} from './utils';

export const Background: React.FC<{timeline: NonNullable<DemoProps['timeline']>}> = ({timeline}) => {
  const c = timeline.theme.colors;
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${c.bgDeep} 0%, ${c.bg} 100%)`,
      }}
    >
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 88% 8%, ${hexToRgba(c.accent, timeline.theme.mode === 'dark' ? 0.2 : 0.14)} 0%, transparent 45%)`,
        }}
      />
    </AbsoluteFill>
  );
};

export const ProductDemo: React.FC<DemoProps> = ({dir, timeline}) => {
  if (!timeline) return null;
  loadFont(timeline.theme.font);

  const {introFrames, stageFrames, outroFrames, audio, fps, totalFrames} = timeline;
  const stageStart = introFrames;
  const outroStart = introFrames + stageFrames;

  // Music: fades in/out over 1s, ducked to the configured volume under narration.
  const musicVol = (f: number) =>
    audio.musicVolume *
    interpolate(f, [0, fps, totalFrames - fps * 1.5, totalFrames], [0, 1, 1, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });

  return (
    <AbsoluteFill style={{fontFamily: FONT_STACK, color: timeline.theme.colors.text}}>
      <Background timeline={timeline} />
      {timeline.intro && introFrames > 0 ? (
        <Sequence from={0} durationInFrames={introFrames}>
          <Intro timeline={timeline} dir={dir} />
        </Sequence>
      ) : null}
      <Sequence from={stageStart} durationInFrames={stageFrames}>
        <Stage timeline={timeline} dir={dir} />
      </Sequence>
      {timeline.outro && outroFrames > 0 ? (
        <Sequence from={outroStart} durationInFrames={outroFrames}>
          <Outro timeline={timeline} dir={dir} />
        </Sequence>
      ) : null}
      {audio.narration ? (
        <Sequence from={stageStart} durationInFrames={stageFrames}>
          <Audio src={asset(dir, audio.narration)} />
        </Sequence>
      ) : null}
      {audio.music ? <Audio src={asset(dir, audio.music)} loop volume={musicVol} /> : null}
    </AbsoluteFill>
  );
};
