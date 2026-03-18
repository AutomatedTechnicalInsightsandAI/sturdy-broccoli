#!/usr/bin/env python3
"""
generator.py — CLI entry point for the sturdy-broccoli content engine.

Usage examples
--------------
Single page (dry-run, no LLM call, prints assembled prompts only):

    python generator.py generate --page-data examples/solar_panel_post.json --dry-run

Batch run from a JSON array file:

    python generator.py batch --pages-file examples/batch_pages.json \\
        --output-dir output/ \\
        --openai-key $OPENAI_API_KEY

Validate an already-generated Markdown file:

    python generator.py validate \\
        --content-file output/solar_panel_post.md \\
        --page-data examples/solar_panel_post.json

SEO analyse an existing file:

    python generator.py seo-analyze \\
        --content-file output/solar_panel_post.md \\
        --page-data examples/solar_panel_post.json
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("generator")

# ---------------------------------------------------------------------------
# Inline minimal OpenAI client so the CLI works out-of-the-box without
# requiring users to wire up a separate integration.  For production use,
# replace or extend this with any LLMClient-conformant implementation.
# ---------------------------------------------------------------------------


class OpenAIClient:
    """
    Thin wrapper around the OpenAI ChatCompletion API.

    Requires ``openai`` package (``pip install openai``).
    """

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        try:
            import openai  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for LLM calls. "
                "Install it with: pip install openai"
            ) from exc
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def complete(self, prompt: str, *, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.4,
        )
        return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# CLI command implementations
# ---------------------------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> int:
    page_data = _load_json(args.page_data)

    from src.prompt_builder import PromptBuilder  # noqa: PLC0415

    builder = PromptBuilder()

    if args.dry_run:
        print("=== SYSTEM PROMPT ===\n")
        print(builder.build_system_prompt(page_data))
        print("\n\n=== CHAIN-OF-THOUGHT PROMPTS ===\n")
        cot = builder.build_chain_of_thought_prompts(page_data)
        for stage, prompt in cot.items():
            print(f"\n--- Stage: {stage} ---\n")
            print(prompt)
        return 0

    client = _build_llm_client(args)
    from src.content_generator import ContentGenerator  # noqa: PLC0415

    generator = ContentGenerator(client)
    result = generator.generate(page_data)

    output_path = _resolve_output_path(args, page_data)
    output_path.write_text(result.final_content, encoding="utf-8")
    logger.info("Content written to: %s", output_path)

    _print_result_summary(result)
    return 0 if result.quality_score >= 70 else 1


def cmd_batch(args: argparse.Namespace) -> int:
    pages = _load_json(args.pages_file)
    if not isinstance(pages, list):
        logger.error("--pages-file must contain a JSON array")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = _build_llm_client(args)
    from src.batch_processor import BatchProcessor  # noqa: PLC0415

    processor = BatchProcessor(client)

    try:
        processor.enforce_variation(pages)
    except ValueError as exc:
        logger.error("Variation check failed: %s", exc)
        return 1

    batch = processor.process_batch(pages)

    for idx, result in enumerate(batch.results):
        topic_slug = _slugify(result.page_data.get("topic", f"page_{idx}"))
        out_file = output_dir / f"{topic_slug}.md"
        out_file.write_text(result.final_content, encoding="utf-8")
        logger.info("Written: %s (quality=%d)", out_file, result.quality_score)

    summary_file = output_dir / "batch_summary.json"
    summary_file.write_text(
        json.dumps(
            {
                "summary": batch.summary,
                "duplication_flags": batch.duplication_flags,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Batch summary written to: %s", summary_file)
    logger.info("Summary: %s", json.dumps(batch.summary, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    content = Path(args.content_file).read_text(encoding="utf-8")
    page_data = _load_json(args.page_data)

    from src.prompt_builder import PromptBuilder  # noqa: PLC0415

    builder = PromptBuilder()
    report = builder.validate_content(content, page_data.get("page_type", "blog_post"))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


def cmd_seo_analyze(args: argparse.Namespace) -> int:
    content = Path(args.content_file).read_text(encoding="utf-8")
    page_data = _load_json(args.page_data)

    from src.seo_optimizer import SEOOptimizer  # noqa: PLC0415

    optimizer = SEOOptimizer()
    report = optimizer.analyze(content, page_data)
    print(json.dumps(report, indent=2))
    return 0 if report["seo_score"] >= 60 else 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path_str: str) -> Any:
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def _build_llm_client(args: argparse.Namespace) -> "OpenAIClient":
    api_key = getattr(args, "openai_key", None)
    if not api_key:
        logger.error(
            "An OpenAI API key is required for LLM calls. "
            "Pass it with --openai-key or set OPENAI_API_KEY."
        )
        sys.exit(1)
    model = getattr(args, "model", "gpt-4o") or "gpt-4o"
    return OpenAIClient(api_key=api_key, model=model)


def _resolve_output_path(
    args: argparse.Namespace, page_data: dict
) -> Path:
    if getattr(args, "output", None):
        return Path(args.output)
    slug = _slugify(page_data.get("topic", "output"))
    return Path(f"{slug}.md")


def _print_result_summary(result: "GenerationResult") -> None:
    print("\n=== GENERATION SUMMARY ===")
    print(f"  Quality Score     : {result.quality_score}/100")
    print(f"  Word Count        : {result.word_count}")
    print(f"  Human Review      : {'Yes' if result.human_review_required else 'No'}")
    violations = result.static_validation.get("violations", [])
    if violations:
        print(f"  Static Violations : {len(violations)}")
        for v in violations:
            print(f"    - [{v['type']}] {v.get('text', v.get('pattern', ''))}")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="sturdy-broccoli: AI Template for Scalable Pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    gen = subparsers.add_parser("generate", help="Generate a single content page")
    gen.add_argument("--page-data", required=True, help="Path to page data JSON file")
    gen.add_argument("--output", help="Output Markdown file path")
    gen.add_argument("--openai-key", help="OpenAI API key")
    gen.add_argument("--model", default="gpt-4o", help="OpenAI model name")
    gen.add_argument(
        "--dry-run",
        action="store_true",
        help="Print assembled prompts without calling the LLM",
    )

    # batch
    batch = subparsers.add_parser("batch", help="Generate a batch of content pages")
    batch.add_argument(
        "--pages-file", required=True, help="Path to JSON array of page data objects"
    )
    batch.add_argument(
        "--output-dir", default="output", help="Directory to write output files"
    )
    batch.add_argument("--openai-key", help="OpenAI API key")
    batch.add_argument("--model", default="gpt-4o", help="OpenAI model name")

    # validate
    val = subparsers.add_parser("validate", help="Validate a generated content file")
    val.add_argument("--content-file", required=True, help="Path to Markdown file")
    val.add_argument("--page-data", required=True, help="Path to page data JSON file")

    # seo-analyze
    seo = subparsers.add_parser("seo-analyze", help="SEO-analyze a generated content file")
    seo.add_argument("--content-file", required=True, help="Path to Markdown file")
    seo.add_argument("--page-data", required=True, help="Path to page data JSON file")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    commands = {
        "generate": cmd_generate,
        "batch": cmd_batch,
        "validate": cmd_validate,
        "seo-analyze": cmd_seo_analyze,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
