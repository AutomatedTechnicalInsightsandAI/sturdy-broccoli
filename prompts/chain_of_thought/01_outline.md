# Stage 1: Outline Generation

## Purpose
Generate a structured, section-level outline for the content piece. This stage produces the skeleton only — no prose. The outline must reflect the unique data inputs for this specific page, ensuring variation from other pages in the batch.

## Instructions

You are constructing the outline for a **{{page_type}}** targeting the query: **"{{primary_keyword}}"**

Audience: {{target_audience}}
Unique Perspective for this page: {{unique_perspective}}
Niche terminology to anchor: {{niche_terminology}}
Primary failure mode to address: {{failure_mode}}

### Output Format

Return ONLY a JSON object with this structure:

```json
{
  "title": "<H1 title: specific, query-matching, no more than 70 characters>",
  "meta_description": "<155-character meta description: includes primary keyword, states the unique angle>",
  "sections": [
    {
      "id": "<section_id>",
      "heading": "<H2 heading: specific, avoids generic labels>",
      "purpose": "<one sentence: what this section proves or demonstrates>",
      "key_claims": ["<claim 1>", "<claim 2>", "<claim 3>"],
      "anchor_term": "<the primary technical term or data point that grounds this section>",
      "word_target": <integer>
    }
  ],
  "semantic_entities": ["<entity 1>", "<entity 2>", "<entity 3>", "..."],
  "counter_intuitive_claim": "<the specific claim that differentiates this page from SERP competitors>",
  "internal_link_opportunities": ["<related topic 1>", "<related topic 2>"]
}
```

### Rules
- The title must NOT be a question
- Each section heading must be unique — no "Introduction", "Conclusion", "Overview"
- `key_claims` must be falsifiable statements, not descriptions
- `semantic_entities` should list the named entities (people, tools, standards, metrics) that will appear in the content — these feed Google's knowledge graph extraction
- `counter_intuitive_claim` must contradict something that appears on the first SERP page for the primary keyword
