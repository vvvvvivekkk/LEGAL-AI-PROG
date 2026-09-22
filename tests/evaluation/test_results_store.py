

def test_load_runs_finds_sweep_arms_nested_in_a_run_directory(tmp_path):
    """A sweep groups its arms in subdirectories; the Evaluation page must see them."""
    import json

    from src.evaluation.results_store import load_runs

    sweep = tmp_path / "2026-09-23-ablations" / "retrieval" / "sac-dense-rerank"
    sweep.mkdir(parents=True)
    (sweep / "config.json").write_text(json.dumps({"mode": "dense"}), encoding="utf-8")
    (sweep / "results.json").write_text(json.dumps({"aggregate": {"f1": 0.417}}), encoding="utf-8")

    flat = tmp_path / "2026-09-20-plain-run"
    flat.mkdir()
    (flat / "results.json").write_text(json.dumps({"ok": True}), encoding="utf-8")

    runs = {r["name"]: r for r in load_runs(tmp_path)}
    assert "2026-09-20-plain-run" in runs
    assert "2026-09-23-ablations/retrieval/sac-dense-rerank" in runs
    assert runs["2026-09-23-ablations/retrieval/sac-dense-rerank"]["config"]["mode"] == "dense"
    # The grouping directories carry no run files of their own, so they are not runs.
    assert "2026-09-23-ablations" not in runs
    assert "2026-09-23-ablations/retrieval" not in runs


def test_load_runs_keeps_a_sweep_summary_alongside_its_arms(tmp_path):
    """The verification sweep writes its own results.json next to per-arm dirs."""
    import json

    from src.evaluation.results_store import load_runs

    sweep = tmp_path / "2026-09-23-ablations" / "verification"
    (sweep / "full_chain").mkdir(parents=True)
    (sweep / "results.json").write_text(json.dumps({"arms": {}}), encoding="utf-8")
    (sweep / "full_chain" / "results.json").write_text(
        json.dumps({"mean_vcs": 0.7675}), encoding="utf-8"
    )

    names = {r["name"] for r in load_runs(tmp_path)}
    assert "2026-09-23-ablations/verification" in names
    assert "2026-09-23-ablations/verification/full_chain" in names
