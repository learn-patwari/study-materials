"""
evaluate.py
===========
Performance metrics for the Resume RAG system (Assignment 3 deliverable).

Retrieval accuracy (against data/ground_truth.json):
    * Precision@K  — of the top-K matches, how many are truly relevant
    * Recall@K     — of all relevant candidates, how many appear in top-K
    * MRR          — mean reciprocal rank of the first relevant hit
Latency:
    * index build time
    * mean / p95 per-query matching time

Relevance = a candidate whose role matches the job's target role
(see data_gen.py). Must-have filters are applied for each job as well.

Run:  python evaluate.py
"""

from __future__ import annotations

import json
import os
import time
from statistics import mean
from typing import Dict, List

from job_matcher import JobMatcher
from resume_rag import ResumeRAG

HERE = os.path.dirname(os.path.abspath(__file__))
RESUME_DIR = os.path.join(HERE, "data", "resumes")
JOB_DIR = os.path.join(HERE, "data", "jobs")
GROUND_TRUTH = os.path.join(HERE, "data", "ground_truth.json")


def _precision_recall(ranked_ids: List[str], relevant: set, k: int):
    topk = ranked_ids[:k]
    hits = sum(1 for cid in topk if cid in relevant)
    precision = hits / max(1, len(topk))
    recall = hits / max(1, len(relevant))
    rr = 0.0
    for rank, cid in enumerate(ranked_ids, start=1):
        if cid in relevant:
            rr = 1.0 / rank
            break
    return precision, recall, rr


def _cid_from_path(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def evaluate(k: int = 10, prefer_embedder=None) -> Dict:
    with open(GROUND_TRUTH, "r", encoding="utf-8") as fh:
        truth = json.load(fh)

    t0 = time.perf_counter()
    rag = ResumeRAG(prefer_embedder=prefer_embedder)
    stats = rag.build_index(RESUME_DIR)
    build_time = time.perf_counter() - t0
    matcher = JobMatcher(rag)

    per_job, latencies = [], []
    for job_id, meta in truth.items():
        jd = open(os.path.join(JOB_DIR, job_id + ".txt"), encoding="utf-8").read()
        relevant = set(meta["relevant"])

        t1 = time.perf_counter()
        result = matcher.match(jd, k=k, must_have=meta.get("must_have", []))
        latencies.append(time.perf_counter() - t1)

        ranked = [_cid_from_path(m["resume_path"]) for m in result["top_matches"]]
        p, r, rr = _precision_recall(ranked, relevant, k)
        # precision@n where n = number of relevant candidates (fairer when
        # |relevant| < k, since precision@k is then capped at |relevant|/k).
        p_at_rel, _, _ = _precision_recall(ranked, relevant, len(relevant))
        per_job.append({"job": job_id, "precision@k": round(p, 3),
                        "precision@relevant": round(p_at_rel, 3),
                        "recall@k": round(r, 3), "reciprocal_rank": round(rr, 3),
                        "returned": len(ranked), "relevant": len(relevant)})

    latencies.sort()
    p95 = latencies[int(0.95 * (len(latencies) - 1))] if latencies else 0.0
    summary = {
        "config": stats,
        "k": k,
        "retrieval": {
            "precision@k": round(mean(j["precision@k"] for j in per_job), 3),
            "precision@relevant": round(
                mean(j["precision@relevant"] for j in per_job), 3),
            "recall@k": round(mean(j["recall@k"] for j in per_job), 3),
            "MRR": round(mean(j["reciprocal_rank"] for j in per_job), 3),
        },
        "latency_seconds": {
            "index_build": round(build_time, 4),
            "query_mean": round(mean(latencies), 4),
            "query_p95": round(p95, 4),
        },
        "per_job": per_job,
    }
    return summary


def main() -> None:
    summary = evaluate(k=10)
    print(json.dumps(summary, indent=2))
    r = summary["retrieval"]
    print(f"\nSUMMARY  P@10={r['precision@k']}  P@relevant={r['precision@relevant']}  "
          f"recall@10={r['recall@k']}  MRR={r['MRR']}  "
          f"| build={summary['latency_seconds']['index_build']}s  "
          f"query_mean={summary['latency_seconds']['query_mean']}s")


if __name__ == "__main__":
    main()
