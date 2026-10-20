import numpy as np
N=512
def mulberry32(seed):
    a=seed & 0xffffffff
    def nxt():
        nonlocal a
        a=(a+0x6D2B79F5)&0xffffffff
        t=a
        t=((t^(t>>15))*(t|1))&0xffffffff
        t^=(t+(((t^(t>>7))*(t|61))&0xffffffff))&0xffffffff
        return ((t^(t>>14))&0xffffffff)/4294967296.0
    return nxt
def white(seed):
    r=mulberry32(seed); return np.array([r() for _ in range(N*N)]).reshape(N,N)
def kernel(s):
    if s<=0: return np.array([1.0])
    R=int(np.ceil(3*s)); x=np.arange(-R,R+1); k=np.exp(-x*x/(2*s*s)); return k/k.sum()
def blur1(img,s,axis):
    k=kernel(s); R=len(k)//2; out=np.zeros_like(img)
    for i,w in enumerate(k): out+=w*np.roll(img,i-R,axis=axis)   # wrap = tileable
    return out
def blur(img,sx,sy): return blur1(blur1(img,sx,1),sy,0)
def rank_map(h,levels,probs):
    # assign quantised levels by rank so the histogram matches exactly
    order=np.argsort(h.ravel(),kind='stable'); out=np.empty(N*N)
    cum=np.round(np.cumsum(probs)/np.sum(probs)*N*N).astype(int); start=0
    for L,c in zip(levels,cum): out[order[start:c]]=L; start=c
    return out.reshape(N,N)
def octaves(seed,sigmas,weights,aniso):
    r=mulberry32(seed); h=np.zeros((N,N))
    for s,w in zip(sigmas,weights):
        if w==0: continue
        n=np.array([r() for _ in range(N*N)]).reshape(N,N)-0.5
        b=blur(n,s*aniso,s) if s>0 else n
        h+=w*b/b.std()
    return h
