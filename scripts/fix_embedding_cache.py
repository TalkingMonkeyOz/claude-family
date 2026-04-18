#!/usr/bin/env python3
"""Rebuild fastembed snapshot dir from blobs (Windows symlink failure recovery)."""
import json
import shutil
from pathlib import Path

CACHE_ROOT = Path(r'C:/Users/johnd/AppData/Local/Temp/fastembed_cache/models--qdrant--bge-large-en-v1.5-onnx')

def main():
    meta = json.loads((CACHE_ROOT / 'files_metadata.json').read_text())
    blobs_dir = CACHE_ROOT / 'blobs'
    by_hash = {p.name: p for p in blobs_dir.iterdir() if p.is_file()}
    by_size = {p.stat().st_size: p for p in blobs_dir.iterdir() if p.is_file()}

    print(f'Blobs available: {list(by_hash.keys())}\n')

    for rel_path, info in meta.items():
        dest = CACHE_ROOT / rel_path.replace('\\', '/')
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = by_hash.get(info['blob_id']) or by_size.get(info['size'])
        if not src:
            print(f'MISSING: {rel_path}')
            continue
        if dest.exists():
            print(f'OK (exists): {dest.name}')
            continue
        print(f'Copying {src.stat().st_size:,} bytes -> {dest.name}')
        shutil.copy2(src, dest)

    snap = CACHE_ROOT / 'snapshots' / 'dc76b2c078fc38f0d243233d0ab0b51de925557e'
    print('\nSnapshot contents:')
    for p in sorted(snap.iterdir()):
        print(f'  {p.name}  {p.stat().st_size:,} bytes')

if __name__ == '__main__':
    main()
