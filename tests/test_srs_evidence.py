"""Quick tests for SRS evidence matrix."""

from mili_vio.validation.srs_evidence import (
    EvidenceLevel,
    evaluate_srs_evidence,
    save_srs_evidence,
)


def test_evidence_matrix_structure() -> None:
    matrix = evaluate_srs_evidence(quick=True, run_measurements=False)
    assert len(matrix.rows) == 10
    ids = {r.metric_id for r in matrix.rows}
    assert "position_error" in ids
    assert "stability" in ids


def test_evidence_not_proven_without_measurements() -> None:
    matrix = evaluate_srs_evidence(run_measurements=False)
    stab = next(r for r in matrix.rows if r.metric_id == "stability")
    assert stab.evidence_level == EvidenceLevel.NOT_PROVEN


def test_evidence_save_yaml(tmp_path) -> None:
    matrix = evaluate_srs_evidence(quick=True, run_measurements=False)
    path = save_srs_evidence(matrix, tmp_path)
    assert path.exists()
    assert "srs_evidence_matrix.yaml" in str(path)
