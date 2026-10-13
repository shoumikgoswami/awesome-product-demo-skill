// Copies the latin woff2 files of the bundled @fontsource families into public/fonts so renders never need the network.
// Usage: node scripts/setup-fonts.mjs
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const families = ['inter', 'poppins', 'manrope', 'dm-sans', 'plus-jakarta-sans', 'space-grotesk'];
const weights = [400, 500, 600, 700];
const out = path.join(root, 'public', 'fonts');
fs.mkdirSync(out, {recursive: true});
let n = 0;
for (const f of families) {
  for (const w of weights) {
    const src = path.join(root, 'node_modules', '@fontsource', f, 'files', `${f}-latin-${w}-normal.woff2`);
    if (!fs.existsSync(src)) {
      console.warn('missing', src);
      continue;
    }
    fs.copyFileSync(src, path.join(out, `${f}-${w}.woff2`));
    n++;
  }
}
console.log(`copied ${n} font files to public/fonts`);
