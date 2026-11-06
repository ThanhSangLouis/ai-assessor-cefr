"""Build layered, seamless 2D terrain and foreground assets for the roadmap."""
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parents[1] / 'src/aicefr/api/static/art/adventure'
PALETTES = {
    'garden': ('#f0f5de', '#d2e6a5', '#a9cb7d', '#608e56'),
    'valley': ('#eaf1df', '#c3dbac', '#8eb484', '#517f63'),
    'forest': ('#e1eddb', '#a9cb99', '#729d77', '#3b6e59'),
    'music': ('#faf0d5', '#ebd69d', '#c6bc7a', '#7f955f'),
    'lake': ('#e6f1e3', '#bbd9b2', '#88b9a1', '#4b8d7b'),
    'summit': ('#edf2ee', '#cedde0', '#9fb9bf', '#587e86'),
}

def tree(x, y, scale, color, pine=False):
    crown = ('<path d="M0-115-35-53h16L-45-5h90L19-53h16Z" fill="%s"/>' % color if pine else
             f'<g fill="{color}"><circle cy="-74" r="32"/><circle cx="-22" cy="-45" r="29"/><circle cx="24" cy="-43" r="31"/></g><ellipse cx="-9" cy="-81" rx="17" ry="13" fill="#fff" opacity=".12"/>')
    return f'<g transform="translate({x} {y}) scale({scale})"><ellipse cy="9" rx="45" ry="13" fill="#34564c" opacity=".13"/><path d="M0 4V-51m0 25-17-16" stroke="#947b5c" stroke-width="8" stroke-linecap="round"/>{crown}</g>'

def rock(x,y,s):
    return f'<g transform="translate({x} {y}) scale({s})"><ellipse cy="5" rx="31" ry="10" fill="#3c5954" opacity=".12"/><path d="m-30 0 10-29 27-9 25 24-6 19Z" fill="#a4b4ad"/><path d="m-20-29 27-9-6 28-31 10Z" fill="#cbd2be"/><path d="m1-10 25 15 6-19L7-38Z" fill="#8d9f9c"/></g>'

def escarpment(x, y, scale, grass, stone):
    """An exposed side below a raised grassy shelf, lit from the upper left."""
    return f'''<g transform="translate({x} {y}) scale({scale})">
    <ellipse cy="63" rx="116" ry="29" fill="#294e46" opacity=".12"/>
    <path d="M-120-8Q-18-55 112-8L92 42 45 64-30 58-102 36Z" fill="{stone}"/>
    <path d="m-30 6 7 48 25 5 9-54m45-3-7 58 35-15 12-51" fill="#38584b" opacity=".15"/>
    <path d="m-96 18 26 9m-12 9 17 6m80-15 23-4m20-2 16-9" stroke="#fff" opacity=".22" stroke-width="3" stroke-linecap="round"/>
    <path d="M-120-15Q-18-62 112-15L99 6Q0 40-114 8Z" fill="{grass}"/>
    <path d="M-119-15Q-20-61 111-15" stroke="#f9f4cf" stroke-width="5" fill="none" opacity=".6"/>
    <path d="M-65 10v19m12-16v10m110-15v13" stroke="{grass}" stroke-width="8" stroke-linecap="round"/>
    </g>'''

def svg(body):
    return '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">'+body+'</svg>'

for index,(name,(base,mid,deep,leaf)) in enumerate(PALETTES.items()):
    rng=Random(91+index)
    body=f'''<defs><linearGradient id="ground" x2=".8" y2="1"><stop stop-color="{base}"/><stop offset="1" stop-color="{mid}" stop-opacity=".4"/></linearGradient><linearGradient id="water" x2="1" y2="1"><stop stop-color="#98d9dc"/><stop offset="1" stop-color="#54aebd"/></linearGradient></defs>
    <rect width="800" height="800" fill="{base}"/><rect width="800" height="800" fill="url(#ground)"/>
    <path d="M0 0H210Q100 110 190 240T140 470T180 800H0Z" fill="{mid}"/>
    <path d="M800 0H680Q590 120 695 260T660 540T690 800H800Z" fill="{mid}"/>
    <path d="M0 120Q190 50 180 190T90 370L0 400Z" fill="{deep}" opacity=".3"/>
    <path d="M800 470Q620 410 655 580T800 720Z" fill="{deep}" opacity=".35"/>'''
    # Atmospheric silhouettes recede behind the darker, sharper vegetation.
    distance=''
    for x,y,s in [(70,240,.42),(180,160,.32),(690,390,.38),(750,600,.5),(100,720,.3)]:
        distance+=tree(x,y,s,deep,name=='summit')
    body+=f'<g opacity=".34">{distance}</g>'
    body+=f'<path d="M0 320Q90 180 205 300L225 345Q80 285 0 380ZM800 690Q720 555 615 660L600 710Q720 660 800 740Z" fill="{deep}" opacity=".18"/>'
    # Raised banks expose a shaded side and a sunlit rim, away from the lesson corridor.
    for transform in ('', 'translate(800 430) scale(-1 .75)'):
        body+=f'<g transform="{transform}"><path d="M0 65Q185 30 195 112T105 230L0 251" fill="none" stroke="{deep}" stroke-width="24" opacity=".4"/><path d="M0 45Q185 10 195 92T105 210L0 231" fill="{mid}" stroke="{base}" stroke-width="5"/></g>'
    if name=='valley':
        body+='<path d="M735-30C570 85 790 200 665 310S695 490 760 565 620 700 700 830" fill="none" stroke="#809d76" stroke-width="105"/><path d="M735-30C570 85 790 200 665 310S695 490 760 565 620 700 700 830" fill="none" stroke="#ecedc8" stroke-width="91"/><path d="M735-30C570 85 790 200 665 310S695 490 760 565 620 700 700 830" fill="none" stroke="url(#water)" stroke-width="68"/>'
    if name=='lake':
        body+='<path d="M800 70Q590 25 606 170T650 390Q570 480 630 610T800 730Z" fill="#83bda9"/><path d="M800 62Q599 28 618 170T662 390Q580 478 642 610T800 716Z" fill="#f4edcd"/><path d="M800 75Q614 40 630 175T674 395Q599 477 656 605T800 704Z" fill="url(#water)"/>'
        for x,y in [(704,165),(734,280),(705,470),(735,610)]:
            body+=f'<path d="M{x-25} {y}q25 7 50 0m-40 12h24" stroke="#d9f2e5" stroke-width="3" fill="none" opacity=".8"/><ellipse cx="{x-5}" cy="{y+37}" rx="15" ry="6" fill="#6da56d"/><circle cx="{x-3}" cy="{y+33}" r="4" fill="#fff0dc"/>'
    if name=='summit':
        for x,y,s in [(65,190,1.2),(750,590,1.4),(115,690,.8)]:
            body+=f'<g transform="translate({x} {y}) scale({s})"><ellipse cy="30" rx="100" ry="21" fill="#7f9a9d" opacity=".2"/><path d="M-100 20 0-150 100 20Z" fill="#a2bcc6"/><path d="M0-150 100 20 14-10Z" fill="#7c9fae"/><path d="m-38-85 38-65 40 68-28-12-14 22-13-21Z" fill="#f9fcf9"/></g>'
    if name == 'garden':
        # Curved planting beds and fence posts make this a cultivated garden.
        for x,y in [(105,430),(710,635)]:
            body+=f'<g transform="translate({x} {y})"><ellipse cy="8" rx="72" ry="31" fill="#94b16e" opacity=".4"/><ellipse rx="70" ry="29" fill="#f3e6c6"/><ellipse cy="-4" rx="62" ry="23" fill="#a3bf76"/>'
            for dx,dy in [(-38,-8),(-12,0),(15,-11),(37,2)]:
                body+=f'<path d="M{dx} {dy}v-15" stroke="#6d9559" stroke-width="3"/><circle cx="{dx}" cy="{dy-18}" r="7" fill="#fff3d3"/><circle cx="{dx}" cy="{dy-18}" r="2.5" fill="#e4ab63"/>'
            body+='</g>'
        body+='<path d="M10 620 155 580m-145 54 145-40" stroke="#c2a776" stroke-width="5"/>'
        for x in range(20,150,25):
            y=620-(x-10)*40/145
            body+=f'<path d="M{x} {y+26}v-47" stroke="#e2ca98" stroke-width="9" stroke-linecap="round"/>'
    if name == 'music':
        # Layered terraces evoke open-air performance lawns.
        for radius in (95,72,49):
            body+=f'<path d="M0 {480-radius}Q{radius*2} 480 0 {480+radius}" fill="none" stroke="#c1b777" stroke-width="13" opacity=".45"/><path d="M0 {475-radius}Q{radius*2} 475 0 {475+radius}" fill="none" stroke="#f7e6b6" stroke-width="9"/>'
        body+='<path d="M655 100Q720 160 800 105" fill="none" stroke="#a18c66" stroke-width="2"/>'
        for x,y,col in [(675,115,'#e6b087'),(710,126,'#b7c58c'),(745,126,'#c3b3ce'),(780,115,'#e6b087')]:
            body+=f'<path d="m{x} {y} 12 4-9 18Z" fill="{col}"/>'
    if name == 'forest':
        for x,y in [(145,440),(700,525),(80,665)]:
            body+=f'<g transform="translate({x} {y})"><ellipse cy="7" rx="25" ry="7" fill="#3b6e59" opacity=".16"/><path d="M-5 4v-23m20 23v-13" stroke="#f1e0b9" stroke-width="7"/><path d="M-24-17Q-7-48 13-17ZM5-8q11-24 23 0Z" fill="#bd8b6f"/><circle cx="-10" cy="-24" r="3" fill="#f4e5c9"/></g>'
    # Exposed landforms establish elevation with a consistent top-left light source.
    stone = '#b1b5a3' if name in ('lake','summit') else '#b5a184'
    body+=escarpment(25,270,.9,mid,stone)
    if name not in ('lake','valley'):
        body+=escarpment(780,580,1.05,mid,stone)
    # Distinct vegetation density: forest is enclosed; lake has a clear shoreline.
    positions=[(30,100,.8),(140,310,.7),(45,550,1.1),(150,765,.8),(740,100,.75),(735,425,.9),(770,760,1.1)]
    if name=='forest':positions += [(90,170,.9),(180,60,.65),(20,380,.9),(680,230,.7),(725,650,1),(10,760,1.2)]
    if name in ('lake','valley'):positions=positions[:4]
    for x,y,s in positions:
        body+=tree(x,y,s,leaf,name=='summit')
    for x,y,s in [(185,390,.65),(55,710,.8),(747,355,.75)]:body+=rock(x,y,s)
    # Surface detail is deliberately confined to the scenery banks.
    for n in range(34):
        x=rng.choice([rng.randrange(12,190),rng.randrange(690,790)]);y=rng.randrange(25,780)
        if name=='lake' and x>600:continue
        body+=f'<path d="M{x-5} {y}l-3-7m8 7v-10m3 10 5-6" stroke="{leaf}" opacity=".38" stroke-width="2" fill="none" stroke-linecap="round"/>'
        if name in ('garden','music') and n%3==0:
            body+=f'<circle cx="{x}" cy="{y-12}" r="4" fill="{["#fff5de","#edb782","#e4c9db"][n%3]}"/><circle cx="{x}" cy="{y-12}" r="1.5" fill="#d1a14e"/>'
    # Broad highlights and cool shadows unify the illustrated objects into a landscape.
    body+='''<defs><radialGradient id="sun"><stop stop-color="#fffbe1" stop-opacity=".4"/><stop offset="1" stop-color="#fffbe1" stop-opacity="0"/></radialGradient><linearGradient id="haze" x2="0" y2="1"><stop stop-color="#f8fcf2" stop-opacity=".26"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#31584f" stop-opacity=".06"/></linearGradient></defs><ellipse cx="210" cy="85" rx="430" ry="290" fill="url(#sun)"/><rect width="800" height="800" fill="url(#haze)"/>'''
    ROOT.joinpath(f'terrain-{name}.svg').write_text(svg(body))
    # A transparent foreground layer sits above the terrain, below lessons and companions.
    foreground=tree(-5,355,1.55,leaf,name=='summit')+tree(815,700,1.65,leaf,name=='summit')
    if name=='forest':foreground+=tree(810,145,1.35,leaf)
    # Darker, partially cropped foliage frames the scene without covering its center.
    foreground+=f'<g fill="{leaf}" opacity=".9"><ellipse cx="-12" cy="510" rx="40" ry="18" transform="rotate(-35 -12 510)"/><ellipse cx="12" cy="542" rx="37" ry="15" transform="rotate(24 12 542)"/><ellipse cx="799" cy="335" rx="42" ry="19" transform="rotate(30 799 335)"/><ellipse cx="808" cy="370" rx="40" ry="17" transform="rotate(-25 808 370)"/></g>'
    ROOT.joinpath(f'foreground-{name}.svg').write_text(svg(foreground))
