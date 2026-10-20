import sys, zlib, struct, os, glob
def read_png(path):
    d=open(path,'rb').read(); assert d[:8]==b'\x89PNG\r\n\x1a\n'
    pos=8; idat=b''; w=h=0; ct=0
    while pos<len(d):
        ln=struct.unpack('>I',d[pos:pos+4])[0]; typ=d[pos+4:pos+8]; body=d[pos+8:pos+8+ln]; pos+=12+ln
        if typ==b'IHDR': w,h,bd,ct=struct.unpack('>IIBB',body[:10]); assert bd==8
        elif typ==b'IDAT': idat+=body
    raw=zlib.decompress(idat); ch={6:4,2:3,0:1,4:2}[ct]; stride=w*ch
    out=bytearray(w*h*4); prev=bytearray(stride); p=0
    for y in range(h):
        f=raw[p]; p+=1; line=bytearray(raw[p:p+stride]); p+=stride
        for i in range(stride):
            a=line[i-ch] if i>=ch else 0; b=prev[i]; c=prev[i-ch] if i>=ch else 0
            if f==1: line[i]=(line[i]+a)&255
            elif f==2: line[i]=(line[i]+b)&255
            elif f==3: line[i]=(line[i]+((a+b)>>1))&255
            elif f==4:
                pa=abs(b-c); pb=abs(a-c); pc=abs(a+b-2*c)
                pr=a if pa<=pb and pa<=pc else (b if pb<=pc else c)
                line[i]=(line[i]+pr)&255
        prev=line
        for x in range(w):
            o=(y*w+x)*4
            if ch==4: out[o:o+4]=line[x*4:x*4+4]
            elif ch==3: out[o:o+3]=line[x*3:x*3+3]; out[o+3]=255
            elif ch==1: out[o]=out[o+1]=out[o+2]=line[x]; out[o+3]=255
            elif ch==2: out[o]=out[o+1]=out[o+2]=line[x*2]; out[o+3]=line[x*2+1]
    return w,h,out
def write_png(path,w,h,rgb):
    raw=b''.join(b'\x00'+bytes(rgb[y*w*3:(y+1)*w*3]) for y in range(h))
    def chunk(t,b): return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
    open(path,'wb').write(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
sheet,outp=sys.argv[1],sys.argv[2]
tiles={}
for f in glob.glob(os.path.join(sheet,'*.png')):
    tx,ty=map(int,os.path.basename(f)[:-4].split('_')); tiles[(tx,ty)]=read_png(f)
xs=[k[0] for k in tiles]; ys=[k[1] for k in tiles]; TS=256
W=(max(xs)-min(xs)+1)*TS; H=(max(ys)-min(ys)+1)*TS
img=bytearray(b'\xff'*(W*H*3))
for (tx,ty),(w,h,px) in tiles.items():
    ox=(tx-min(xs))*TS; oy=(ty-min(ys))*TS
    for y in range(h):
        for x in range(w):
            i=(y*w+x)*4; o=((oy+y)*W+ox+x)*3; a=px[i+3]/255
            for c in range(3): img[o+c]=int(px[i+c]*a+255*(1-a))
write_png(outp,W,H,img); print(outp,W,H,len(tiles),'tiles')
