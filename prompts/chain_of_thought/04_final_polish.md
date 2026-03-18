# Stage 4: Final Polish and Quality Gate

## Purpose
Review the draft from Stage 3 against all quality constraints. Fix violations. Produce the final output. This stage also outputs a quality score that the batch processor uses to flag pages needing human review.

## Instructions

You have the following draft:

```
{{draft_content}}
```

### Quality Checks to Perform (in order)

#### Check 1: Banned Phrase Scan
Scan the full draft for the following banned phrases and patterns:
{{banned_phrases_formatted}}

For each violation found:
- Note the location (paragraph number, sentence)
- Replace the banned phrase with a specific, technical alternative
- The replacement must NOT introduce a new banned phrase

#### Check 2: Sentence Subject Audit
Identify every sentence that opens with "This", "It", "They", "These", "Those", "Such", "There".

For each:
- Replace the vague pronoun subject with the specific named entity it refers to
- Rewrite the sentence in active voice if it is currently passive

#### Check 3: Semantic Triplet Density
Count sentences that follow Subject-Predicate-Object structure vs. total sentences.
- If the ratio is below 60%, identify the lowest-density paragraph and rewrite it to hit the threshold.

#### Check 4: Reading Level Estimate
Review the draft for passages that read below Grade 8 (too simplistic) or above Grade 14 (too dense).
- Below Grade 8: add one layer of technical specificity to the weakest paragraph
- Above Grade 14: break the longest sentence in the densest paragraph into two

#### Check 5: Unique Perspective Verification
Locate the section containing the counter-intuitive claim: **{{counter_intuitive_claim}}**

Verify:
- The claim is stated directly and specifically, not hedged
- The claim is supported by at least one evidence anchor
- The claim is not softened in the concluding section

#### Check 6: Opening Line Audit
Verify the first sentence:
- Does NOT start with "In", "Are", "Have", "Welcome", "Today", "When it comes to"
- Does NOT pose a rhetorical question
- Does contain a specific fact, claim, or named entity

#### Check 7: Closing Line Audit
Verify the final sentence:
- Does NOT start with "In conclusion", "To summarize", "Overall"
- Does end with a specific directive, a pointed question that demands a concrete answer, or a forward-looking implication of the article's core claim

### Output Format

Return a JSON object followed by the corrected article:

```json
{
  "quality_score": <integer 0-100>,
  "violations_found": [
    {
      "check": "<check name>",
      "location": "<paragraph and sentence description>",
      "original": "<original text>",
      "corrected": "<replacement text>"
    }
  ],
  "word_count": <integer>,
  "semantic_triplet_ratio": <float 0.0-1.0>,
  "estimated_reading_grade": <float>,
  "human_review_required": <boolean>,
  "human_review_reason": "<string, null if not required>"
}
```

Then provide the corrected article in full Markdown.

### Scoring Rubric
- Start at 100
- Deduct 5 per banned phrase violation
- Deduct 3 per vague subject sentence (This/It/They)
- Deduct 10 if semantic triplet ratio < 0.60
- Deduct 8 if opening line violates rules
- Deduct 8 if closing line violates rules
- Deduct 5 if counter-intuitive claim is hedged
- Flag `human_review_required: true` if final score < 70
