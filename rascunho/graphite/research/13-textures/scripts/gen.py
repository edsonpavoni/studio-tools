import sys,json,numpy as np
from PIL import Image
sys.path.insert(0,sys.argv[2]); from metrics import stats
from synth import *
IMG=sys.argv[1]; cfg=json.loads(sys.argv[3])
def table(g):
    u,c=np.unique(g,return_counts=True); return u.astype(float),c/c.sum()
out={}
# noise
gn=np.asarray(Image.open(IMG+'/noise.png'))[...,0].astype(float)
L,p=table(gn); nz=rank_map(white(cfg.get('seed',1)),L,p)  # i.i.d. + exact table (rank map == inverse-CDF lookup)
# paper
gp=np.asarray(Image.open(IMG+'/paper.png'))[...,0].astype(float)
L2,p2=table(gp)
h=np.zeros((N,N)); r=mulberry32(cfg.get('seed',1)+7)
for (sx,sy,amp) in cfg['oct']:
    n=np.array([r() for _ in range(N*N)]).reshape(N,N)-0.5
    b=blur(n,sx,sy) if sx>0 else n
    h+=amp*b/b.std()
pp=rank_map(h,L2,p2)
for nm,o,gg in (('noise',gn,nz),('paper',gp,pp)):
    Image.fromarray(gg.astype(np.uint8)).save(f'gen_{nm}.png')
    so,_=stats(o); sg,_=stats(gg); out[nm]=(so,sg)
keys=['mean','std','p1','p5','p25','p50','p75','p95','p99','skew','ac1x','ac1y','ac2x','ac2y','ac4x','ac4y','ac8x','ac8y','fcent','fpeak_cyc512','slope_4_128','slope_128_255','E_lo(<16)','E_mid(16-64)','E_hi(>=64)','aniso_ratio','spec_peak_deg','lc1','lc2','lc4','lc8','hi_frac','hi_blob_mean_px','hi_largest4','hi_largest8','pit_frac','pit_blob_mean_px','pit_largest4','hw50_x','hw50_y','seamLR_corr','seamTB_corr','interior_corr_x']
print(f"{'metric':22s} {'noise.orig':>10s} {'noise.gen':>10s} {'paper.orig':>10s} {'paper.gen':>10s}")
for k in keys: print(f"{k:22s} {out['noise'][0][k]:10.3f} {out['noise'][1][k]:10.3f} {out['paper'][0][k]:10.3f} {out['paper'][1][k]:10.3f}")
json.dump({k:[{kk:float(vv) for kk,vv in d.items()} for d in v] for k,v in out.items()},open('compare.json','w'),indent=1)
