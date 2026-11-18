from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import gzip
import json


@dataclass(frozen=True)
class Conversation:
    source_id: str
    split: str
    turns: tuple
    alignment_ok: bool


def read_abcd(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        data=json.load(stream)
    if not isinstance(data,dict) or set(data)!={'train','dev','test'}:
        raise ValueError('invalid_dataset_root')
    valid=[];bad=[];seen=set();counts={};roles=Counter()
    for split in ('train','dev','test'):
        rows=data[split]
        if not isinstance(rows,list):raise ValueError('invalid_split')
        counts[split]=len(rows)
        for index,row in enumerate(rows):
            reason=None
            if not isinstance(row,dict) or type(row.get('convo_id')) not in (int,str) or str(row.get('convo_id','')).strip()=='':
                reason='missing_id'
            else:
                cid=str(row['convo_id'])
                if cid in seen:reason='duplicate_id'
                seen.add(cid)
            original=row.get('original') if isinstance(row,dict) else None
            if reason is None and (not isinstance(original,list) or not original):reason='missing_turns'
            if reason is None:
                for turn in original:
                    if not isinstance(turn,(list,tuple)) or len(turn)!=2:
                        reason='invalid_turn';break
                    role,text=turn
                    if role not in {'customer','agent','action'}:reason='unknown_role';break
                    if not isinstance(text,str) or not text.strip():reason='missing_text';break
            if reason is None and not any(r=='customer' for r,_ in original):reason='no_customer_text'
            if reason:
                bad.append({'source_split':split,'row_index':index,'reason':reason})
                continue
            delexed=row.get('delexed',[])
            alignment=isinstance(delexed,list) and len(delexed)==len(original) and all(isinstance(t,dict) and t.get('speaker')==r for t,(r,_) in zip(delexed,original))
            roles.update(r for r,_ in original)
            valid.append(Conversation(cid,split,tuple(tuple(t) for t in original),alignment))
    # Không chuyển scenario/targets/candidates ra khỏi ranh giới custodian reader.
    return valid,bad,{'split_read':counts,'role_turn_counts':dict(roles),'read':sum(counts.values())}


def read_ontology(path):
    with open(path,encoding='utf-8-sig') as stream:data=json.load(stream)
    intents=data.get('intents',{});flows=intents.get('flows');subs=intents.get('subflows')
    if not isinstance(flows,list) or not isinstance(subs,dict) or set(flows)!=set(subs) or len(flows)!=len(set(flows)):
        raise ValueError('invalid_ontology')
    if any(not isinstance(s,list) or len(s)!=len(set(s)) or any(not isinstance(v,str) for v in s) for s in subs.values()):
        raise ValueError('invalid_subflows')
    names=data.get('values',{}).get('enumerable',{}).get('customer_name',[])
    return {'flow_count':len(flows),'subflow_count':sum(map(len,subs.values())),'pii_name_lexicon':names}
