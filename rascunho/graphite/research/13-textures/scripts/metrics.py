import numpy as np
from scipy import ndimage as nd
N=512
def psd(u):
    # Moisan periodic component
    u=u-u.mean(); M,Nn=u.shape
    v=np.zeros_like(u)
    v[0,:]+=u[-1,:]-u[0,:]; v[-1,:]+=u[0,:]-u[-1,:]
    v[:,0]+=u[:,-1]-u[:,0]; v[:,-1]+=u[:,0]-u[:,-1]
    q=np.arange(M).reshape(-1,1); r=np.arange(Nn).reshape(1,-1)
    den=2*np.cos(2*np.pi*q/M)+2*np.cos(2*np.pi*r/Nn)-4; den[0,0]=1
    s=np.real(np.fft.ifft2(np.fft.fft2(v)/den)); s-=s.mean()
    p=u-s
    return np.abs(np.fft.fft2(p))**2
def grid():
    f=np.fft.fftfreq(N)*N; FX,FY=np.meshgrid(f,f); return FX,FY,np.hypot(FX,FY)
FX,FY,R=grid()
def radial(F):
    rb=np.round(R).astype(int); return (np.bincount(rb.ravel(),F.ravel())/np.maximum(np.bincount(rb.ravel()),1))[:N//2]
def corr(a,b): a=a-a.mean(); b=b-b.mean(); return (a*b).sum()/np.sqrt((a*a).sum()*(b*b).sum())
def lcc(b,conn):
    st=np.ones((3,3)) if conn==8 else None
    lab,n=nd.label(b,structure=st)
    if n==0: return 0,0,0
    sz=np.bincount(lab.ravel())[1:]; return n, sz.mean(), sz.max()/b.sum()
def stats(g,rng=np.random.default_rng(0)):
    r={}; m=g.mean(); s=g.std()
    r['levels']=len(np.unique(g)); r['mean']=m; r['std']=s; r['min']=g.min(); r['max']=g.max()
    for q in (1,5,25,50,75,95,99): r['p%d'%q]=np.percentile(g,q)
    r['skew']=((g-m)**3).mean()/s**3; r['exkurt']=((g-m)**4).mean()/s**4-3
    r['frac_at_max']=(g==g.max()).mean(); r['frac_at_min']=(g==g.min()).mean()
    # tiling
    ac=np.real(np.fft.ifft2(np.abs(np.fft.fft2(g-m))**2)); ac/=ac[0,0]
    r['ac1x']=ac[0,1]; r['ac1y']=ac[1,0]
    for k in (2,4,8): r['ac%dx'%k]=ac[0,k]; r['ac%dy'%k]=ac[k,0]
    r['seamLR_corr']=corr(g[:,0],g[:,-1]); r['seamTB_corr']=corr(g[0,:],g[-1,:])
    r['interior_corr_x']=np.mean([corr(g[:,i],g[:,i+1]) for i in range(0,510,17)])
    r['interior_corr_y']=np.mean([corr(g[i,:],g[i+1,:]) for i in range(0,510,17)])
    r['far_corr']=corr(g[:,0],g[:,256])
    # repeat check
    a2=ac.copy(); a2[np.hypot(*np.meshgrid(np.fft.fftfreq(N)*N,np.fft.fftfreq(N)*N))<6]=-9
    r['max_ac_far']=a2.max()
    F=psd(g); rad=radial(F)
    e=rad*np.arange(len(rad)); e[0]=0; es=nd.uniform_filter1d(e,9)
    r['fpeak_cyc512']=int(np.argmax(es)); r['fcent']=(rad[1:]*np.arange(1,256)).sum()/rad[1:].sum()
    f=np.arange(4,128); r['slope_4_128']=np.polyfit(np.log(f),np.log(rad[4:128]+1e-9),1)[0]
    f=np.arange(128,255); r['slope_128_255']=np.polyfit(np.log(f),np.log(rad[128:255]+1e-9),1)[0]
    # low/mid/high band energy fraction
    tot=F[R>0].sum()
    r['E_lo(<16)']=F[(R>0)&(R<16)].sum()/tot; r['E_mid(16-64)']=F[(R>=16)&(R<64)].sum()/tot; r['E_hi(>=64)']=F[R>=64].sum()/tot
    # orientation: angle of frequency vector, 0..180, weight, band 8<R<128
    ang=np.degrees(np.arctan2(FY,FX))%180; msk=(R>8)&(R<200)&(np.abs(FX)>1)&(np.abs(FY)>1)
    h,_=np.histogram(ang[msk],bins=36,range=(0,180),weights=F[msk]); c,_=np.histogram(ang[msk],bins=36,range=(0,180))
    h=h/np.maximum(c,1); h=nd.uniform_filter1d(h,3,mode='wrap')
    r['aniso_ratio']=h.max()/h.min(); r['spec_peak_deg']=(np.argmax(h)*5+2.5)
    # grain direction (elongation) is perpendicular to spectral peak
    r['grain_dir_deg']=(r['spec_peak_deg']+90)%180
    for sg in (1,2,4,8): r['lc%d'%sg]=(g-nd.gaussian_filter(g,sg,mode='wrap')).std()
    # peaks: tooth tops (high) and pits (low)
    thr=min(m+s,g.max()); hi=g>=thr if m+s>g.max() else g>m+s
    lo=g<m-s
    perm=rng.permutation(g.ravel()).reshape(g.shape)
    for nm,b,bp in (('hi',hi,(perm>=thr) if m+s>g.max() else perm>m+s),('pit',lo,perm<m-s)):
        r[nm+'_frac']=b.mean()
        n,mean,lf=lcc(b,4); _,_,lf8=lcc(b,8); _,mp,lfp=lcc(bp,4)
        r[nm+'_blobs']=n; r[nm+'_blob_mean_px']=mean; r[nm+'_blob_mean_shuffled']=mp; r[nm+'_largest4']=lf; r[nm+'_largest8']=lf8; r[nm+'_largest4_shuffled']=lfp
    # correlation length (x,y) where ac drops below 0.5 (fractional)
    for ax,arr in (('x',ac[0,:64]),('y',ac[:64,0])):
        k=np.argmax(arr<0.5); r['hw50_'+ax]=k-1+(arr[k-1]-0.5)/(arr[k-1]-arr[k]) if k>0 else 0
    return r,rad
