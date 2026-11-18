"""Ghi environment và snapshot G0; không mở dataset hoặc chạy mô hình."""
import importlib.metadata
import platform
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT,read_json,write_json,sha256,canonical_hash


def main():
    if sys.version_info[:2]!=(3,11):raise ValueError('python_3_11_required')
    registry=read_json(ROOT/'config/experiment_registry.json')
    if any(e['status']!='metadata_locked' for e in registry['models']):raise ValueError('model_metadata_pending')
    registry['stage']='G0_registered'
    write_json(ROOT/'config/experiment_registry.json',registry)
    packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    environment=dict(schema_version='1.0.0',experiment_id='phase1',run_id='bootstrap',python_version=platform.python_version(),python_executable=sys.executable,base_prefix=sys.base_prefix,platform=platform.platform(),packages=packages,compatibility_scope='Đã kiểm thử reader/schema/tokenizers trên Python3.11; chưa cài hoặc xác nhận runtime BERTopic',models_executed=False)
    write_json(ROOT/'artifacts/phase1/bootstrap/environment_manifest.json',environment)
    files=['config/experiment_registry.json','config/access_policy.json','schemas/artifacts-1.0.0.json','requirements-phase1.txt']
    snapshot=dict(schema_version='1.0.0',experiment_id='phase1',run_id='bootstrap',gate='G0',registry_sha256=sha256(ROOT/files[0]),file_sha256={f:sha256(ROOT/f) for f in files},evidence_status='registry_contracts_only; không phải G1, không model search/test scoring',reviewers_assigned=False,benchmark_validity='pending_preparation_and_later_gates')
    snapshot['snapshot_hash']=canonical_hash(snapshot)
    write_json(ROOT/'artifacts/phase1/bootstrap/g0_snapshot.json',snapshot)
    (ROOT/'requirements-phase1.lock').write_text(''.join(f'{name}=={version}\n' for name,version in sorted(packages.items())),encoding='utf-8')
    print('G0 registry/environment snapshot written; no G1-G3 advanced')


if __name__=='__main__':main()
