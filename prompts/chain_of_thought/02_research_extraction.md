# Stage 2: Research Extraction and Claim Substantiation

## Purpose
Given the outline from Stage 1, expand each section's `key_claims` into substantiated, specific assertions. This stage produces raw material — dense, factual, technical — that will be shaped into prose in Stage 3. It eliminates vague claims before they enter the final output.

## Instructions

You have the following outline:

```json
{{outline_json}}
```

The following supporting data has been provided for this page:
- **Primary data point:** {{data_point}}
- **Named tool or platform:** {{named_tool}}
- **Authority source:** {{authority_source}}
- **Experience signal:** {{experience_signal}}

### Task

For each section in the outline, produce:

1. **Substantiated Claims** — take each `key_claim` and expand it with:
   - A specific subject (named entity, metric, or mechanism)
   - A specific predicate (active verb with measurable or testable meaning)
   - A specific object (outcome, value, or comparison)

2. **Evidence Anchors** — for each claim, note the evidence type:
   - `[primary_data]` — the provided data point
   - `[named_tool]` — behavior or outcome specific to the named tool
   - `[authority_source]` — referenced standard, study, or specification
   - `[first_principles]` — logical derivation from a stated mechanism
   - `[experience]` — first-person observation from the provided signal

3. **Failure Mode Integration** — in the section addressing `{{failure_mode}}`, include:
   - The specific condition that triggers the failure
   - The measurable consequence
   - The corrective action with its mechanism

### Output Format

Return a JSON object with the following structure:

```json
{
  "substantiated_sections": [
    {
      "section_id": "<matches outline section id>",
      "expanded_claims": [
        {
          "claim": "<Subject + active verb + specific object>",
          "evidence_type": "<evidence anchor tag>",
          "evidence_detail": "<specific supporting detail or calculation>"
        }
      ],
      "failure_mode_block": {
        "trigger": "<condition>",
        "consequence": "<measurable outcome>",
        "correction": "<specific action + mechanism>"
      }
    }
  ]
}
```

### Rules
- Every claim must have a named subject — no "it", "this", or "they"
- Every claim must use an active verb — no "is", "are", "has", "involves", "allows"
- Numeric values are preferred over qualitative descriptors
- The `failure_mode_block` is required only for the section most relevant to {{failure_mode}}; include null for others
