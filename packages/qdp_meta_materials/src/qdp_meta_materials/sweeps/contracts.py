from __future__ import annotations

from .models import EquivalenceCluster, EquivalenceEdge, SweepSummary, TrancheSummary


def get_equivalence_edges(summary: object) -> list[EquivalenceEdge]:
    adjudication = getattr(summary, "adjudication", None)
    graph = getattr(adjudication, "equivalence_graph", None)
    graph_edges = _sorted_edges(getattr(graph, "edges", []))
    if graph_edges:
        return graph_edges

    weakest_edges = _sorted_edges(getattr(summary, "weakest_edges", []))
    if weakest_edges:
        return weakest_edges

    clusters = [
        *getattr(summary, "equivalence_clusters", []),
        *getattr(adjudication, "equivalence_clusters", []),
    ]
    legacy_edges = _legacy_edges_from_clusters(clusters)
    if legacy_edges:
        _mark_legacy_contract_downgrade(
            summary,
            "Legacy artifact lacked a persisted equivalence graph; edge topology was reconstructed from cluster-only data with reduced fidelity.",
        )
    return legacy_edges


def load_sweep_summary_payload(payload: dict[str, object]) -> SweepSummary:
    return normalize_loaded_sweep_summary(SweepSummary.model_validate(payload))


def load_tranche_summary_payload(payload: dict[str, object]) -> TrancheSummary:
    summary = TrancheSummary.model_validate(payload)
    if summary.adjudication is None:
        return summary
    return summary.model_copy(
        update={
            "adjudication": summary.adjudication.model_copy(
                update={
                    "measurement_config": summary.adjudication.measurement_config,
                    "measurement_config_provenance": (
                        summary.adjudication.measurement_config_provenance
                    ),
                },
                deep=True,
            )
        },
        deep=True,
    )


def normalize_loaded_sweep_summary(summary: SweepSummary) -> SweepSummary:
    edges = get_equivalence_edges(summary)
    adjudication = summary.adjudication
    clusters = (
        list(adjudication.equivalence_clusters)
        if adjudication.equivalence_clusters
        else list(summary.equivalence_clusters)
    )
    history = (
        list(adjudication.discriminator_history)
        if adjudication.discriminator_history
        else list(summary.discriminator_history)
    )
    return summary.model_copy(
        update={
            "equivalence_clusters": clusters,
            "weakest_edges": edges[:10],
            "discriminator_history": history,
            "legacy_contract_downgrade": getattr(summary, "legacy_contract_downgrade", False),
            "legacy_contract_notes": list(getattr(summary, "legacy_contract_notes", [])),
            "adjudication": adjudication.model_copy(
                update={
                    "equivalence_clusters": clusters,
                    "weakest_unresolved_edges": edges[:10],
                    "discriminator_history": history,
                    "measurement_config": adjudication.measurement_config,
                    "measurement_config_provenance": adjudication.measurement_config_provenance,
                },
                deep=True,
            ),
        },
        deep=True,
    )


def _sorted_edges(edges: object) -> list[EquivalenceEdge]:
    return sorted(
        list(edges or []),
        key=lambda edge: (edge.equivalence_margin, edge.edge_id),
    )


def _mark_legacy_contract_downgrade(summary: object, note: str) -> None:
    try:
        setattr(summary, "legacy_contract_downgrade", True)
        notes = list(getattr(summary, "legacy_contract_notes", []))
        if note not in notes:
            notes.append(note)
        setattr(summary, "legacy_contract_notes", notes)
    except AttributeError:
        return


def _legacy_edges_from_clusters(clusters: list[EquivalenceCluster]) -> list[EquivalenceEdge]:
    edges: list[EquivalenceEdge] = []
    for cluster in sorted(clusters, key=lambda item: item.cluster_id):
        tranche_ids = sorted(cluster.tranche_ids)
        if len(tranche_ids) < 2:
            continue
        slice_ids = sorted(cluster.slice_ids)
        if len(slice_ids) < 2:
            slice_ids = [*slice_ids, *slice_ids]
        left_slice_id = slice_ids[0] if slice_ids else tranche_ids[0]
        right_slice_id = slice_ids[1] if len(slice_ids) > 1 else tranche_ids[1]
        margin = cluster.equivalence_margin or max(
            0.0, 1.0 - cluster.measurement_equivalence_score
        )
        edges.append(
            EquivalenceEdge(
                edge_id=f"legacy::{cluster.cluster_id}::{tranche_ids[0]}::{tranche_ids[1]}",
                left_tranche_id=tranche_ids[0],
                left_slice_id=left_slice_id,
                right_tranche_id=tranche_ids[1],
                right_slice_id=right_slice_id,
                equivalence_margin=margin,
                measurement_equivalence_score=cluster.measurement_equivalence_score,
                tested_axes=["legacy_cluster_only"],
            )
        )
    return _sorted_edges(edges)
