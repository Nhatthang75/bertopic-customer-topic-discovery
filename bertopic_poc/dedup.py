from __future__ import annotations
from collections import Counter, defaultdict
import math
import re
import unicodedata


def words(text):
    return re.findall(r'\w+',unicodedata.normalize('NFC',text).casefold())


def duplicate_components(texts):
    """Exact + exact Jaccard>=.90 qua prefix filtering, không dùng MinHash xấp xỉ."""
    parent=list(range(len(texts)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    exact={};sets={}
    for i,text in enumerate(texts):
        key=' '.join(unicodedata.normalize('NFC',text).casefold().split())
        if key in exact:union(i,exact[key])
        else:exact[key]=i
        tokens=words(text)
        if len(tokens)>=20:sets[i]=set(tuple(tokens[n:n+5]) for n in range(len(tokens)-4))
    freq=Counter(token for s in sets.values() for token in s)
    index=defaultdict(list)
    comparisons=0
    for i in sorted(sets,key=lambda n:(len(sets[n]),n)):
        current=sets[i];length=len(current)
        ordered=sorted(current,key=lambda x:(freq[x],x))
        prefix=ordered[:length-math.ceil(.9*length)+1]
        candidates={j for token in prefix for j in index[token] if len(sets[j])*10>=9*length}
        for j in candidates:
            other=sets[j];common=len(current&other);comparisons+=1
            if common*10>=9*(length+len(other)-common):union(i,j)
        for token in prefix:index[token].append(i)
    groups=defaultdict(list)
    for i in range(len(texts)):groups[find(i)].append(i)
    return list(groups.values()),comparisons


def exclusions(records,texts):
    groups,comparisons=duplicate_components(texts)
    priority={'train':0,'dev':1,'test':2};excluded={};audit=[]
    for group in groups:
        if len(group)<2:continue
        highest=max(priority[records[i].split] for i in group)
        for i in group:
            if priority[records[i].split]<highest:excluded[i]='cross_split_duplicate'
        audit.append(group)
    return excluded,audit,comparisons
