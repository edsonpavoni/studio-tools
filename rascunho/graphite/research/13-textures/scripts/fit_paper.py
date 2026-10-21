import sys,json,numpy as np
from PIL import Image
from scipy.optimize import least_squares
sys.path.insert(0,sys.argv[2]); from metrics import psd,R,FX,FY
from synth import kernel,N
g=np.asarray(Image.open(sys.argv[1]+'/paper.png'))[...,0].astype(float)
P=psd(g); P/=P[R>0].mean()
sig=[0,0.5,1,2,4,8,16]
rb=np.clip(np.floor(np.log2(np.maximum(R,1))*4).astype(int),0,40)
ang=(np.degrees(np.arctan2(FY,FX))%180)//45
bins=(rb*4+ang).astype(int); valid=(R>=2)&(R<256)
def bavg(X):
    s=np.bincount(bins[valid],X[valid],minlength=164); c=np.bincount(bins[valid],minlength=164); return s/np.maximum(c,1),c
Pb,cnt=bavg(P); ok=cnt>0
def transfer(s):
    if s<=0: return np.ones(N)
    k=kernel(s); R_=len(k)//2; imp=np.zeros(N)
    for i,w in enumerate(k): imp[(i-R_)%N]+=w
    return np.abs(np.fft.fft(imp))**2
best=None
for a in np.arange(1.0,2.01,0.1):
    cols=[]
    for s in sig:
        M=np.outer(transfer(s),transfer(s*a)); M=M/M[R>0].mean(); cols.append(bavg(M)[0][ok])
    A=np.stack(cols,1); lp=np.log(Pb[ok])
    f=lambda x: np.log(A@np.exp(x)+1e-12)-lp
    r=least_squares(f,np.full(len(sig),-2.0))
    if best is None or r.cost<best[0]: best=(r.cost,a,np.exp(r.x))
c,a,w=best
w=w/w.sum()
print('aniso',round(a,2),'sigmas',sig,'power frac',w.round(4),'amp',np.sqrt(w).round(3),'cost',round(c,3))
json.dump({'aniso':float(a),'sigmas':sig,'amp':np.sqrt(w).tolist()},open('paper_fit.json','w'))
