"""Package only Step 9, with recorded tests and per-file SHA-256."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from state_manager import sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    root=Path(__file__).resolve().parent;out=Path(args.output).resolve()
    if out.exists() or root in out.parents:raise ValueError('Use fresh ZIP outside Step 9 folder')
    env=os.environ.copy();env['OMP_NUM_THREADS']='2';env['OPENBLAS_NUM_THREADS']='2'
    result=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(root/'tests'),'-v'],capture_output=True,text=True,env=env)
    (root/'results/test_log.txt').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Tests failed; no ZIP created')
    files=[f for f in root.rglob('*') if f.is_file() and '__pycache__' not in f.parts
           and f.suffix!='.pyc' and f.name!='SHA256SUMS.json']
    manifest={str(f.relative_to(root)).replace('\\','/'):sha(f) for f in sorted(files)}
    (root/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2))
    files.append(root/'SHA256SUMS.json')
    with ZipFile(out,'w',compression=ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(files):z.write(f,'SupplyGrid_Step9/'+str(f.relative_to(root)).replace('\\','/'))
    with ZipFile(out) as z:
        if z.testzip():raise RuntimeError('ZIP corruption detected')
        assert all(n.startswith('SupplyGrid_Step9/') for n in z.namelist())
        assert not any(n.endswith('.joblib') or n.endswith('.csv') for n in z.namelist())
        assert all(hashlib.sha256(z.read('SupplyGrid_Step9/'+name)).hexdigest()==value for name,value in manifest.items())
    print(out,'files',len(files),'bytes',out.stat().st_size)


if __name__=='__main__':main()
