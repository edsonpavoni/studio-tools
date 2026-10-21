import sys,numpy as np
from PIL import Image, ImageDraw
IMG=sys.argv[1]
def g(p): a=np.asarray(Image.open(p)); return a[...,0] if a.ndim==3 else a
def lab(im,t):
    im=Image.fromarray(im).convert('RGB'); d=ImageDraw.Draw(im); d.rectangle([0,0,8*len(t)+8,16],fill=(255,255,255)); d.text((4,3),t,fill=(200,0,0)); return np.asarray(im)
def x4(a): return np.asarray(Image.fromarray(a[:128,:128]).resize((512,512),Image.NEAREST))
sep=np.full((512,8,3),255,np.uint8)
rows=[]
for n in ('noise','paper'):
    o=g(f'{IMG}/{n}.png'); s=g(f'gen_{n}.png')
    rows.append(np.hstack([lab(o,n+' orig'),sep,lab(s,n+' generated'),sep,lab(x4(o),'orig 4x crop'),sep,lab(x4(s),'gen 4x crop')]))
Image.fromarray(np.vstack([rows[0],np.full((8,rows[0].shape[1],3),255,np.uint8),rows[1]])).save('comparison_noise_paper.png')
# tiling check 2x2 of generated
for n in ('noise','paper'):
    s=g(f'gen_{n}.png'); Image.fromarray(np.tile(s,(2,2))[256:768,256:768]).save(f'gen_{n}_tilecheck.png')
# contact sheet: 8 originals 256 crops + 2 generated, labelled
names=['noise','paper','cotman','langton','mermaid2','monval_tradition','muse_touch','wargman']
tiles=[lab(g(f'{IMG}/{n}.png')[:256,:256],n) for n in names]+[lab(g('gen_noise.png')[:256,:256],'GEN noise'),lab(g('gen_paper.png')[:256,:256],'GEN paper')]
blank=np.full((256,256,3),255,np.uint8); tiles+= [blank,blank]
r=[np.hstack(tiles[i:i+4]) for i in range(0,12,4)]
Image.fromarray(np.vstack(r)).save('contact_sheet.png')
