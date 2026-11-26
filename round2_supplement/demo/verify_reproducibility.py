#!/usr/bin/env python3
"""Run the published generation/coding path twice and compare exact bytes."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parent

def inventory():
    paths=sorted(p for folder in ['inputs','results'] for p in (ROOT/folder).rglob('*') if p.is_file())
    paths += [ROOT/name for name in ['main_results.tex','overview.tex','manifest.json','runtime.json']]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def main():
    subprocess.run([sys.executable,str(ROOT/'run_all.py')],check=True,capture_output=True,text=True)
    first=inventory()
    subprocess.run([sys.executable,str(ROOT/'run_all.py')],check=True,capture_output=True,text=True)
    second=inventory()
    if first!=second:
        differences=sorted(k for k in set(first)|set(second) if first.get(k)!=second.get(k))
        raise AssertionError('Nonidentical regenerated files: '+', '.join(differences))
    result={'status':'PASS','runs':2,'compared_files':len(first),
            'comparison':'SHA-256 of every generated input, result, table, overview, manifest and runtime file',
            'aggregate_sha256':hashlib.sha256(json.dumps(first,sort_keys=True).encode()).hexdigest(),
            'file_sha256':first,'scope':'exact regeneration in the tested interpreter; no external validity claim'}
    (ROOT/'reproducibility.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='file_sha256'},indent=2))

if __name__=='__main__':
    main()
