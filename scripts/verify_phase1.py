"""Chạy tests và ghi bằng chứng máy đọc trong workspace."""
import argparse
import json
import sys
import time
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT,write_json,sha256


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['foundation','all'],default='all');args=p.parse_args()
    pattern='test_foundation.py' if args.stage=='foundation' else 'test_*.py'
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern)
    ids=[]
    def collect(s):
        for t in s:
            if isinstance(t,unittest.TestSuite):collect(t)
            else:ids.append(t.id())
    collect(suite)
    before=time.time();result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(schema_version='1.0.0',experiment_id='phase1',run_id='bootstrap',stage=args.stage,
        tests_run=result.testsRun,failures=[(t.id(),e) for t,e in result.failures],errors=[(t.id(),e) for t,e in result.errors],
        skipped=[(t.id(),e) for t,e in result.skipped],test_ids=ids,pass_status=result.wasSuccessful(),duration_seconds=time.time()-before,
        test_file_sha256={str(f.relative_to(ROOT)):sha256(f) for f in sorted((ROOT/'tests').glob('test_*.py'))})
    write_json(ROOT/'artifacts/phase1/bootstrap'/('tests_'+args.stage+'.json'),report)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__=='__main__':main()
