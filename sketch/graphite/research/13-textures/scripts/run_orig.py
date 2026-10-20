import sys,json,numpy as np
from PIL import Image
sys.path.insert(0,sys.argv[2]); from metrics import stats
IMG=sys.argv[1]; names=['noise','paper','cotman','langton','mermaid2','monval_tradition','muse_touch','wargman']
out={}
for n in names:
    a=np.asarray(Image.open(f'{IMG}/{n}.png')).astype(float)
    r,rad=stats(a[...,0]); r['maxchdiff']=float(np.abs(a[...,:3]-a[...,:1]).max()); out[n]=r
json.dump(out,open('orig2.json','w'),default=float,indent=1)
for k in out['noise']:
    print(f'{k:24s}',' '.join(f'{out[n][k]:9.3f}' for n in names))
