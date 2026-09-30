from __future__ import annotations
import re
from pathlib import Path
import pymupdf
from app.documents import document_id_exists, save_document
Q=re.compile(r'^\s*(?:Question|Q)\s*\.?\s*(\d+)\s*[:.]?\s*$',re.I)
HEADINGS={'solids','liquids','gases','melting point','boiling point','condensation','sublimation','vaporization','evaporation','change of state','inter-molecular spaces','inter-molecular forces of attraction'}
def norm(s):
    s=s.replace('\x00',' ').replace('\r\n','\n').replace('\r','\n'); return '\n'.join(re.sub(r'[ \t]+',' ',x).strip() for x in s.split('\n') if x.strip()).strip()
def inline(s): return re.sub(r'\s+',' ',norm(s).replace('\n',' ')).strip()
def safe(s): return re.sub(r'[^a-z0-9]+','_',Path(s).stem.lower()).strip('_') or 'document'
def unique(b):
    x=b;n=2
    while document_id_exists(x): x=f'{b}_{n}';n+=1
    return x
def blocks(answer):
    out=[]; heading=None; lines=[]
    def flush():
        nonlocal heading,lines
        t=inline('\n'.join(lines))
        if t: out.append({'heading':heading,'text':t})
        heading=None;lines=[]
    for l in answer.splitlines():
        l=l.strip()
        if not l: continue
        h=re.sub(r'[:\s]+$','',l).lower()
        if h in HEADINGS: flush();heading=re.sub(r'[:\s]+$','',l)
        else: lines.append(l)
    flush(); return out or [{'heading':None,'text':inline(answer)}]
def qna(doc):
    texts=[norm(p.get_text('text')) for p in doc]; starts=[]
    for pi,t in enumerate(texts):
        for li,l in enumerate(t.splitlines()):
            m=Q.match(l)
            if m: starts.append((int(m.group(1)),pi,li))
    if not starts:return []
    out=[]
    for i,(num,sp,sl) in enumerate(starts):
        ep,el=(starts[i+1][1],starts[i+1][2]) if i+1<len(starts) else (len(doc)-1,None)
        lines=[]
        for pi in range(sp,ep+1):
            ls=texts[pi].splitlines(); a=sl if pi==sp else 0;b=el if pi==ep and el is not None else len(ls);lines+=ls[a:b]
        ai=next((j for j,l in enumerate(lines) if re.match(r'^\s*Answer\s*:?',l,re.I)),None)
        if ai is None:continue
        question=inline('\n'.join(lines[1:ai])); ans=lines[ai:]
        if ans: ans[0]=re.sub(r'^\s*Answer\s*:?\s*','',ans[0],flags=re.I)
        answer=norm('\n'.join(ans)); ps=sp+1;pe=ep+1
        out.append({'type':'question','question_number':num,'question':question,'text':answer,'answer':answer,'answer_blocks':blocks(answer),'page':ps,'page_start':ps,'page_end':pe,'visual_support':False})
    return out
def pages(doc):
    out=[]
    for i,p in enumerate(doc,1):
        t=norm(p.get_text('text'))
        if t: out.append({'type':'page','question_number':None,'question':'','text':t,'answer':t,'answer_blocks':[{'heading':None,'text':t}],'page':i,'page_start':i,'page_end':i,'visual_support':False})
    return out
def ingest_pdf(pdf_path:Path,original_name:str|None=None):
    name=original_name or pdf_path.name; did=unique(safe(name)); doc=pymupdf.open(str(pdf_path)); records=qna(doc);mode='question_answer'
    if not records: records=pages(doc);mode='page'
    for r in records: r['document_id']=did
    meta={'document_id':did,'filename':name,'title':Path(name).stem,'pages':len(doc),'records':len(records),'extraction_mode':mode,'answer_engine':'chat-llm','status':'ready'}
    doc.close()
    save_document(did,meta,records)
    return meta
