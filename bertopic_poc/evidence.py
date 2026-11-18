from __future__ import annotations
import hashlib
from tokenizers import Tokenizer
from .io import ROOT, sha256
from .policy import model_text
from .text import content_status, spans


class EvidenceTokenizer:
    def __init__(self, entry):
        self.entry=entry
        self.path=ROOT/entry['tokenizer_directory']/'tokenizer.json'
        if sha256(self.path)!=entry['file_sha256']['tokenizer.json']:
            raise ValueError('tokenizer_hash_mismatch')
        self.tokenizer=Tokenizer.from_file(str(self.path))
        self.tokenizer.no_padding();self.tokenizer.no_truncation()

    def offsets(self,text):
        return self.tokenizer.encode(text,add_special_tokens=False).offsets

    def windows(self,text,max_tokens=200,overlap=20):
        offsets=self.offsets(text)
        if len(offsets)<=max_tokens:
            return [(0,len(text))] if text else []
        # Ranh giới chỉ ở token offsets; luôn re-encode để bảo đảm <=200.
        windows=[];start=0
        while start<len(text):
            local=self.offsets(text[start:])
            if len(local)<=max_tokens:
                windows.append((start,len(text)));break
            end=local[max_tokens-1][1]
            while end>0 and len(self.offsets(text[start:start+end]))>max_tokens:
                end-=1
            if end<=0:raise ValueError('token_window_no_progress')
            windows.append((start,start+end))
            accepted=self.offsets(text[start:start+end])
            back=accepted[max(0,len(accepted)-overlap)][0]
            next_start=start+back
            if next_start<=start:next_start=start+end
            start=next_start
        return windows


def opaque_id(value):
    return hashlib.sha256(('abcd-v1.1:'+str(value)).encode()).hexdigest()[:24]


def evidence_rows(conversation_id,split,masked_turns,tokenizer,*,experiment_id,run_id):
    for turn_index,(role,text) in enumerate(masked_turns):
        if role!='customer':continue
        for a,b in spans(text):
            unit_id=f'{conversation_id}_t{turn_index}_s{a}_{b}'
            unit=text[a:b]
            status=content_status(unit)
            for wi,(left,right) in enumerate(tokenizer.windows(unit)):
                feature=dict(conversation_id=conversation_id,source_split=split,
                    segment_id=f'{unit_id}_w{wi}',evidence_unit_id=unit_id,
                    customer_turn_index=turn_index,span_start=a+left,span_end=a+right,
                    masked_customer_text=unit[left:right],context_turn_indices=[],context_text=None,
                    language='en',preprocessing_version='1.0.0')
                model_text(feature)  # allowlist trước khi thêm các trường envelope/schema.
                yield dict(schema_version='1.0.0',experiment_id=experiment_id,run_id=run_id,
                           **feature,content_status=status)


def feature_projection(row):
    from .policy import FEATURE_FIELDS
    return {k:v for k,v in row.items() if k in FEATURE_FIELDS}
