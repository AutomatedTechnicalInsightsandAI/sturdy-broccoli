"""Shared test fixtures for the sturdy-broccoli test suite."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Minimal page_data fixture used across test modules
# ---------------------------------------------------------------------------

SAMPLE_PAGE_DATA: dict[str, Any] = {
    "topic": "PostgreSQL autovacuum tuning for high-write OLTP workloads",
    "target_audience": "senior database engineers and PostgreSQL DBAs",
    "search_intent_type": "informational",
    "primary_keyword": "postgresql autovacuum tuning high-write",
    "secondary_keywords": "dead tuples, table bloat, vacuum_cost_delay",
    "niche": "PostgreSQL database engineering",
    "niche_terminology": "MVCC, dead tuples, heap bloat, autovacuum workers, cost-based vacuuming",
    "unique_perspective": (
        "Most autovacuum guides recommend lowering autovacuum_vacuum_scale_factor, "
        "but on high-write tables this is the wrong lever — the bottleneck is "
        "autovacuum_vacuum_cost_delay, not trigger threshold."
    ),
    "data_point": (
        "A table receiving 5,000 writes/second with default cost_delay=2ms will "
        "complete a vacuum cycle 8× slower than one configured at 0ms, "
        "generating 40GB+ of bloat within 24 hours under sustained load."
    ),
    "named_tool": "pg_stat_user_tables",
    "failure_mode": (
        "DBAs reduce autovacuum_vacuum_scale_factor without adjusting cost parameters, "
        "triggering more frequent but equally throttled vacuum cycles that fail to "
        "keep pace with write throughput."
    ),
    "depth_level": "deep",
    "experience_signal": (
        "Measured on a Citus cluster processing 4,800 writes/s where default "
        "autovacuum settings produced 60GB heap bloat in under 12 hours"
    ),
    "primary_technical_term": "MVCC",
    "authority_source": "PostgreSQL 16 documentation, Section 25.1",
    "page_type": "blog_post",
    "tone_register": "technical-peer",
}


@pytest.fixture
def sample_page_data() -> dict[str, Any]:
    return dict(SAMPLE_PAGE_DATA)


# ---------------------------------------------------------------------------
# Mock LLM client
# ---------------------------------------------------------------------------


class MockLLMClient:
    """
    Deterministic LLM client for testing.  Returns pre-canned responses
    that satisfy the JSON parsing expectations of each pipeline stage.
    """

    OUTLINE_RESPONSE = json.dumps(
        {
            "title": "PostgreSQL Autovacuum Tuning: The Cost-Delay Bottleneck on High-Write Tables",
            "meta_description": (
                "Most guides target autovacuum scale factor. "
                "The real bottleneck on high-write PostgreSQL tables is cost_delay. "
                "Here's how to measure and fix it."
            ),
            "sections": [
                {
                    "id": "cost_delay_problem",
                    "heading": "Why autovacuum_vacuum_cost_delay Is the Real Bottleneck",
                    "purpose": "Demonstrate that cost throttling prevents vacuum from keeping pace with write throughput",
                    "key_claims": [
                        "autovacuum_vacuum_cost_delay throttles I/O between vacuum page reads",
                        "Default 2ms delay limits vacuum throughput to ~200MB/s on NVMe storage",
                        "Scale factor adjustments trigger more cycles without increasing per-cycle throughput",
                    ],
                    "anchor_term": "vacuum_cost_delay",
                    "word_target": 300,
                }
            ],
            "semantic_entities": [
                "MVCC",
                "dead tuples",
                "heap bloat",
                "autovacuum workers",
                "pg_stat_user_tables",
                "PostgreSQL 16",
            ],
            "counter_intuitive_claim": (
                "Reducing autovacuum_vacuum_scale_factor on high-write tables "
                "worsens bloat accumulation by triggering cost-throttled cycles "
                "faster than they can complete."
            ),
            "internal_link_opportunities": [
                "PostgreSQL MVCC internals",
                "pg_stat_user_tables monitoring guide",
            ],
        }
    )

    RESEARCH_RESPONSE = json.dumps(
        {
            "substantiated_sections": [
                {
                    "section_id": "cost_delay_problem",
                    "expanded_claims": [
                        {
                            "claim": "autovacuum_vacuum_cost_delay introduces a 2ms sleep between each vacuum_cost_page_hit accumulation cycle.",
                            "evidence_type": "[authority_source]",
                            "evidence_detail": "PostgreSQL 16 documentation, Section 25.1, Table 25.1",
                        }
                    ],
                    "failure_mode_block": {
                        "trigger": "DBA reduces autovacuum_vacuum_scale_factor without adjusting vacuum_cost_delay",
                        "consequence": "Autovacuum triggers more frequently but each cycle completes at the same throttled rate, failing to reclaim dead tuples faster than they accumulate",
                        "correction": "Set autovacuum_vacuum_cost_delay=0 on high-write tables using per-table storage parameters via ALTER TABLE",
                    },
                }
            ]
        }
    )

    DRAFT = """## Why autovacuum_vacuum_cost_delay Is the Real Bottleneck

PostgreSQL's autovacuum daemon throttles its own I/O using a cost-based delay mechanism. The `autovacuum_vacuum_cost_delay` parameter introduces a sleep between each vacuum page operation cycle. At the default value of 2ms, autovacuum on NVMe storage reads roughly 200 pages per second — far below what a high-write table produces in dead tuples.

`pg_stat_user_tables` exposes `n_dead_tup` and `last_autovacuum` timestamps. A table receiving 5,000 writes per second with default cost_delay=2ms will accumulate dead tuples at a rate that autovacuum cannot clear within a reasonable cycle window.

## The Scale Factor Mistake

Reducing `autovacuum_vacuum_scale_factor` from 0.2 to 0.01 triggers vacuum more frequently. Each triggered cycle runs under the same I/O throttle. The per-cycle reclaim rate does not increase. The net effect is more frequent, equally slow vacuum runs that create additional lock contention without eliminating bloat accumulation.

## Configuring Per-Table Cost Parameters

PostgreSQL 16 supports per-table autovacuum parameters via storage options. Apply them without touching the global configuration:

```sql
ALTER TABLE orders SET (
  autovacuum_vacuum_cost_delay = 0,
  autovacuum_vacuum_cost_limit = 800
);
```

Measure the impact using `pg_stat_user_tables` before and after: track `n_dead_tup` over a 30-minute window under production load. A correctly tuned table will show `n_dead_tup` stabilising below 10% of `n_live_tup`.
"""

    POLISH_RESPONSE = (
        """```json
{
  "quality_score": 88,
  "violations_found": [],
  "word_count": 210,
  "semantic_triplet_ratio": 0.72,
  "estimated_reading_grade": 11.4,
  "human_review_required": false,
  "human_review_reason": null
}
```

"""
        + DRAFT
    )

    def complete(self, prompt: str, *, system_prompt: str = "") -> str:
        # Use unique title strings from each stage template to dispatch correctly.
        # Order matters: check more specific (later) stages before earlier ones
        # to avoid false matches on back-references (e.g. stage 4 mentions "Stage 3").
        if "Final Polish and Quality Gate" in prompt:
            return self.POLISH_RESPONSE
        if "Tone Application and Prose Generation" in prompt:
            return self.DRAFT
        if "Research Extraction and Claim Substantiation" in prompt:
            return self.RESEARCH_RESPONSE
        # Stage 1 / Outline (default fallback)
        return self.OUTLINE_RESPONSE


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    return MockLLMClient()
