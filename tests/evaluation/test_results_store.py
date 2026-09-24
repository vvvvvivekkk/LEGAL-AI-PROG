

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


def test_describe_run_gives_each_kind_of_run_its_own_headline_numbers():
    """Only retrieval runs have P/R/F1; the others must still say what they measured."""
    from src.evaluation.results_store import describe_run

    retrieval = describe_run(
        "sweep/sac-dense-rerank", {"chunking": "sac", "mode": "dense"}, {"aggregate": {"f1": 0.417}}
    )
    assert retrieval["kind"] == "retrieval" and "SAC" in retrieval["about"]

    probes = {"fabricated_citation": {"bad_claims_total": 14, "bad_claims_surfaced": 14},
              "mismatched_claim": {"bad_claims_total": 14, "bad_claims_surfaced": 14}}
    arm = describe_run("v/minus_v5", {}, {"arm": "minus_v5", "mean_vcs": 0.7675,
                                          "n_answer": 10, "n_abstain": 0, "probes": probes})
    assert arm["kind"] == "verification_arm"
    values = {h["label"]: h["value"] for h in arm["highlights"]}
    # rounds half-up like the paper's tables, not to 0.767
    assert values == {"Mean VCS": "0.768", "Answered / refused": "10 / 0", "Bad claims shown": "28 / 28"}

    safety = describe_run("lc/safety/python", {"pipeline": "python"},
                          {"mean_vcs": 0.7675, "n_answer": 7, "n_abstain": 3,
                           "surfaced_total": 0, "bad_total": 28})
    assert safety["kind"] == "safety"
    assert {"label": "Bad claims shown", "value": "0 / 28"} in safety["highlights"]


def test_describe_run_never_raises_on_an_unrecognised_or_malformed_file():
    from src.evaluation.results_store import describe_run

    assert describe_run("x", {}, {"whatever": 1}) == {"kind": "other", "about": "", "highlights": []}
    # a known shape with broken values still must not take the page down
    out = describe_run("x", {}, {"summary": {"python": {"mean_s": "?"}, "langchain": {}}})
    assert out["kind"] == "latency"
