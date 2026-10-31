#!/usr/bin/env python3
"""Export the project icon into the standard macOS iconset sizes."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
iconset=ROOT/'.package-cache/AppIcon.iconset'
iconset.mkdir(parents=True,exist_ok=True)
source=ROOT/'native/assets/AppIcon.png'
for size in (16,32,128,256,512):
    for scale in (1,2):
        name=f'icon_{size}x{size}'+('@2x' if scale==2 else '')+'.png'
        subprocess.run(['sips','-z',str(size*scale),str(size*scale),str(source),'--out',str(iconset/name)],check=True,stdout=subprocess.DEVNULL)
subprocess.run(['iconutil','-c','icns',str(iconset),'-o',str(ROOT/'native/assets/AppIcon.icns')],check=True)
