#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "mmm_mechanism_registry.yaml",
    "mmm_structure_library.yaml",
    "mmm_material_genome_database.yaml",
    "mmm_candidate_generation_algorithms.yaml",
    "mmm_environment_model_registry.yaml",
    "mmm_benchmark_models.yaml",
    "mmm_scaling_discrimination_models.yaml",
    "mmm_device_architecture_registry.yaml",
    "mmm_material_system_registry.yaml",
    "mmm_experiment_registry.yaml",
    "mmm_instrument_constraints.yaml",
    "mmm_validation_rules.yaml",
    "mmm_cross_device_registry.yaml",
    "mmm_geometry_scaling_models.yaml",
    "mmm_tolerance_models.yaml",
    "registry/mechanisms.yaml",
    "registry/structures.yaml",
    "genome/material_genome_database.yaml",
    "discovery/generation_algorithms.yaml",
    "simulation/environment_models.yaml",
    "benchmark/null_mechanism_models.yaml",
    "scaling/scaling_models.yaml",
    "integration/device_architecture.yaml",
    "fabrication/fabrication_methods.md",
    "experiments/protocols.md",
    "replication/replication_protocols.md",
    "analysis/analysis_pipeline.md",
    "publications/mmm_overview.tex",
]


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def unique(items):
    return len(items) == len(set(items))


def main() -> int:
    errors = []
    warnings = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"Missing required file: {rel}")

    if errors:
        print("MMM VALIDATION REPORT")
        print("=====================")
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    mech = load_yaml(ROOT / "mmm_mechanism_registry.yaml")
    struct = load_yaml(ROOT / "mmm_structure_library.yaml")
    genome = load_yaml(ROOT / "mmm_material_genome_database.yaml")
    bench = load_yaml(ROOT / "mmm_benchmark_models.yaml")
    scale = load_yaml(ROOT / "mmm_scaling_discrimination_models.yaml")
    dev = load_yaml(ROOT / "mmm_device_architecture_registry.yaml")
    exp = load_yaml(ROOT / "mmm_experiment_registry.yaml")
    val = load_yaml(ROOT / "mmm_validation_rules.yaml")
    tol = load_yaml(ROOT / "mmm_tolerance_models.yaml")
    geo = load_yaml(ROOT / "mmm_geometry_scaling_models.yaml")

    observables = exp["observable_registry"]
    protocols = exp["protocols"]
    validations = val["validation_rules"]
    mechanisms = mech["mechanisms"]
    structures = struct["structures"]
    genomes = genome["genomes"]
    benchmark_models = bench["benchmark_models"]
    scaling_models = scale["scaling_models"]
    device_architectures = dev["device_architectures"]
    tolerance_models = tol["tolerance_models"]
    geometry_scaling_models = geo["geometry_scaling_models"]

    observable_ids = [o["observable_id"] for o in observables]
    protocol_ids = [p["protocol_id"] for p in protocols]
    validation_ids = [v["validation_rule_id"] for v in validations]
    mechanism_ids = [m["mechanism_id"] for m in mechanisms]
    structure_ids = [s["structure_id"] for s in structures]
    genome_ids = [g["genome_id"] for g in genomes]
    benchmark_ids = [b["null_model_id"] for b in benchmark_models]
    scaling_ids = [s["scaling_model_id"] for s in scaling_models]

    for name, ids in [
        ("observable_ids", observable_ids),
        ("protocol_ids", protocol_ids),
        ("validation_ids", validation_ids),
        ("mechanism_ids", mechanism_ids),
        ("structure_ids", structure_ids),
        ("genome_ids", genome_ids),
        ("benchmark_ids", benchmark_ids),
        ("scaling_ids", scaling_ids),
    ]:
        if not unique(ids):
            errors.append(f"Duplicate IDs detected in {name}")

    observable_set = set(observable_ids)
    protocol_set = set(protocol_ids)
    validation_set = set(validation_ids)
    mechanism_set = set(mechanism_ids)
    structure_set = set(structure_ids)
    benchmark_set = set(benchmark_ids)

    for m in mechanisms:
        mid = m["mechanism_id"]
        if not m.get("predicted_observable_ids"):
            errors.append(f"{mid}: missing predicted_observable_ids")
        if not m.get("experimental_protocol_ids"):
            errors.append(f"{mid}: missing experimental_protocol_ids")
        if not m.get("validation_rule_ids"):
            errors.append(f"{mid}: missing validation_rule_ids")

        for oid in m.get("predicted_observable_ids", []):
            if oid not in observable_set:
                errors.append(f"{mid}: unresolved observable {oid}")
        for pid in m.get("experimental_protocol_ids", []):
            if pid not in protocol_set:
                errors.append(f"{mid}: unresolved protocol {pid}")
        for vid in m.get("validation_rule_ids", []):
            if vid not in validation_set:
                errors.append(f"{mid}: unresolved validation rule {vid}")
        for bid in m.get("baseline_null_priority", []):
            if bid not in benchmark_set:
                errors.append(f"{mid}: unresolved benchmark null {bid}")
        if m.get("priority_tier") == "A" and m["fabrication_feasibility"].get(
            "exotic_fabrication_flag"
        ):
            warnings.append(f"{mid}: Tier-A mechanism flagged exotic; verify governance intent.")

    for s in structures:
        sid = s["structure_id"]
        for mid in s.get("implements_mechanisms", []):
            if mid not in mechanism_set:
                errors.append(f"{sid}: unresolved mechanism {mid}")
        if s["fabrication_requirements"].get("exotic_flag") and sid in {
            "STR-PH-SOI-JJ-PHC",
            "STR-PH-SOI-FULLCAP-PHC",
            "STR-PH-GRADED-SINK",
        }:
            warnings.append(f"{sid}: lead phononic family marked exotic unexpectedly.")

    for g in genomes:
        gid = g["genome_id"]
        if g["parent_structure_id"] not in structure_set:
            errors.append(f"{gid}: unresolved parent structure {g['parent_structure_id']}")
        if not (1 <= g["fabrication_complexity_score"] <= 10):
            errors.append(f"{gid}: fabrication_complexity_score outside 1-10")
        if not (1 <= g["null_risk_score"] <= 10):
            errors.append(f"{gid}: null_risk_score outside 1-10")

    for sm in scaling_models:
        if sm["mechanism_id"] not in mechanism_set:
            errors.append(f"{sm['scaling_model_id']}: unresolved mechanism {sm['mechanism_id']}")
        for pid in sm.get("required_protocols", []):
            if pid not in protocol_set:
                errors.append(f"{sm['scaling_model_id']}: unresolved protocol {pid}")
        for bid in sm.get("null_comparators", []):
            if bid not in benchmark_set:
                errors.append(f"{sm['scaling_model_id']}: unresolved null comparator {bid}")

    for d in device_architectures:
        for sid in d.get("allowed_structure_ids", []):
            if sid not in structure_set:
                errors.append(f"{d['device_class']}: unresolved structure {sid}")

    tol_structure_set = {t["structure_id"] for t in tolerance_models}
    geo_structure_set = {g["structure_id"] for g in geometry_scaling_models}

    for sid in [
        "STR-EM-CPW-EBG-RING",
        "STR-EM-LID-HIS",
        "STR-PH-SOI-JJ-PHC",
        "STR-PH-GRADED-SINK",
        "STR-VX-ANTIDOT-LATTICE",
        "STR-CTRL-BANDSTOP-INTERPOSER",
    ]:
        if sid not in tol_structure_set:
            warnings.append(f"{sid}: no tolerance model found")
    for sid in [
        "STR-EM-CPW-EBG-RING",
        "STR-PH-SOI-JJ-PHC",
        "STR-PH-GRADED-SINK",
        "STR-VX-ANTIDOT-LATTICE",
    ]:
        if sid not in geo_structure_set:
            warnings.append(f"{sid}: no geometry scaling model found")

    print("MMM VALIDATION REPORT")
    print("=====================")
    print(f"Root: {ROOT}")
    print(f"Required files checked: {len(REQUIRED_FILES)}")
    print(f"Mechanisms: {len(mechanisms)}")
    print(f"Structures: {len(structures)}")
    print(f"Genomes: {len(genomes)}")
    print(f"Protocols: {len(protocols)}")
    print(f"Validation rules: {len(validations)}")
    print(f"Scaling models: {len(scaling_models)}")
    print()

    if warnings:
        print("WARNINGS")
        print("--------")
        for w in warnings:
            print(f"WARNING: {w}")
        print()

    if errors:
        print("FAIL")
        print("----")
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    print("PASS")
    print("----")
    print("All required files exist.")
    print("All critical references resolve.")
    print("Governance links (observable / protocol / validation) are present for every mechanism.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
