"""Chỉ tải metadata/tokenizer công khai; không đọc hội thoại hoặc tải weights."""
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT, canonical_hash, read_json, write_json
from bertopic_poc.contracts import BASE, FIELDS, KEYS


def get(url):
    request=urllib.request.Request(url,headers={'User-Agent':'BERTopic-PoC-metadata-lock/1.0'})
    with urllib.request.urlopen(request,timeout=60) as r:return r.read()


def main():
    registry=read_json(ROOT/'config/experiment_registry.json')
    for entry in registry['models']:
        model=entry['model_id']
        info=json.loads(get('https://huggingface.co/api/models/'+model+'?blobs=true'))
        revision=info['sha']
        if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('revision_not_immutable')
        license=info.get('cardData',{}).get('license')
        if license!='apache-2.0':raise ValueError('license_blocked:'+model)
        folder=ROOT/'resources/tokenizers'/model.split('/')[-1]/revision
        folder.mkdir(parents=True,exist_ok=True)
        files={item['rfilename']:item for item in info['siblings']}
        hashes={}
        for name in ['tokenizer.json','tokenizer_config.json','special_tokens_map.json','config.json','sentence_bert_config.json','README.md']:
            if name not in files:continue
            data=get('https://huggingface.co/'+model+'/resolve/'+revision+'/'+name)
            (folder/name).write_bytes(data)
            hashes[name]=hashlib.sha256(data).hexdigest()
        weights={n:v['lfs']['sha256'] for n,v in files.items() if n in ['model.safetensors','pytorch_model.bin'] and 'lfs' in v}
        if not weights:raise ValueError('missing_remote_weights_digest')
        write_json(folder/'metadata.json',info)
        entry.update(revision=revision,license=license,status='metadata_locked',tokenizer_directory=folder.relative_to(ROOT).as_posix(),file_sha256=hashes,remote_weights_sha256=weights,weights_downloaded=False,input_adapter='tokenizers-json; add_special_tokens=False; no truncation/padding; NFC text',max_text_tokens=200)
    write_json(ROOT/'config/experiment_registry.json',registry)
    schemas={'schema_version':'1.0.0','dialect':'bertopic-poc-contract-v1','required_base':BASE,'artifacts':{k:{'required_fields':v,'unique_key':['experiment_id','run_id']+KEYS[k]} for k,v in FIELDS.items()},'csv_null':'\\N'}
    write_json(ROOT/'schemas/artifacts-1.0.0.json',schemas)
    print(json.dumps({'models':[{k:e[k] for k in ['model_id','revision','license','weights_downloaded']} for e in registry['models']]},ensure_ascii=False))


if __name__=='__main__':main()
