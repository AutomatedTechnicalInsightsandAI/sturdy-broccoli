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

Hub-and-spoke content cluster (dry-run):

    python generator.py hub-and-spoke \\
        --config examples/hub_and_spoke_linkedin_marketing.json \\
        --output-dir output/linkedin_cluster/ \\
        --dry-run

Competitor analysis:

    python generator.py competitor-analysis \\
        --config examples/competitor_analysis_digital_pr.json

Multi-format content generation (dry-run):

    python generator.py multi-format \\
        --source examples/multi_platform_geo_ai_seo.json \\
        --formats linkedin twitter email \\
        --dry-run
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


def cmd_hub_and_spoke(args: argparse.Namespace) -> int:
    config = _load_json(args.config)

    hub_page_data = config.get("hub_page_data", config)
    spoke_topics = config.get("spoke_topics", [])
    guide_title = config.get("guide_title", None)

    if not spoke_topics:
        logger.error("config must contain a 'spoke_topics' list")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    from src.prompt_builder import PromptBuilder  # noqa: PLC0415
    from src.batch_processor import HubAndSpokeProcessor  # noqa: PLC0415

    if args.dry_run:
        builder = PromptBuilder()
        print("=== HUB PROMPT ===\n")
        print(builder.build_hub_prompt(hub_page_data))
        print("\n\n=== SPOKE PROMPTS ===\n")
        spoke_prompts = builder.build_spoke_prompts(hub_page_data, spoke_topics)
        for sp in spoke_prompts:
            print(f"\n--- Spoke {sp['spoke_number']}: {sp['topic']} ---\n")
            print(sp["prompt"][:500] + "...\n")
        print("\n\n=== THOUGHT LEADERSHIP PROMPT ===\n")
        print(builder.build_thought_leadership_prompt(hub_page_data, guide_title)[:500] + "...")
        return 0

    client = _build_llm_client(args)
    processor = HubAndSpokeProcessor(
        client,
        include_thought_leadership=not args.no_thought_leadership,
    )
    cluster = processor.generate_cluster(hub_page_data, spoke_topics, guide_title)

    # Write hub
    if cluster.hub:
        slug = _slugify(hub_page_data.get("topic", "hub"))
        hub_file = output_dir / f"{slug}_hub.md"
        hub_file.write_text(cluster.hub.final_content, encoding="utf-8")
        logger.info("Hub written: %s (quality=%d)", hub_file, cluster.hub.quality_score)

    # Write spokes
    for i, spoke in enumerate(cluster.spokes):
        spoke_slug = _slugify(spoke_topics[i] if i < len(spoke_topics) else f"spoke_{i}")
        spoke_file = output_dir / f"{spoke_slug}_spoke.md"
        spoke_file.write_text(spoke.final_content, encoding="utf-8")
        logger.info("Spoke %d written: %s (quality=%d)", i + 1, spoke_file, spoke.quality_score)

    # Write thought leadership guide
    if cluster.thought_leadership:
        tl_slug = _slugify(guide_title or f"ultimate-guide-{hub_page_data.get('topic', 'guide')}")
        tl_file = output_dir / f"{tl_slug}_guide.md"
        tl_file.write_text(cluster.thought_leadership.final_content, encoding="utf-8")
        logger.info("Guide written: %s", tl_file)

    # Write summary and linking strategy
    summary_file = output_dir / "cluster_summary.json"
    summary_file.write_text(
        json.dumps(
            {
                "summary": cluster.summary,
                "internal_linking_strategy": cluster.internal_linking_strategy,
                "content_outlines": cluster.content_outlines,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Cluster summary written: %s", summary_file)
    logger.info("Summary: %s", json.dumps(cluster.summary, indent=2))
    return 0


def cmd_competitor_analysis(args: argparse.Namespace) -> int:
    config = _load_json(args.config)

    service_topic = config.get("service_topic", "")
    competitors = config.get("competitors", [])
    our_strengths = config.get("our_strengths", [])

    if not competitors:
        logger.error("config must contain a 'competitors' list")
        return 1

    from src.competitor_analyzer import CompetitorAnalyzer  # noqa: PLC0415

    client = None
    if getattr(args, "openai_key", None):
        client = _build_llm_client(args)

    analyzer = CompetitorAnalyzer(llm_client=client)
    report = analyzer.analyze(service_topic, competitors, our_strengths)

    output: dict[str, Any] = {
        "service_topic": report.service_topic,
        "competitor_count": len(report.competitors),
        "common_themes": report.common_themes,
        "common_keywords": report.common_keywords,
        "content_gaps": report.content_gaps,
        "differentiation_opportunities": report.differentiation_opportunities,
        "unique_positioning": report.unique_positioning,
        "recommended_spoke_topics": report.recommended_spoke_topics,
        "summary": report.summary,
        "competitors": [
            {
                "name": c.name,
                "url": c.url,
                "content_themes": c.content_themes,
                "trust_signals": c.trust_signals,
                "has_case_studies": c.has_case_studies,
                "has_testimonials": c.has_testimonials,
                "has_pricing": c.has_pricing,
                "word_count": c.word_count,
            }
            for c in report.competitors
        ],
    }

    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2), encoding="utf-8")
        logger.info("Competitor analysis written to: %s", args.output)
    else:
        print(json.dumps(output, indent=2))

    return 0


def cmd_multi_format(args: argparse.Namespace) -> int:
    source = _load_json(args.source)

    formats = args.formats if args.formats else None

    from src.multi_format_generator import MultiFormatGenerator  # noqa: PLC0415

    client = None
    if not args.dry_run and getattr(args, "openai_key", None):
        client = _build_llm_client(args)

    gen = MultiFormatGenerator(llm_client=client)

    try:
        bundle = gen.generate_all(source, formats=formats)
    except ValueError as exc:
        logger.error("Multi-format generation error: %s", exc)
        return 1

    if args.dry_run or not args.output_dir:
        for fmt_name, output in bundle.outputs.items():
            print(f"\n{'=' * 60}")
            print(f"FORMAT: {fmt_name.upper()}")
            print(f"Platform notes: {output.platform_notes}")
            print(f"{'=' * 60}\n")
            print(output.content)
        return 0

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ext_map = {
        "html": ".html",
        "markdown": ".md",
        "linkedin": ".txt",
        "youtube": ".md",
        "reddit": ".md",
        "twitter": ".txt",
        "email": ".txt",
    }

    slug = _slugify(source.get("topic", "content"))
    for fmt_name, output in bundle.outputs.items():
        ext = ext_map.get(fmt_name, ".txt")
        out_file = output_dir / f"{slug}_{fmt_name}{ext}"
        out_file.write_text(output.content, encoding="utf-8")
        logger.info("Written: %s", out_file)

    index_file = output_dir / "bundle_index.json"
    index_file.write_text(
        json.dumps(
            {
                "source_topic": bundle.source_topic,
                "source_keyword": bundle.source_keyword,
                "formats_generated": bundle.format_names(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Bundle index written: %s", index_file)
    return 0


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

    # hub-and-spoke
    hs = subparsers.add_parser(
        "hub-and-spoke",
        help="Generate a service hub page + supporting spoke blog posts",
    )
    hs.add_argument(
        "--config",
        required=True,
        help="Path to hub-and-spoke config JSON (see examples/hub_and_spoke_linkedin_marketing.json)",
    )
    hs.add_argument("--output-dir", default="output", help="Directory to write output files")
    hs.add_argument("--openai-key", help="OpenAI API key")
    hs.add_argument("--model", default="gpt-4o", help="OpenAI model name")
    hs.add_argument(
        "--dry-run",
        action="store_true",
        help="Print assembled prompts without calling the LLM",
    )
    hs.add_argument(
        "--no-thought-leadership",
        action="store_true",
        help="Skip generating the long-form thought leadership guide",
    )

    # competitor-analysis
    ca = subparsers.add_parser(
        "competitor-analysis",
        help="Analyse competitors and generate differentiation recommendations",
    )
    ca.add_argument(
        "--config",
        required=True,
        help="Path to competitor analysis config JSON (see examples/competitor_analysis_digital_pr.json)",
    )
    ca.add_argument("--output", help="Path to write JSON report (default: stdout)")
    ca.add_argument("--openai-key", help="OpenAI API key (optional — enables richer analysis)")
    ca.add_argument("--model", default="gpt-4o", help="OpenAI model name")

    # multi-format
    mf = subparsers.add_parser(
        "multi-format",
        help="Generate content for all platforms from a single source",
    )
    mf.add_argument(
        "--source",
        required=True,
        help="Path to source content JSON (see examples/multi_platform_geo_ai_seo.json)",
    )
    mf.add_argument(
        "--formats",
        nargs="+",
        choices=["html", "markdown", "linkedin", "youtube", "reddit", "twitter", "email"],
        help="Formats to generate (default: all)",
    )
    mf.add_argument("--output-dir", help="Directory to write output files (default: print to stdout)")
    mf.add_argument("--openai-key", help="OpenAI API key (optional — enables LLM-enriched output)")
    mf.add_argument("--model", default="gpt-4o", help="OpenAI model name")
    mf.add_argument(
        "--dry-run",
        action="store_true",
        help="Use template-based generation (no LLM call)",
    )

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    commands = {
        "generate": cmd_generate,
        "batch": cmd_batch,
        "validate": cmd_validate,
        "seo-analyze": cmd_seo_analyze,
        "hub-and-spoke": cmd_hub_and_spoke,
        "competitor-analysis": cmd_competitor_analysis,
        "multi-format": cmd_multi_format,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
