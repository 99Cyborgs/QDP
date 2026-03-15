#!/usr/bin/env python3
"""
QDP v10.6 M03 reference-resolution and governance-registry tool.

Usage examples:
  python modules/m03_reference_resolution/runner.py \
    --manifest /mnt/data/config/manifests/reference_manifest.json \
    --registry /mnt/data/config/registries/governance_registry.json \
    --root /mnt/data \
    --write-report /mnt/data/QDP_v10_6_REFERENCE_RESOLUTION_REPORT_CURRENT.json

  python modules/m03_reference_resolution/runner.py \
    --manifest /mnt/data/config/manifests/reference_manifest.json \
    --registry /mnt/data/config/registries/governance_registry.json \
    --candidate /path/to/candidate.json \
    --write-candidate /path/to/candidate_patched.json
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f'JSON root must be an object: {path}')
    return data


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def resolve_manifest(manifest: Dict[str, Any], root: Path, mode: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    resolved: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []
    for entry in manifest.get('reference_entries', []):
        modes = entry.get('modes', ['ordinary', 'subsystem'])
        if mode not in modes:
            continue
        rel = entry['relative_path']
        path = root / rel
        item = copy.deepcopy(entry)
        item['absolute_path'] = str(path)
        if path.exists():
            item['resolved'] = True
            item['sha256'] = sha256(path)
            item['bytes'] = path.stat().st_size
            resolved.append(item)
        else:
            item['resolved'] = False
            item['missing_reason'] = 'file_not_present_in_current_environment'
            unresolved.append(item)
    return resolved, unresolved


def derive_system_status(gsc: Dict[str, Any]) -> str:
    schema = gsc.get('schema_validation_status', '')
    ref = gsc.get('reference_resolution_status', '')
    vh = gsc.get('validation_harness_status', '')
    det = gsc.get('determinism_status', '')
    if schema == 'FAILED':
        return 'SCHEMA_VALIDATION_FAILURE'
    if ref == 'FAILED':
        return 'REFERENCE_RESOLUTION_FAILURE'
    if vh == 'FAILED' or det == 'FAILED':
        return 'GOVERNANCE_LOGIC_FAILURE'
    if vh == 'UNKNOWN':
        return 'HARNESS_REQUIRED'
    if vh == 'PASSED' and det == 'PASSED' and ref == 'PASSED' and schema == 'PASSED':
        return 'READY'
    return gsc.get('system_status', '') or ''


def update_candidate(candidate: Dict[str, Any], registry: Dict[str, Any], unresolved: List[Dict[str, Any]], report_id: str, linked_artifacts: List[str]) -> Dict[str, Any]:
    out = copy.deepcopy(candidate)
    gsc = out.setdefault('governance_self_check', {})
    auto_flags = out.setdefault('automatic_flags_triggered', [])
    failure_hits = out.setdefault('failure_mode_library_hits', [])

    if unresolved:
        gsc['reference_resolution_status'] = 'FAILED'
        for item in unresolved:
            flag = f"REFERENCE_UNRESOLVED:{item['ref_id']}"
            if flag not in auto_flags:
                auto_flags.append(flag)
        if 'REFERENCE_UNRESOLVED' not in failure_hits:
            failure_hits.append('REFERENCE_UNRESOLVED')
        out['promotion_cap_governance'] = 'SANDBOX_ONLY'
    else:
        gsc['reference_resolution_status'] = 'PASSED'

    # Duplicate detection against model and active branch tags.
    tag = (out.get('branch_or_model_tag') or '').strip()
    sym = (out.get('candidate_H_mod_symbolic') or '').strip()
    duplicate_status = 'UNASSESSED'
    duplicate_reference = ''

    known_tags = set()
    for item in registry.get('model_registry', []):
        mt = item.get('model_tag', '').strip()
        if mt:
            known_tags.add(mt)
    for item in registry.get('active_branch_registry', []):
        bt = item.get('branch_or_model_tag', '').strip()
        if bt:
            known_tags.add(bt)

    if tag:
        if tag in known_tags:
            duplicate_status = 'DUPLICATE'
            duplicate_reference = tag
            flag = f'DUPLICATE_BRANCH_TAG:{tag}'
            if flag not in auto_flags:
                auto_flags.append(flag)
            if 'DUPLICATE_BRANCH_TAG' not in failure_hits:
                failure_hits.append('DUPLICATE_BRANCH_TAG')
    elif sym:
        duplicate_status = 'NO_TAG_SYMBOL_ONLY'
    out['registry_duplicate_status'] = duplicate_status
    out['duplicate_reference'] = duplicate_reference

    if 'linked_artifacts' not in out or not isinstance(out['linked_artifacts'], list):
        out['linked_artifacts'] = []
    for art in linked_artifacts:
        if art not in out['linked_artifacts']:
            out['linked_artifacts'].append(art)

    out['evaluation_notes'] = out.get('evaluation_notes', [])
    note = f'M03 reference-resolution executed; report_id={report_id}'
    if note not in out['evaluation_notes']:
        out['evaluation_notes'].append(note)

    # Recompute top-level and nested system_status.
    gsc['system_status'] = derive_system_status(gsc)
    out['system_status'] = gsc['system_status']
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description='Resolve QDP references and optionally patch a candidate JSON object.')
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--registry', required=True, type=Path)
    parser.add_argument('--root', type=Path, default=REPO_ROOT)
    parser.add_argument('--mode', choices=['ordinary', 'subsystem'], default='ordinary')
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--write-report', type=Path)
    parser.add_argument('--write-candidate', type=Path)
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    registry = load_json(args.registry)
    resolved, unresolved = resolve_manifest(manifest, args.root, args.mode)

    critical_unresolved = [u for u in unresolved if u.get('required') and str(u.get('criticality', '')).startswith('CRITICAL')]
    ref_status = 'FAILED' if critical_unresolved else 'PASSED'
    system_status = 'REFERENCE_RESOLUTION_FAILURE' if critical_unresolved else 'HARNESS_REQUIRED'
    promo_cap = 'SANDBOX_ONLY' if critical_unresolved else ''
    auto_flags = [f"REFERENCE_UNRESOLVED:{u['ref_id']}" for u in critical_unresolved]

    report = {
        'artifact_id': 'QDP_V10_6_REFERENCE_RESOLUTION_REPORT_M03',
        'report_id': f"m03-reference-report-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        'module_id': 'M03',
        'mode': args.mode,
        'root': str(args.root),
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'manifest_id': manifest.get('artifact_id', ''),
        'registry_id': registry.get('artifact_id', ''),
        'resolved_count': len(resolved),
        'unresolved_count': len(unresolved),
        'critical_unresolved_count': len(critical_unresolved),
        'reference_resolution_status': ref_status,
        'system_status': system_status,
        'promotion_cap_governance': promo_cap,
        'automatic_flags_triggered': auto_flags,
        'resolved_references': [
            {
                'ref_id': r['ref_id'],
                'relative_path': r['relative_path'],
                'sha256': r['sha256'],
                'bytes': r['bytes']
            }
            for r in resolved
        ],
        'unresolved_references': [
            {
                'ref_id': u['ref_id'],
                'relative_path': u['relative_path'],
                'criticality': u['criticality'],
                'required': u['required'],
                'missing_reason': u['missing_reason']
            }
            for u in unresolved
        ]
    }

    if args.write_report:
        args.write_report.write_text(json.dumps(report, indent=2), encoding='utf-8')

    if args.candidate:
        candidate = load_json(args.candidate)
        linked = [str(args.manifest), str(args.registry)]
        if args.write_report:
            linked.append(str(args.write_report))
        patched = update_candidate(candidate, registry, critical_unresolved, report['report_id'], linked)
        if args.write_candidate:
            args.write_candidate.write_text(json.dumps(patched, indent=2), encoding='utf-8')
        else:
            print(json.dumps(patched, indent=2))
    else:
        print(json.dumps(report, indent=2))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
