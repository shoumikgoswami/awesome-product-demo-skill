// All frame numbers are in the composition fps. Stage-relative = 0 at the first frame after the intro.
export type Rect = {x: number; y: number; w: number; h: number}; // fractions (0-1) of the screenshot

export type Theme = {
  product: string;
  mode: 'dark' | 'light';
  font: string; // inter | poppins | manrope | dm-sans | plus-jakarta-sans | space-grotesk
  logo?: string | null;
  logoPlate?: string | null; // background pill colour behind the logo when it would not read on the video background
  colors: {
    bgDeep: string;
    bg: string;
    bgLight: string;
    accent: string;
    accent2: string;
    text: string;
    textMuted: string;
    onAccent: string;
    card: string;
  };
};

export type Word = {text: string; start: number; end: number};
export type Caption = {start: number; end: number; words: Word[]};

export type Focus = Rect & {
  frame: number; // scene-relative frame when the zoom move begins
  zoom: number;
  hold: number; // frames to hold before easing back
  click?: boolean;
  cursor?: boolean;
  highlight?: boolean;
};

export type Chip = {text: string; start: number; end: number}; // scene-relative
export type TypeOp = Rect & {frame: number; text: string; fill: string; color: string; size: number};
export type Callout = Rect & {frame: number; hold: number; scale: number};

export type Scene = {
  id: string;
  kind: 'image' | 'clip';
  image?: string;
  imageSize?: {w: number; h: number};
  clip?: {src: string; fromFrame: number; toFrame: number};
  start: number; // stage-relative
  duration: number;
  chapter: string;
  transition: 'crossfade' | 'push' | 'none'; // how this scene comes in
  transitionFrames: number;
  focus: Focus[];
  chips: Chip[];
  blur: Rect[];
  type: TypeOp[];
  callouts: Callout[];
  cursorStart?: {x: number; y: number} | null;
};

export type Chapter = {id: string; step: number | null; title: string; start: number};

export type IntroData = {
  eyebrow?: string;
  headline: string;
  highlight?: string;
  subhead?: string;
  hero?: string | null;
  points?: string[];
};

export type OutroData = {
  headline: string;
  highlight?: string;
  subhead?: string;
  pills?: string[];
  cards?: {title: string; body: string}[];
  closing?: string;
};

export type Timeline = {
  fps: number;
  width: number;
  height: number;
  totalFrames: number;
  introFrames: number;
  stageFrames: number;
  outroFrames: number;
  theme: Theme;
  stageLabel: string; // eyebrow text for chapters without a step number, e.g. "Product tour"
  intro: IntroData | null;
  outro: OutroData | null;
  scenes: Scene[];
  chapters: Chapter[];
  captions: Caption[];
  audio: {narration: string | null; music: string | null; musicVolume: number};
};
