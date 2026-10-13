import React from 'react';
import type {Theme} from './types';
import {asset} from './utils';

// Logo (or product-name wordmark). When the logo's own colours would vanish on the video background, build_timeline.py sets
// theme.logoPlate and the logo sits on a rounded plate of that colour.
export const Logo: React.FC<{theme: Theme; dir: string; height?: number}> = ({theme, dir, height = 62}) => {
  const plate = theme.logoPlate;
  const inner = theme.logo ? (
    <img src={asset(dir, theme.logo)} style={{height, maxWidth: 260, objectFit: 'contain', display: 'block'}} />
  ) : (
    <div style={{fontSize: 34, fontWeight: 700, letterSpacing: -0.5}}>{theme.product}</div>
  );
  if (!plate || !theme.logo) return inner;
  return <div style={{background: plate, padding: '8px 18px', borderRadius: 14, boxShadow: '0 6px 20px rgba(0,0,0,0.25)'}}>{inner}</div>;
};
