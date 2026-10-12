"""Download public snapshots and exercise the production ZIP scanner. Never execute upstream code."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import time
import zipfile
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.analysis.repository_analyzer import (analyze_repository_zip, SUPPORTED_SUFFIXES,
    IGNORED_PARTS, MAX_FILE_BYTES, MAX_SOURCE_FILES, MAX_TOTAL_SOURCE_BYTES)

CACHE = ROOT / 'benchmark_cache'
OUT = ROOT / 'Evaluation_Results' / 'public_benchmark'
QUERIES = [
    'automotive language:C fork:false size:10..6000',
    'CAN bus language:C++ fork:false size:10..6000',
    'ECU language:C++ fork:false size:10..6000',
    'topic:embedded language:C fork:false size:10..6000',
]


def scan_snapshot(meta):
    start = time.perf_counter()
    name = meta['full_name']
    dest = CACHE / (name.replace('/', '__') + '.zip')
    result = dict(repository=name, url=meta['html_url'], category_query=meta['category_query'],
                  branch=meta['default_branch'], metadata_pushed_at=meta['pushed_at'],
                  license=(meta.get('license') or {}).get('spdx_id'), status='failed')
    try:
        if not dest.exists():
            url = f"https://codeload.github.com/{name}/legacy.zip/refs/heads/{meta['default_branch']}"
            response = requests.get(url, timeout=(10, 60), stream=True)
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > 40 * 1024 * 1024:
                    raise ValueError('Download exceeded 40 MB benchmark boundary')
            dest.write_bytes(data)
        raw = dest.read_bytes()
        result['archive_sha256'] = hashlib.sha256(raw).hexdigest()
        sources = []
        excluded = []
        expanded_bytes = 0
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            result['snapshot_root'] = archive.namelist()[0].split('/')[0]
            for entry in sorted(archive.infolist(), key=lambda i: i.filename):
                path = PurePosixPath(entry.filename)
                if entry.is_dir() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                    continue
                reason = None
                if any(p.lower() in IGNORED_PARTS for p in path.parts[:-1]): reason = 'ignored-directory'
                elif entry.file_size > MAX_FILE_BYTES: reason = 'source-size-limit'
                if reason:
                    excluded.append(dict(path=str(path), reason=reason)); continue
                expanded_bytes += entry.file_size
                if expanded_bytes > 25 * 1024 * 1024:
                    raise ValueError('Supported expanded source exceeded 25 MB benchmark boundary')
                data = archive.read(entry)
                try: data.decode('utf-8')
                except UnicodeDecodeError:
                    excluded.append(dict(path=str(path), reason='non-UTF8')); continue
                if b'\x00' in data:
                    excluded.append(dict(path=str(path), reason='binary')); continue
                sources.append((str(path), data))
        if not sources: raise ValueError('No eligible C/C++ sources')
        batches = []; current = []; size = 0
        for item in sources:
            if current and (len(current) >= MAX_SOURCE_FILES or size + len(item[1]) > MAX_TOTAL_SOURCE_BYTES):
                batches.append(current); current = []; size = 0
            current.append(item); size += len(item[1])
        if current: batches.append(current)
        findings = []; lines = functions = 0
        file_manifest = []
        for batch in batches:
            buffer = io.BytesIO()
            # ZIP_STORED avoids benchmark-generated compression-ratio artefacts.
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as bounded:
                for path, data in batch:
                    bounded.writestr(path, data)
                    file_manifest.append(dict(path=path, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
            review = analyze_repository_zip(buffer.getvalue(), name.replace('/', '_') + '.zip')
            findings.extend(review['findings'])
            lines += review['repository_summary']['total_lines']
            functions += review['repository_summary']['function_count']
        result.update(status='scanned', files=len(sources), lines=lines, functions=functions,
                      findings=len(findings), partition_count=len(batches), excluded_files=excluded,
                      file_manifest=file_manifest, candidate_findings=[
                          {key: item.get(key) for key in ('finding_id','rule_id','title','category','severity','line','function','file','cwe','analysis_method')}
                          for item in findings],
                      scope='All eligible C/C++ files in snapshot, bounded partitions; no build or defect labels')
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    result['duration_seconds'] = round(time.perf_counter() - start, 3)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=int, default=100)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--refresh-catalog', action='store_true')
    args = parser.parse_args()
    implementation_hashes={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (ROOT/'src'/'analysis').glob('*.py')}
    CACHE.mkdir(exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    catalog_path = OUT / 'catalog.json'
    if catalog_path.exists() and not args.refresh_catalog:
        catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    else:
        catalog = []; seen = set()
        for query in QUERIES:
            response = requests.get('https://api.github.com/search/repositories',
                                    params=dict(q=query, per_page=100, sort='stars'), timeout=30)
            response.raise_for_status()
            for meta in response.json()['items']:
                if meta['full_name'] not in seen:
                    seen.add(meta['full_name']); meta['category_query'] = query; catalog.append(meta)
        catalog_path.write_text(json.dumps(catalog, indent=2), encoding='utf-8')
    all_results = []
    for begin in range(0, len(catalog), args.workers):
        if sum(r['status'] == 'scanned' for r in all_results) >= args.target: break
        needed = args.target - sum(r['status'] == 'scanned' for r in all_results)
        candidates = catalog[begin:begin + min(args.workers, needed)]
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(scan_snapshot, meta) for meta in candidates]
            for future in as_completed(futures):
                result = future.result(); all_results.append(result)
                print(f"{len(all_results):03} {result['status']} {result['repository']} files={result.get('files', 0)}", flush=True)
                (OUT / 'results.json').write_text(json.dumps(all_results, indent=2), encoding='utf-8')
    passed = [r for r in all_results if r['status'] == 'scanned']
    durations = sorted(r['duration_seconds'] for r in passed)
    summary = dict(generated_at=datetime.now(timezone.utc).isoformat(), distinct_repositories=len(passed),
                   implementation_sha256=implementation_hashes,
                   target=args.target, attempted=len(all_results), failed=len(all_results)-len(passed),
                   files=sum(r['files'] for r in passed), lines=sum(r['lines'] for r in passed),
                   candidate_findings=sum(r['findings'] for r in passed),
                   p50_total_seconds=durations[len(durations)//2] if durations else None,
                   metric_scope='Download + scan time, not analyzer-only latency',
                   limitations=['Public convenience sample, not 100 production ECUs',
                                'Unlabelled candidates do not measure precision or recall',
                                'No upstream code executed or built',
                                'Cross-partition dependencies are not resolved',
                                'Snapshot hashes and per-file hashes support audit; cache needed for exact replay'])
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 0 if len(passed) >= args.target else 1


if __name__ == '__main__':
    raise SystemExit(main())
