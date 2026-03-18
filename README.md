# sturdy-broccoli

AI Template for Scalable Pages — a prompt engineering system for generating high-authority, non-generic content at scale.

---

## What This Does

Generic AI content fails because it relies on default model weights with no variable grounding, no constraint enforcement, and no structured differentiation between pages. This system fixes that across hundreds of pages through three mechanisms:

1. **Variable-Driven Specificity** — every page ingests unique data points (niche terminology, local data, audience pain points) through a structured template, so a 100-page batch cannot produce identical output.
2. **Negative Constraint Injection** — a curated blacklist of LLM-isms (`delve`, `leverage`, `in the rapidly evolving landscape`, and 80+ others) is injected into every prompt, with pattern-level detection to catch sentence-level constructions.
3. **Multi-Step Chain-of-Thought Pipeline** — generation is broken into four stages (Outline → Research Extraction → Tone Application → Final Polish), each with a quality gate, so the model cannot lose the thread of authority across long-form content.

---

## Architecture

```
sturdy-broccoli/
├── generator.py                   # CLI entry point
├── requirements.txt
├── config/
│   ├── negative_constraints.json  # Blacklisted phrases, patterns, sentence starters
│   ├── content_structure.json     # Required sections, word targets, variation axes
│   └── seo_config.json            # Search intent types, EEAT signals, long-tail patterns
├── prompts/
│   ├── system_prompt.md           # Technical Consultant persona + hard output rules
│   └── chain_of_thought/
│       ├── 01_outline.md          # Stage 1: Structured outline as JSON
│       ├── 02_research_extraction.md  # Stage 2: Claim substantiation
│       ├── 03_tone_application.md # Stage 3: Prose generation with tone rules
│       └── 04_final_polish.md     # Stage 4: Quality gate + scoring
├── src/
│   ├── prompt_builder.py          # Template rendering + static content validation
│   ├── content_generator.py       # Four-stage CoT pipeline orchestration
│   ├── seo_optimizer.py           # Semantic triplet density, EEAT, intent analysis
│   └── batch_processor.py        # Batch runner with cross-page duplication detection
├── tests/
│   ├── conftest.py
│   ├── test_prompt_builder.py
│   ├── test_content_generator.py
│   ├── test_seo_optimizer.py
│   └── test_batch_processor.py
└── examples/
    ├── postgresql_autovacuum_post.json  # Single-page example
    └── batch_pages.json                 # Three-page batch example
```

---

## Page Data Schema

Every page requires the following fields. These are the **variation axes** — the data points that prevent batch duplication.

| Field | Description | Example |
|---|---|---|
| `topic` | The specific subject of this page | `"PostgreSQL autovacuum tuning for high-write OLTP workloads"` |
| `target_audience` | Named, specific audience segment | `"senior PostgreSQL DBAs"` |
| `search_intent_type` | `informational` \| `navigational` \| `transactional` \| `commercial_investigation` | `"informational"` |
| `primary_keyword` | The long-tail query this page targets | `"postgresql autovacuum tuning high-write"` |
| `secondary_keywords` | Comma-separated supporting terms | `"dead tuples, table bloat, vacuum_cost_delay"` |
| `niche` | The domain or industry | `"PostgreSQL database engineering"` |
| `niche_terminology` | Domain-specific terms to use and define | `"MVCC, dead tuples, heap bloat"` |
| `unique_perspective` | The counter-intuitive claim that differentiates this page from SERP competitors | `"The bottleneck is cost_delay, not scale_factor"` |
| `data_point` | A specific, measurable data point to anchor the content | `"5,000 writes/s with 2ms delay → 40GB bloat in 24h"` |
| `named_tool` | A specific tool or platform to reference | `"pg_stat_user_tables"` |
| `failure_mode` | What the target audience typically does wrong | `"Reduces scale_factor without adjusting cost_delay"` |
| `depth_level` | `shallow` \| `medium` \| `deep` | `"deep"` |
| `experience_signal` | First-person observation or measurement to embed | `"Measured on Citus cluster at 4,800 writes/s"` |
| `primary_technical_term` | The term to define and anchor expertise around | `"MVCC"` |
| `authority_source` | A named standard, study, or specification to cite | `"PostgreSQL 16 documentation, Section 25.1"` |
| `page_type` | `blog_post` \| `landing_page` | `"blog_post"` |
| `tone_register` | `technical-peer` \| `practitioner-guide` \| `executive-briefing` | `"technical-peer"` |

---

## Usage

### Prerequisites

```bash
pip install -r requirements.txt
pip install openai   # required for LLM calls; omit for dry-run
```

### Single Page — Dry Run (no LLM call, inspect assembled prompts)

```bash
python generator.py generate \
  --page-data examples/postgresql_autovacuum_post.json \
  --dry-run
```

### Single Page — Full Generation

```bash
python generator.py generate \
  --page-data examples/postgresql_autovacuum_post.json \
  --output output/postgresql_autovacuum.md \
  --openai-key $OPENAI_API_KEY \
  --model gpt-4o
```

### Batch Generation

```bash
python generator.py batch \
  --pages-file examples/batch_pages.json \
  --output-dir output/ \
  --openai-key $OPENAI_API_KEY
```

Output files are written to `output/` as `{topic-slug}.md`. A `batch_summary.json` is produced with quality scores, review flags, and duplication analysis.

### Validate an Existing File

```bash
python generator.py validate \
  --content-file output/postgresql_autovacuum.md \
  --page-data examples/postgresql_autovacuum_post.json
```

### SEO Analysis

```bash
python generator.py seo-analyze \
  --content-file output/postgresql_autovacuum.md \
  --page-data examples/postgresql_autovacuum_post.json
```

---

## Quality Gates

### Stage 4 Quality Score (0–100)

Each generated page receives a quality score. Pages scoring below 70 are flagged `human_review_required: true`.

| Deduction | Condition |
|---|---|
| −5 per violation | Banned phrase present |
| −3 per sentence | Vague subject (This/It/They) |
| −10 | Semantic triplet ratio < 60% |
| −8 | Opening line violates strict no-intro rule |
| −8 | Closing line is a summary or restatement |
| −5 | Counter-intuitive claim is hedged |

### SEO Score (0–100)

Separately from the LLM quality gate, the `SEOOptimizer` runs static analysis:

| Deduction | Condition |
|---|---|
| −20 | Primary keyword not present |
| −15 | Search intent signals absent |
| up to −20 | Semantic triplet density below 60% |
| −8 per signal | Missing EEAT signal (experience, expertise, authority, trust) |
| −15 | Word count below depth-level minimum |

### Batch Duplication Detection

The `BatchProcessor` fingerprints 6-gram phrases across all generated pages. Any phrase appearing on more than 10% of batch pages is flagged in `batch_summary.json`. This catches prompt-level repetition that survives the per-page quality gate.

---

## Customisation

### Add New Banned Phrases

Edit `config/negative_constraints.json` — add entries to `blacklisted_phrases`, `blacklisted_patterns`, or `blacklisted_sentence_starters`.

### Add a New Page Type

Edit `config/content_structure.json` — add a new key under `page_types` following the existing `blog_post` or `landing_page` structure. Define `required_sections`, `total_word_range`, and `variation_axes`.

### Swap the LLM Backend

Implement the `LLMClient` protocol (a single `complete(prompt, *, system_prompt)` method) and pass your implementation to `ContentGenerator` or `BatchProcessor`. The system is backend-agnostic.

```python
from src.content_generator import ContentGenerator

class MyAnthropicClient:
    def complete(self, prompt: str, *, system_prompt: str = "") -> str:
        # your Anthropic/Bedrock/Azure call here
        ...

generator = ContentGenerator(MyAnthropicClient())
result = generator.generate(page_data)
```

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

All tests use a mock LLM client and run without an API key.
