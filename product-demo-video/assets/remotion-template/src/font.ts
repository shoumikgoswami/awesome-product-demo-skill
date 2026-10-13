import {continueRender, delayRender, staticFile} from 'remotion';

const loaded = new Set<string>();

// Loads the bundled woff2 files (public/fonts/<family>-<weight>.woff2, created by `npm run setup-fonts`).
// Falls back silently to the system sans-serif when a file is missing, so a render never blocks on the network.
export const loadFont = (family: string) => {
  if (loaded.has(family)) return;
  loaded.add(family);
  const handle = delayRender(`font ${family}`);
  Promise.all(
    [400, 500, 600, 700].map((w) =>
      new FontFace('DemoFont', `url(${staticFile(`fonts/${family}-${w}.woff2`)})`, {weight: String(w)})
        .load()
        .then((f) => {
          (document.fonts as unknown as {add: (f: FontFace) => void}).add(f);
        })
        .catch(() => undefined),
    ),
  ).finally(() => continueRender(handle));
};

export const FONT_STACK = `'DemoFont', 'Inter', 'Segoe UI', system-ui, -apple-system, Roboto, Arial, sans-serif`;
export const MONO_STACK = `ui-monospace, 'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', monospace`;
