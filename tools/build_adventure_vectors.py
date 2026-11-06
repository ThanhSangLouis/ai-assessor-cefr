"""Build the small, editable 2D props for the adaptive learning roadmap."""
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'src/aicefr/api/static/art/adventure'
SAGE, LEAF, WOOD, CREAM, ORANGE, TEAL = '#96b988', '#6f9d78', '#bb9367', '#fff7e5', '#f3b35b', '#acd4d9'

def tree(x=90, y=40, color=SAGE, shape='round'):
    trunk = f'<path d="M{x} {y+35}v65m0-30-20-22m20 34 17-24" stroke="{WOOD}" stroke-width="7" fill="none" stroke-linecap="round"/>'
    if shape == 'pine': crown = f'<path d="m{x} {y-30}-35 55h16l-27 34h92l-27-34h16Z" fill="{color}"/>'
    elif shape == 'tall': crown = f'<ellipse cx="{x}" cy="{y+12}" rx="30" ry="53" fill="{color}"/>'
    else: crown = f'<path d="M{x-35} {y+20}c-18-24 1-49 25-42 17-28 52-13 49 12 29 17 15 51-11 46-20 18-49 10-63-16Z" fill="{color}"/>'
    return trunk + crown

def flowers(x=70,y=100,color='#fff'):
    return f'<path d="M{x} {y}v25m22-14v20" stroke="{LEAF}" stroke-width="2"/><g fill="{color}"><circle cx="{x}" cy="{y-4}" r="6"/><circle cx="{x-6}" cy="{y+2}" r="6"/><circle cx="{x+6}" cy="{y+2}" r="6"/><circle cx="{x}" cy="{y+7}" r="6"/></g><circle cx="{x}" cy="{y+2}" r="3" fill="{ORANGE}"/><circle cx="{x+22}" cy="{y+10}" r="6" fill="{ORANGE}"/>'

def leaves(x=90,y=100):
    return f'<path d="M{x} {y+30}v-60" stroke="{LEAF}" stroke-width="3"/>' + ''.join(f'<ellipse cx="{x+s*10}" cy="{y-15+j*13}" rx="14" ry="6" transform="rotate({s*35} {x+s*10} {y-15+j*13})" fill="{SAGE}"/>' for j in range(3) for s in [-1,1])

def rock(x=65,y=115):
    return f'<path d="m{x} {y} 16-26 37-4 22 30Z" fill="#c4d0c6"/><path d="m{x+16} {y-26} 37-4-15 30Z" fill="#dce3d9"/>'

assets={
 'tree-round':tree(), 'tree-tall':tree(shape='tall'), 'tree-pine':tree(shape='pine'),
 'tree-pair':tree(65,62,SAGE)+tree(132,81,LEAF,'tall'),
 'tree-orchard':tree()+''.join(f'<circle cx="{x}" cy="{y}" r="5" fill="{ORANGE}"/>' for x,y in [(68,40),(102,23),(116,55)]),
 'tree-willow':f'<path d="M90 65v72" stroke="{WOOD}" stroke-width="8"/>'+''.join(f'<path d="M90 30Q{x} 26 {x} 100" stroke="{SAGE}" stroke-width="15" fill="none" stroke-linecap="round"/>' for x in [38,58,78,103,124,144]),
 'bush-round':f'<path d="M22 125c-16-28 10-53 32-39 9-37 51-36 60-8 30-23 62 4 48 32 16 9 12 20 2 24H24Z" fill="{SAGE}"/>',
 'bush-flowering':f'<ellipse cx="95" cy="105" rx="65" ry="27" fill="{SAGE}"/>'+flowers(65,98)+flowers(118,91),
 'fern':leaves(70,95)+leaves(110,105), 'reeds':''.join(f'<path d="M{x} 135v-{h}" stroke="{LEAF}" stroke-width="3"/><path d="M{x} {135-h}v-14" stroke="{WOOD}" stroke-width="7" stroke-linecap="round"/>' for x,h in [(60,52),(83,75),(108,59),(130,44)]),
 'grass-tuft':''.join(f'<path d="M90 135q{x-90} -20 {x-90} -{h}" stroke="{SAGE}" stroke-width="7" fill="none" stroke-linecap="round"/>' for x,h in [(60,38),(78,52),(98,55),(119,39)]),
 'lily-pads':f'<ellipse cx="64" cy="99" rx="38" ry="15" fill="{SAGE}"/><ellipse cx="127" cy="120" rx="31" ry="12" fill="{LEAF}"/><path d="m80 99-17-9v14Z" fill="#fff"/><path d="m138 119-13-6v12Z" fill="#fff"/>',
 'flowers-white':flowers(), 'flowers-orange':flowers(90,100,ORANGE), 'flowers-blue':flowers(90,100,'#a9c8e0'),
 'flowers-bells':''.join(f'<path d="M{x} 135V{y}" stroke="{LEAF}" stroke-width="2"/><path d="M{x-8} {y+9}q-4-32 9-31 14 3 8 31Z" fill="{CREAM}" stroke="#d7d6ba"/>' for x,y in [(55,90),(90,62),(124,96)]),
 'mushrooms':''.join(f'<path d="M{x} {y}v23" stroke="#e7c9a0" stroke-width="10"/><path d="M{x-23} {y}q23-42 46 0Z" fill="{ORANGE}"/><circle cx="{x-6}" cy="{y-10}" r="3" fill="{CREAM}"/><circle cx="{x+7}" cy="{y-5}" r="3" fill="{CREAM}"/>' for x,y in [(65,98),(123,113)]),
 'rocks-small':rock(30,130)+rock(98,112), 'rocks-tall':f'<path d="m63 135-8-61 25-35 37 17 15 79Z" fill="#c3d0c8"/><path d="m80 39 11 96H63l-8-61Z" fill="#dde5dc"/>',
 'stump':f'<path d="M58 73v58q34 18 68 0V73" fill="{WOOD}"/><ellipse cx="92" cy="73" rx="34" ry="12" fill="#e1c29a"/><ellipse cx="92" cy="73" rx="21" ry="6" fill="none" stroke="{WOOD}"/>',
 'log':f'<rect x="38" y="88" width="111" height="39" rx="8" fill="{WOOD}"/><ellipse cx="144" cy="108" rx="15" ry="21" fill="#e1c29a"/><ellipse cx="144" cy="108" rx="8" ry="12" fill="none" stroke="{WOOD}"/>',
 'butterflies':''.join(f'<ellipse cx="{x-8}" cy="{y}" rx="10" ry="15" transform="rotate(-30 {x-8} {y})" fill="{ORANGE}"/><ellipse cx="{x+8}" cy="{y}" rx="10" ry="15" transform="rotate(30 {x+8} {y})" fill="#f9d38b"/><path d="M{x} {y-4}v17" stroke="{WOOD}" stroke-width="2"/>' for x,y in [(65,67),(124,101)]),
 'music-notes':f'<path d="M68 110V60l56-10v47M68 75l56-10" fill="none" stroke="{LEAF}" stroke-width="7"/><ellipse cx="58" cy="110" rx="14" ry="9" fill="{LEAF}"/><ellipse cx="114" cy="97" rx="14" ry="9" fill="{LEAF}"/>',
 'book-stack':''.join(f'<rect x="{x}" y="{y}" width="83" height="17" rx="4" fill="{c}"/><path d="M{x+8} {y+8}h65" stroke="{CREAM}" stroke-width="7"/>' for x,y,c in [(45,116,LEAF),(38,97,ORANGE),(51,78,TEAL)]),
 'fence':f'<path d="M28 96h136M28 116h136" stroke="#d3b284" stroke-width="7"/>'+''.join(f'<path d="M{x} 135V74" stroke="{WOOD}" stroke-width="8" stroke-linecap="round"/>' for x in [40,82,124,158]),
 'stepping-stones':''.join(f'<ellipse cx="{x}" cy="{y}" rx="24" ry="10" fill="#c8d4cc"/>' for x,y in [(45,128),(90,107),(134,86)]),
 'signpost':f'<path d="M89 42v95" stroke="{WOOD}" stroke-width="8"/><path d="M40 47h92l20 15-20 15H40Z" fill="#e7bd80"/>',
 'lantern':f'<path d="M93 136V39q0-26 25-26" stroke="{WOOD}" stroke-width="5" fill="none"/><path d="M108 26h25l6 33h-37Z" fill="#f6cf7e"/><path d="M103 26h35m-37 34h40" stroke="{WOOD}" stroke-width="4"/>',
 'well':f'<path d="M50 96h85v39H50Z" fill="#c3d0c3"/><path d="M56 98V49m73 49V49" stroke="{WOOD}" stroke-width="6"/><path d="m40 50 54-33 54 33Z" fill="{ORANGE}"/><path d="M91 52v48" stroke="{WOOD}" stroke-width="2"/>',
 'birdhouse':f'<path d="M95 95v42" stroke="{WOOD}" stroke-width="7"/><path d="M62 60h65v44H62Z" fill="#dfbb87"/><path d="m52 60 42-35 43 35Z" fill="{LEAF}"/><circle cx="95" cy="78" r="10" fill="{WOOD}"/>',
 'waterfall':f'<path d="M30 50h130v91H30Z" fill="#c8d8ca"/><path d="M70 50h53v90H70Z" fill="{TEAL}"/><path d="M82 58v68m20-58v60" stroke="#ecf7f5" stroke-width="3"/><ellipse cx="98" cy="138" rx="70" ry="12" fill="#d6edef"/>',
 'arch-vines':f'<path d="M42 137V60q50-60 100 0v77" stroke="{WOOD}" stroke-width="7" fill="none"/>'+''.join(f'<ellipse cx="{x}" cy="{y}" rx="12" ry="6" transform="rotate({r} {x} {y})" fill="{SAGE}"/>' for x,y,r in [(43,86,35),(53,50,-35),(80,31,15),(114,36,-30),(142,75,-35)]),
 'flag-rest':f'<path d="M69 40v95" stroke="{WOOD}" stroke-width="5"/><path d="M72 40h67l-13 21 13 20H72Z" fill="{SAGE}"/><path d="m88 59 8 8 19-18" stroke="white" stroke-width="4" fill="none"/>',
 'milestone':f'<path d="M56 138V84q40-54 80 0v54Z" fill="#d3ded1"/><path d="M75 106h42" stroke="#9aaf99" stroke-width="4"/>',
 'chest':f'<path d="M48 95q0-42 48-42t48 42v41H48Z" fill="{WOOD}"/><path d="M48 96h96m-70-36v76m45-76v76" stroke="#e6bf78" stroke-width="6"/><rect x="86" y="96" width="18" height="21" rx="3" fill="{ORANGE}"/>',
 'compass':f'<circle cx="95" cy="88" r="45" fill="{CREAM}" stroke="#dbbc7f" stroke-width="4"/><path d="m113 58-9 42-27 19 9-42Z" fill="{ORANGE}"/><path d="m113 58-27 19 18 23Z" fill="{LEAF}"/>',
 'trophy':f'<path d="M66 52h58v23q-29 51-58 0Z" fill="#f2bf55"/><path d="M66 58H48q0 29 27 28m49-28h18q0 29-27 28" stroke="#ddb04d" stroke-width="5" fill="none"/><path d="M95 100v22m-23 9h46" stroke="#ddb04d" stroke-width="10"/>',
 'finish-flag':f'<path d="M65 40v97" stroke="{WOOD}" stroke-width="5"/><path d="M69 40h70v48H69Z" fill="{CREAM}"/>'+''.join(f'<rect x="{69+x*17.5}" y="{40+y*16}" width="17.5" height="16" fill="{SAGE}"/>' for x in range(4) for y in range(3) if (x+y)%2==0),
 'cloud-wide':f'<path d="M26 91c-14-24 12-40 30-29 6-32 44-33 57-9 28-15 55 8 40 31 23 19 10 32-14 32H42c-31 0-35-17-16-25Z" fill="#e0edf0"/>',
 'cloud-small':f'<path d="M44 104c-22-21-3-44 17-37 16-34 55-21 55 4 35-8 51 39 10 43H57Z" fill="#e9f1f1"/>',
 'hills-meadow':f'<path d="M4 142Q50 56 110 96q45-36 79 46Z" fill="#e1edd5"/><path d="M15 142q54-56 104 0Z" fill="#cfdfbc"/>',
 'hills-forest':f'<path d="M0 143q39-111 96-49 59-94 104 49Z" fill="#d2e3d1"/><path d="M15 143q83-54 172 0Z" fill="#e4eddd"/>',
 'mountains':f'<path d="m0 141 63-105 56 80 29-54 52 79Z" fill="#d4e0ef"/><path d="m43 70 20-34 22 32-18-7-9 13-7-9Z" fill="#f6f9fc"/>',
 'lake-ripples':f'<ellipse cx="96" cy="103" rx="83" ry="34" fill="#d9edf0"/><path d="M35 97h45m24 14h50m-84 10h35" stroke="#f3fafb" stroke-width="3" stroke-linecap="round"/>',
}
assert len(assets)==44, len(assets)
OUT.mkdir(parents=True,exist_ok=True)
for name,body in assets.items():
    (OUT/f'{name}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 160" fill="none">{body}</svg>\n')
print(f'Built {len(assets)} editable SVG assets')
