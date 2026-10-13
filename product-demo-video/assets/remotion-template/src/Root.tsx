import React from 'react';
import {Composition, staticFile} from 'remotion';
import {ProductDemo} from './ProductDemo';
import type {Timeline} from './types';

export type DemoProps = {dir: string; timeline: Timeline | null};

export const Root: React.FC = () => (
  <Composition
    id="ProductDemo"
    component={ProductDemo}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={300}
    defaultProps={{dir: 'project', timeline: null} as DemoProps}
    calculateMetadata={async ({props}) => {
      const res = await fetch(staticFile(`${props.dir}/timeline.json`));
      if (!res.ok) throw new Error(`Cannot load public/${props.dir}/timeline.json - run scripts/build_timeline.py first`);
      const timeline = (await res.json()) as Timeline;
      return {
        durationInFrames: timeline.totalFrames,
        fps: timeline.fps,
        width: timeline.width,
        height: timeline.height,
        props: {...props, timeline},
      };
    }}
  />
);
