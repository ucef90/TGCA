from pathlib import Path
import math, html, random
import cairosvg
OUTPUT=Path('/mnt/data/TGCA_Site_Professionnel_2026/static/img/plans3d')
OUTPUT.mkdir(exist_ok=True, parents=True)
# Isometric illustrative room schematics. Draw geometry directly in editable SVG.
COLORS={
 'living':'#e9dfcc','salon':'#ead8c1','bed':'#e2e2d6','kitchen':'#dfd9c9','bath':'#d3e3df',
 'terrace':'#d3c4a9','office':'#e2d8c6','pool':'#9ed2da','garden':'#b6c8a8','entrance':'#e7e1d5'
}
room_sets = {
'villa-patio':[
 (0,0,7,6,'Grand séjour','living'),(7,0,4,6,'Cuisine ouverte','kitchen'),(11,0,5,6,'Suite principale','bed'),
 (0,6,6,6,'Chambre invités','bed'),(6,6,4,6,'Hall / bureau','office'),(10,6,6,6,'Terrasse / jardin','terrace')],
'appartement-3-chambres':[
 (0,0,7,6,'Salon / repas','living'),(7,0,4,6,'Cuisine','kitchen'),(11,0,5,6,'Chambre 1','bed'),
 (0,6,6,6,'Chambre 2','bed'),(6,6,4,6,'S. de bains','bath'),(10,6,6,6,'Chambre 3','bed')],
'riad-contemporain':[
 (0,0,6,6,'Salon marocain','salon'),(6,0,4,6,'Patio central','garden'),(10,0,6,6,'Suite','bed'),
 (0,6,6,6,'Salon / repas','living'),(6,6,4,6,'Bassin','pool'),(10,6,6,6,'Cuisine','kitchen')],
'etage-residentiel':[
 (0,0,8,6,'Appartement A','living'),(8,0,8,6,'Appartement B','living'),
 (0,6,6,6,'Appartement C','bed'),(6,6,4,6,'Hall commun','entrance'),(10,6,6,6,'Appartement D','bed')]
}

def create(slug,rooms):
    parts=[]
    def p(x,y,z=0): return (round(615+34*(x-y),1),round(140+19.5*(x+y)-z,1))
    def path(points,fill,stroke='none',sw=1,opacity=1):
        coords=' '.join(f'{p[0]},{p[1]}' for p in points)
        parts.append(f'<polygon points="{coords}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}" stroke-linejoin="round" />')
    def path3(rect,z,fill,stroke='none',sw=1):
        x,y,w,d=rect;path([p(x,y,z),p(x+w,y,z),p(x+w,y+d,z),p(x,y+d,z)],fill,stroke,sw)
    def cube(x,y,w,d,h,top='#ffffff',side='#7a7167'):
        path([p(x,y,0),p(x+w,y,0),p(x+w,y,h),p(x,y,h)],side,'#ffffff33')
        path([p(x+w,y,0),p(x+w,y+d,0),p(x+w,y+d,h),p(x+w,y,h)],side,'#ffffff33')
        path3((x,y,w,d),h,top,'#ffffffad',1)
    def round_item(x,y,r,fill='#488173'):
        a,b=p(x,y,10);parts.append(f'<ellipse cx="{a}" cy="{b}" rx="{r*20}" ry="{r*11}" fill="{fill}" stroke="#ffffff77" stroke-width="2"/>')
    def label(text,x,y,size=14):
        a,b=p(x,y,8);text=html.escape(text)
        parts.append(f'<text x="{a}" y="{b}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" font-weight="700" fill="#14304a" stroke="none" text-anchor="middle">{text}</text>')
    # Back and side walls, non-occluding open view
    for x,y,w,d,_,kind in rooms:
        h=43
        path([p(x,y,0),p(x+w,y,0),p(x+w,y,h),p(x,y,h)],'#eee9e1','#aa9a88',1.5,.90)
        path([p(x,y,0),p(x,y+d,0),p(x,y+d,h),p(x,y,h)],'#dad4cb','#a79787',1.5,.90)
        path([p(x,y,h),p(x+w,y,h),p(x+w,y,h-3),p(x,y,h-3)],'#b39159')

    for x,y,w,d,name,kind in rooms:
        color=COLORS[kind]
        path3((x,y,w,d),0,color,'#b9b2a5',2)
        for j in range(1,4):
            x2=x+w*j/4
            path([p(x2,y),p(x2,y+d)],'#ffffff00','#faf7f088',.8)
        if kind in ('living','salon'):
            cube(x+.9,y+1.0,2.6,.9,.52,'#f9f4e9','#ada69b')
            cube(x+1.0,y+2.6,1.2,1,.25,'#ad7547','#8d674b')
            cube(x+4.5,y+1.5,.8,2,.50,'#e5dac9','#a09a91')
        elif kind == 'kitchen':
            cube(x+.35,y+.7,w-.8,.7,.72,'#d1bc96','#a49a8f')
            cube(x+1.4,y+3.0,min(2,w-1.8),1,.75,'#f7f4eb','#ad9f8b')
        elif kind=='bed':
            cube(x+1.0,y+1.0,min(w-1.4,2.4),2.9,.40,'#eee9df','#c9c2b4')
            cube(x+1.2,y+1.1,1,.6,.51,'#fffafa','#b4a99c')
            cube(x+2.3,y+1.1,.8,.6,.51,'#fffafa','#b4a99c')
        elif kind=='bath':
            cube(x+.6,y+.9,2.1,1.3,.4,'#fafafa','#a9c5c2')
            round_item(x+2.6,y+4,.6,'#8ac1c4')
        elif kind=='office':
            cube(x+.8,y+1.2,1.6,1.2,.7,'#a87951','#9b795c')
            round_item(x+2.5,y+4,.5,'#78a58a')
        elif kind=='terrace':
            cube(x+.65,y+1.1,3,.95,.35,'#f1e6d3','#bca58a')
            round_item(x+w-1.2,y+1.3,.65)
            round_item(x+1.3,y+d-1,.5)
        elif kind=='garden':
            round_item(x+1,y+1,.75);round_item(x+w-1,y+d-1,.75)
        elif kind=='pool':
            cube(x+.5,y+.8,w-1,3,.10,'#72b9c8','#5596a3')
        elif kind=='entrance':
            cube(x+1,y+2,1.7,1,.38,'#bb8b56','#a78b73')
        label(name,x+w/2,y+d-1.15,12.5 if len(name)>14 else 14)
    # Exterior edge visual
    path([p(0,0),p(16,0),p(16,12),p(0,12)],'none','#8e8b84',3)
    title={'villa-patio':'VILLA CONTEMPORAINE · PATIO','appartement-3-chambres':'APPARTEMENT · 3 CHAMBRES','riad-contemporain':'RIAD · PATIO CENTRAL','etage-residentiel':'IMMEUBLE · ÉTAGE TYPE'}[slug]
    prefix=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 860" role="img" aria-label="Plan architectural 3D isométrique {html.escape(title)}">
    <defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#eff3f4"/><stop offset="1" stop-color="#e2e8e7"/></linearGradient>
    <filter id="shadow"><feGaussianBlur stdDeviation="17"/></filter></defs>
    <rect width="1280" height="860" rx="22" fill="url(#bg)" />
    <circle cx="1130" cy="110" r="195" fill="#f4e6c9" opacity=".32"/><circle cx="185" cy="750" r="230" fill="#d0e2e0" opacity=".4" />
    <text x="58" y="64" fill="#bd8a3c" font-size="16" font-weight="700" font-family="Arial" letter-spacing="3">TGCA · ARCHITECTURE &amp; CONSTRUCTION</text>
    <text x="58" y="107" fill="#0b2a47" font-size="28" font-weight="750" font-family="Arial">{title}</text>
    <ellipse cx="620" cy="620" rx="455" ry="100" fill="#5b6b72" opacity=".14" filter="url(#shadow)" />'''
    suffix='<text x="59" y="813" font-size="15" fill="#5f7080" font-family="Arial">Perspective 3D conceptuelle · non contractuelle · aménagement adaptable</text><text x="1208" y="814" text-anchor="end" font-size="15" fill="#bd8a3c" font-family="Arial" font-weight="700">TGCA SARL.AU</text></svg>'
    dest=OUTPUT/(slug+'.svg');dest.write_text(prefix+'\n'+'\n'.join(parts)+'\n'+suffix,encoding='utf-8')
    png=OUTPUT/(slug+'.png')
    cairosvg.svg2png(bytestring=dest.read_bytes(),write_to=str(png),output_width=1152,output_height=774)
    print(dest.name,png.stat().st_size)

for slug,rooms in room_sets.items():create(slug,rooms)
