#!/usr/bin/env python3
"""Bounded pcap TCP reassembly; save private frames, emit protocol metadata only."""
import argparse,json,os,struct,zlib
from pathlib import Path
from inspect_capture import inspect_frame
from decode_force_call import decode_messages

def segments(path):
    data=path.read_bytes()
    assert data[:4]==b'\xd4\xc3\xb2\xa1' and struct.unpack_from('<I',data,20)[0]==1
    pos=24
    while pos<len(data):
        _,_,n,_=struct.unpack_from('<IIII',data,pos);pos+=16
        p=data[pos:pos+n];pos+=n
        if len(p)!=n:raise ValueError('truncated record')
        if len(p)<54 or p[12:14]!=b'\x08\x00' or p[23]!=6:continue
        iplen=(p[14]&15)*4;off=14+iplen
        if struct.unpack_from('!H',p,20)[0]&0x3fff:raise ValueError('fragmented IPv4 unsupported')
        size=struct.unpack_from('!H',p,16)[0]
        sport,dport,seq=struct.unpack_from('!HHI',p,off)
        tcp=(p[off+12]>>4)*4
        payload=p[off+tcp:14+size]
        if payload:yield (p[26:30].hex(),sport,p[30:34].hex(),dport),seq,payload

def reassemble(parts):
    # One bounded connection direction; sequence wrap or reuse is rejected.
    parts=sorted(parts)
    base=parts[0][0];out=bytearray()
    for seq,data in parts:
        offset=seq-base
        if offset>len(out):raise ValueError('TCP gap; refusing to guess missing bytes')
        overlap=min(len(data),len(out)-offset)
        if out[offset:offset+overlap]!=data[:overlap]:raise ValueError('conflicting TCP overlap')
        out.extend(data[overlap:])
    return bytes(out)

def frames(data):
    while data:
        if len(data)<12:raise ValueError('incomplete frame header')
        h=12+((data[0]>>4)&3)
        if len(data)<h:raise ValueError('incomplete frame header')
        size=int.from_bytes(data[11:h],'big')
        if not 4<=size<=65536 or len(data)<h+size:raise ValueError('invalid or incomplete frame body')
        frame,data=data[:h+size],data[h+size:]
        inspect_frame(frame)
        yield frame

def summarize(frame):
    info=inspect_frame(frame)
    body=frame[info['header_size']:-4]
    try:
        if info['method']==1:
            d=zlib.decompressobj();body=d.decompress(body,1048577)
            if len(body)>1048576 or not d.eof or d.unused_data:raise ValueError('compressed size/shape rejected')
        elif info['method']!=0:raise ValueError('unsupported compression')
        messages=decode_messages(body)
        info['messages']=[{'id':mid,'version':ver,'fields':list(values),
                            'opaque_bytes':sum(len(v) for v in values.values() if isinstance(v,bytes))}
                           for mid,ver,values in messages]
    except ValueError as e:
        info['decode_error']=str(e)
        if body:
            width=2 if body[0]&16 else 1
            if len(body)>=1+width:
                info['first_message_header_only']={'id':int.from_bytes(body[1:1+width],'big'),
                    'version':body[0]>>5,'flags':body[0]&15}

    return info

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pcap',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    os.umask(0o077);a.output.mkdir(mode=0o700,exist_ok=False)
    streams={}
    for key,seq,data in segments(a.pcap):streams.setdefault(key,[]).append((seq,data))
    results=[]
    for i,(key,parts) in enumerate(streams.items()):
        entry={'stream':i,'source_port':key[1],'destination_port':key[3],'frames':[]}
        try:
            for j,frame in enumerate(frames(reassemble(parts))):
                name='%02d-%02d.bin'%(i,j);(a.output/name).write_bytes(frame)
                info=summarize(frame);info['file']=name;entry['frames'].append(info)
        except ValueError as e:entry['stream_error']=str(e)
        results.append(entry)
    report={'streams':results}
    (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
