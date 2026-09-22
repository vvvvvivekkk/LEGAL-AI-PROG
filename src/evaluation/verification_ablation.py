"""Phase-6 ablation over the verification chain: V1-V6 each on/off.

Generation is the expensive part of the pipeline (a real LLM call per query,
plus resamples for V4); verification is cheap and local (NLI). So the sweep is
split in two:

1. `build_cache()` runs retrieval + one citation-forced generation per eval
   query with the real LLM, plus a fixed number of V4 resamples for a subset
   of queries, and writes everything to a JSON cache.
2. `run_sweep()` replays the verification chain over that cache once per
   ablation arm, with the corresponding layer disabled via VCSConfig's
   enable_v1..enable_v6 switches. No further LLM calls happen.

Metrics per arm
---------------
mean_vcs            mean answer-level VCS over queries that produced a score
n_answer/n_abstain  the arm's decisions over the query set
bad_claims_surfaced the hallucination/error proxy: claims the FULL chain
                    rejects outright (fabricated citation, or the cited source
                    CONTRADICTS the claim) that this arm would still show the
                    user, i.e. that sit inside an answer the arm decides to
                    ANSWER. The full chain is the reference for "bad", so this
                    is comparable across arms.
abstention_accuracy fraction of queries where the arm's decision matches
                    whether the labelled gold chunk(s) for that query were
                    actually in the retrieved context (retrieved -> should
                    ANSWER, not retrieved -> should ABSTAIN).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.generation.generator import Answer, generate, parse_answer
from src.verification.chain import verify_answer
from src.verification.nli import NLIModel
from src.verification.v5_vcs import ANSWER, VCSConfig

# Ablation arms: name -> the VCSConfig kwargs that define "off" for that layer.
ARMS: dict[str, dict] = {
    "full_chain": {},
    "minus_v1": {"enable_v1": False},
    "minus_v2": {"enable_v2": False},
    "minus_v3": {"enable_v3": False},
    "minus_v4": {"enable_v4": False},
    "minus_v5": {"enable_v5": False},
    "minus_v6": {"enable_v6": False},
}


@dataclass
class CachedGeneration:
    query: str
    raw_text: str
    claims: list[dict]
    context_chunk_ids: list[str]
    context_chunks: list[dict]
    abstained: bool
    resample_texts: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "raw_text": self.raw_text,
            "claims": self.claims,
            "context_chunk_ids": list(self.context_chunk_ids),
            "context_chunks": self.context_chunks,
            "abstained": self.abstained,
            "resample_texts": list(self.resample_texts),
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CachedGeneration":
        return cls(
            query=d["query"],
            raw_text=d["raw_text"],
            claims=d.get("claims", []),
            context_chunk_ids=d.get("context_chunk_ids", []),
            context_chunks=d.get("context_chunks", []),
            abstained=d.get("abstained", False),
            resample_texts=d.get("resample_texts", []),
            error=d.get("error"),
        )

    @property
    def available(self) -> bool:
        return self.error is None

    def answer(self) -> Answer:
        return parse_answer(self.query, self.raw_text, self.context_chunks)

    def resamples(self) -> list[Answer]:
        return [
            parse_answer(self.query, t, self.context_chunks) for t in self.resample_texts
        ]


def build_cache(
    queries: list[str],
    retriever,
    adapter,
    resample_queries: list[str] | None = None,
    n_resamples: int = 2,
    pause_s: float = 2.0,
) -> list[CachedGeneration]:
    """Retrieve + generate once per query (plus V4 resamples for a subset).

    A query whose generation fails (quota, provider outage) is recorded with
    `error` set rather than dropped, so the sweep can report it as unavailable.
    """
    resample_queries = resample_queries or []
    cache: list[CachedGeneration] = []
    for q in queries:
        context = retriever.retrieve(q)
        try:
            ans = generate(q, context, adapter)
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            cache.append(
                CachedGeneration(
                    query=q, raw_text="", claims=[], context_chunk_ids=[],
                    context_chunks=context, abstained=False,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue

        resample_texts: list[str] = []
        if q in resample_queries and not ans.abstained:
            for _ in range(n_resamples):
                time.sleep(pause_s)
                try:
                    resample_texts.append(generate(q, context, adapter).raw_text)
                except Exception:  # noqa: BLE001 - a missing resample just lowers n
                    break

        cache.append(
            CachedGeneration(
                query=q,
                raw_text=ans.raw_text,
                claims=[c.to_dict() for c in ans.claims],
                context_chunk_ids=list(ans.context_chunk_ids),
                context_chunks=context,
                abstained=ans.abstained,
                resample_texts=resample_texts,
            )
        )
        time.sleep(pause_s)
    return cache


def save_cache(cache: list[CachedGeneration], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps([c.to_dict() for c in cache], indent=2), encoding="utf-8"
    )


def load_cache(path: str | Path) -> list[CachedGeneration]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [CachedGeneration.from_dict(d) for d in raw]


def _bad_claim_indices(vcs_result) -> set[int]:
    """Claim positions the chain rejects outright (a hard gate fired)."""
    return {i for i, c in enumerate(vcs_result.per_claim) if c.gate_failed}


def _weak_claim_indices(vcs_result, threshold: float) -> set[int]:
    """Claim positions the chain scores below the abstention threshold.

    Softer than a hard gate: the cited source doesn't entail the claim well
    enough to clear the bar, even though nothing was fabricated outright.
    """
    return {i for i, c in enumerate(vcs_result.per_claim) if c.vcs < threshold}


# --- Perturbation probe ----------------------------------------------------
#
# The eval query set is clean: the model cites real chunks and the sources
# support it, so no hard gate ever fires and the arms are indistinguishable on
# the error proxy. To measure what each layer actually *catches*, the cached
# answers are deterministically corrupted in ways the layers are designed to
# detect. Nothing here is generated or invented — every perturbation is a
# mechanical edit of a real cached answer, and the corrupted claim is bad by
# construction, so "surfaced" = the chain failed to catch a known-bad claim.

FABRICATED_SUFFIX = "::s99:z"

PERTURBATIONS = ("fabricated_citation", "mismatched_claim")


def perturb_cache(cache: list[CachedGeneration], mode: str) -> list[CachedGeneration]:
    """Corrupt every claim of every cached answer in one specific way.

    fabricated_citation  every citation is rewritten to a chunk id that was
                         never retrieved  -> V1 should catch it
    mismatched_claim     the claim text is swapped for a real claim from a
                         different query, keeping this query's citation, so
                         the cited source no longer supports the sentence
                         -> V2/V3 should catch it
    """
    if mode not in PERTURBATIONS:
        raise ValueError(f"unknown perturbation {mode!r}; expected one of {PERTURBATIONS}")

    available = [c for c in cache if c.available and c.claims]
    out: list[CachedGeneration] = []
    for idx, item in enumerate(cache):
        if not item.available or not item.claims:
            out.append(item)
            continue

        if mode == "fabricated_citation":
            claims = [
                {
                    "text": c["text"],
                    "cited_chunk_ids": [
                        cid.split("::")[0] + FABRICATED_SUFFIX
                        for cid in c["cited_chunk_ids"]
                    ],
                }
                for c in item.claims
            ]
        else:
            donor = available[(available.index(item) + 1) % len(available)]
            donor_claims = donor.claims
            claims = [
                {
                    "text": donor_claims[i % len(donor_claims)]["text"],
                    "cited_chunk_ids": list(c["cited_chunk_ids"]),
                }
                for i, c in enumerate(item.claims)
            ]

        raw_text = "\n".join(
            f"{c['text']} " + "".join(f"[{cid}]" for cid in c["cited_chunk_ids"])
            for c in claims
        )
        out.append(
            CachedGeneration(
                query=item.query,
                raw_text=raw_text,
                claims=claims,
                context_chunk_ids=list(item.context_chunk_ids),
                context_chunks=item.context_chunks,
                abstained=False,
                resample_texts=[],  # resamples no longer correspond to this text
            )
        )
    return out


def run_probe(cache: list[CachedGeneration], nli: NLIModel, mode: str) -> dict[str, dict]:
    """Run every arm over a perturbed cache where all claims are bad by design."""
    perturbed = perturb_cache(cache, mode)
    results: dict[str, dict] = {}
    for arm in ARMS:
        config = VCSConfig(**ARMS[arm])
        n_claims = n_surfaced = n_answer = n_abstain = 0
        gate_counts = {"citation": 0, "contradiction": 0}
        vcs_values: list[float] = []
        for item in perturbed:
            if not item.available or not item.claims:
                continue
            answer = item.answer()
            result = verify_answer(answer, item.context_chunks, nli, config=config)
            vr = result.vcs_result
            n_claims += len(answer.claims)
            if vr.decision == ANSWER:
                n_answer += 1
                n_surfaced += len(answer.claims)
            else:
                n_abstain += 1
            if vr.vcs is not None:
                vcs_values.append(vr.vcs)
            for c in vr.per_claim:
                if c.gate_failed in gate_counts:
                    gate_counts[c.gate_failed] += 1
        results[arm] = {
            "arm": arm,
            "perturbation": mode,
            "mean_vcs": (sum(vcs_values) / len(vcs_values)) if vcs_values else None,
            "n_answer": n_answer,
            "n_abstain": n_abstain,
            "bad_claims_total": n_claims,
            "bad_claims_surfaced": n_surfaced,
            "bad_claims_caught": n_claims - n_surfaced,
            "catch_rate": (n_claims - n_surfaced) / n_claims if n_claims else None,
            "gate_failures": gate_counts,
        }
    return results


def run_arm(
    arm: str,
    cache: list[CachedGeneration],
    nli: NLIModel,
    reference_bad: dict[str, set[int]] | None = None,
    gold: dict[str, list[str]] | None = None,
    reference_weak: dict[str, set[int]] | None = None,
) -> dict:
    """Replay the verification chain over the cache with one layer disabled."""
    config = VCSConfig(**ARMS[arm])
    per_query: list[dict] = []
    vcs_values: list[float] = []
    n_answer = n_abstain = 0
    bad_surfaced = 0
    weak_surfaced = 0
    n_correct_decisions = 0
    n_scored_queries = 0
    total_claims = 0
    gate_counts = {"citation": 0, "contradiction": 0}

    for item in cache:
        if not item.available:
            per_query.append({"query": item.query, "error": item.error})
            continue

        answer = item.answer()
        result = verify_answer(
            answer,
            item.context_chunks,
            nli,
            resamples=item.resamples() or None,
            config=config,
        )
        vcs_result = result.vcs_result
        decision = vcs_result.decision
        if decision == ANSWER:
            n_answer += 1
        else:
            n_abstain += 1
        if vcs_result.vcs is not None:
            vcs_values.append(vcs_result.vcs)
        total_claims += len(answer.claims)
        for c in vcs_result.per_claim:
            if c.gate_failed in gate_counts:
                gate_counts[c.gate_failed] += 1

        bad = (
            reference_bad.get(item.query, set())
            if reference_bad is not None
            else _bad_claim_indices(vcs_result)
        )
        surfaced = len(bad) if decision == ANSWER else 0
        bad_surfaced += surfaced

        weak = (
            reference_weak.get(item.query, set())
            if reference_weak is not None
            else _weak_claim_indices(vcs_result, config.threshold)
        )
        weak_here = len(weak) if decision == ANSWER else 0
        weak_surfaced += weak_here

        expected = None
        if gold is not None and item.query in gold:
            n_scored_queries += 1
            retrieved = set(item.context_chunk_ids)
            expected = ANSWER if (set(gold[item.query]) & retrieved) else "ABSTAIN"
            if expected == decision:
                n_correct_decisions += 1

        per_query.append(
            {
                "query": item.query,
                "decision": decision,
                "vcs": vcs_result.vcs,
                "n_claims": len(answer.claims),
                "bad_claims_full_chain": sorted(bad),
                "bad_claims_surfaced": surfaced,
                "weak_claims_full_chain": sorted(weak),
                "weak_claims_surfaced": weak_here,
                "expected_decision": expected,
                "proof_emitted": result.proof is not None,
                "n_resamples": len(item.resample_texts),
            }
        )

    return {
        "arm": arm,
        "config": {
            "enable_v1": config.enable_v1,
            "enable_v2": config.enable_v2,
            "enable_v3": config.enable_v3,
            "enable_v4": config.enable_v4,
            "enable_v5": config.enable_v5,
            "enable_v6": config.enable_v6,
            "threshold": config.threshold,
            "w_entail": config.w_entail,
            "w_fidelity": config.w_fidelity,
            "w_consistency": config.w_consistency,
        },
        "mean_vcs": (sum(vcs_values) / len(vcs_values)) if vcs_values else None,
        "n_queries": len(cache),
        "n_unavailable": sum(1 for c in cache if not c.available),
        "n_answer": n_answer,
        "n_abstain": n_abstain,
        "total_claims": total_claims,
        "bad_claims_surfaced": bad_surfaced,
        "weak_claims_surfaced": weak_surfaced,
        "gate_failures": gate_counts,
        "abstention_accuracy": (
            n_correct_decisions / n_scored_queries if n_scored_queries else None
        ),
        "per_query": per_query,
    }


def run_sweep(
    cache: list[CachedGeneration],
    nli: NLIModel,
    gold: dict[str, list[str]] | None = None,
    arms: list[str] | None = None,
) -> dict[str, dict]:
    """Run every arm, using the full chain's verdicts as the "bad claim" oracle."""
    arms = arms or list(ARMS)
    baseline = run_arm("full_chain", cache, nli, reference_bad=None, gold=gold)
    reference_bad = {
        q["query"]: set(q.get("bad_claims_full_chain", []))
        for q in baseline["per_query"]
        if "error" not in q
    }
    reference_weak = {
        q["query"]: set(q.get("weak_claims_full_chain", []))
        for q in baseline["per_query"]
        if "error" not in q
    }
    # Recompute the baseline row against its own reference so every row uses
    # the same definition of "bad" / "weak" claim.
    results = {
        "full_chain": run_arm("full_chain", cache, nli, reference_bad, gold, reference_weak)
    }
    for arm in arms:
        if arm == "full_chain":
            continue
        results[arm] = run_arm(arm, cache, nli, reference_bad, gold, reference_weak)
    return results
