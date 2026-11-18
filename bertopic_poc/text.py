from __future__ import annotations
import re
import unicodedata

NON_NEED={'hi','hello','hey','good morning','good afternoon','good evening','thanks','thank you','thank you very much','bye','goodbye','have a nice day'}
INSUFFICIENT={'yes','no','ok','okay','sure','that one','it','this'}
ABBREVIATIONS={'mr.','mrs.','ms.','dr.','st.','e.g.','i.e.'}


def normalize(text):
    return re.sub(r'[^\S\n]+',' ',unicodedata.normalize('NFC',text.replace('\r\n','\n').replace('\r','\n'))).strip()


class Masker:
    def __init__(self,names=()):
        self.names=sorted((n for n in names if isinstance(n,str) and n.strip()),key=len,reverse=True)
        self.name_regex=re.compile(r'\b(?:'+ '|'.join(re.escape(n) for n in self.names)+r')\b',re.I) if self.names else None

    def __call__(self,text):
        t=normalize(text)
        t=re.sub(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b','<EMAIL>',t,flags=re.I)
        t=re.sub(r'(?<!\w)(?:\+\d{1,3}[ -]?)?(?:\(\d{3}\)[ -]?\d{3}[ -]?\d{4}|\d{3}[.-]\d{3}[.-]\d{4})(?!\w)','<PHONE>',t)
        t=re.sub(r'\b\d{1,6}\s+(?:[A-Za-z0-9]+\s+){0,5}(?:street|avenue|road|lane|drive|boulevard|court|st|ave|rd|ln|dr|blvd|ct)\b','<ADDRESS>',t,flags=re.I)
        t=re.sub(r'\b(?:order\s*(?:id|number|#)|account\s*(?:id|number)|zip\s*code|pin(?:\s*number)?)\s*[:#]?\s*[A-Za-z0-9_-]*\d[A-Za-z0-9_-]*\b','<ID>',t,flags=re.I)
        t=re.sub(r'\b(?:username|security answer)\s*:\s*[^\s,;]+','<ID>',t,flags=re.I)
        t=re.sub(r'(?<!\w)\d{7,}(?!\w)','<ID>',t)
        t=re.sub(r'(?<!\w)\d{5}(?:-\d{4})?(?!\w)','<ID>',t)
        if self.name_regex:t=self.name_regex.sub('<PERSON>',t)
        t=re.sub(r'\b(?:my name is|name\s*:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',lambda m:m.group(0)[:m.start(1)-m.start()]+'<PERSON>',t)
        return normalize(t)


def content_status(text):
    without_markers=re.sub(r'<(?:PERSON|EMAIL|PHONE|ADDRESS|ID)>','',text)
    if not without_markers.strip(' \t\n.,!?;:-\"\''):return 'non_need'
    value=text.casefold().strip()
    while value and unicodedata.category(value[0]).startswith('P'):value=value[1:]
    while value and unicodedata.category(value[-1]).startswith('P'):value=value[:-1]
    value=' '.join(value.split())
    if value in NON_NEED:return 'non_need'
    if value in INSUFFICIENT:return 'insufficient_evidence'
    return 'analyzable'


def spans(text):
    start=0
    def trimmed(a,b):
        while a<b and text[a].isspace():a+=1
        while b>a and text[b-1].isspace():b-=1
        return a,b
    for i,ch in enumerate(text):
        split=ch in ';\n'
        if ch in '.?!':
            decimal=ch=='.' and i>0 and i+1<len(text) and text[i-1].isdigit() and text[i+1].isdigit()
            word=re.search(r'[A-Za-z.]+$',text[:i+1])
            abbreviation=word and word.group().lower() in ABBREVIATIONS
            split=not decimal and not abbreviation and (i+1==len(text) or text[i+1].isspace())
        if split:
            a,b=trimmed(start,i+1)
            if a<b:yield a,b
            start=i+1
    a,b=trimmed(start,len(text))
    if a<b:yield a,b
