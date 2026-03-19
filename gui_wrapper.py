"""
gui_wrapper.py — Streamlit GUI for the sturdy-broccoli content engine.

Run with:
    streamlit run gui_wrapper.py
"""
from __future__ import annotations

import io
import json
from datetime import date, datetime

import streamlit as st

from src.competitor_analyzer import CompetitorAnalyzer
from src.database import Database
from src.multi_format_generator import MultiFormatGenerator
from src.prompt_builder import PromptBuilder
from src.quality_scorer import QualityScorer
from src.template_manager import TemplateManager


def _json_default(obj: object) -> str:
    """Custom JSON encoder fallback for datetime/date objects."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")

st.set_page_config(
    page_title="Sturdy Broccoli — Enterprise SEO Content Factory",
    page_icon="🥦",
    layout="wide",
)

st.title("🥦 Sturdy Broccoli — Enterprise SEO Content Factory")

# ---------------------------------------------------------------------------
# Initialise persistent database (stored in Streamlit session state so the
# same in-process instance is reused across reruns within a session).
# ---------------------------------------------------------------------------
if "db" not in st.session_state:
    st.session_state.db = Database()

db: Database = st.session_state.db

tab_prompt, tab_hub, tab_competitor, tab_multiformat, tab_template, tab_library = st.tabs([
    "📝 Prompt Generator",
    "🕸️ Hub & Spoke",
    "🔍 Competitor Analysis",
    "📢 Multi-Format",
    "🏗️ Landing Page Templates",
    "📚 Page Library",
])

# ---------------------------------------------------------------------------
# Tab 1: Prompt Generator (original functionality)
# ---------------------------------------------------------------------------

with tab_prompt:
    st.header("Prompt Generator")
    st.caption("Build system and chain-of-thought prompts for a single content page.")

    page_data_input = st.text_area(
        "Enter Page Data (JSON):",
        height=300,
        placeholder='{"topic": "...", "primary_keyword": "...", ...}',
        key="prompt_page_data",
    )

    dry_run = st.checkbox("Dry-run mode (show prompts only, no LLM call)", value=True, key="prompt_dry_run")

    if st.button("Generate Prompts", key="btn_generate_prompts"):
        if not page_data_input.strip():
            st.error("Please enter page data JSON before generating.")
        else:
            try:
                page_data = json.loads(page_data_input)
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON: {exc}")
            else:
                try:
                    builder = PromptBuilder()

                    if dry_run:
                        st.subheader("System Prompt")
                        system_prompt = builder.build_system_prompt(page_data)
                        st.code(system_prompt, language="markdown")

                        st.subheader("Chain-of-Thought Prompts")
                        cot_prompts = builder.build_chain_of_thought_prompts(page_data)
                        for stage, prompt in cot_prompts.items():
                            with st.expander(f"Stage: {stage}"):
                                st.code(prompt, language="markdown")
                    else:
                        st.info(
                            "Live generation requires an OpenAI API key. "
                            "Use the CLI for full generation: "
                            "`python generator.py generate --page-data <file> --openai-key <key>`"
                        )
                except ValueError as exc:
                    st.error(f"Page data validation error: {exc}")

# ---------------------------------------------------------------------------
# Tab 2: Hub & Spoke Generator
# ---------------------------------------------------------------------------

with tab_hub:
    st.header("Hub & Spoke Content Generator")
    st.caption(
        "Generate a service hub page, supporting spoke blog posts, and a thought leadership guide "
        "using the hub-and-spoke content model."
    )

    col_hub_left, col_hub_right = st.columns([1, 1])

    with col_hub_left:
        hub_json_input = st.text_area(
            "Hub Page Data (JSON):",
            height=250,
            placeholder='{"topic": "LinkedIn Marketing", "primary_keyword": "...", ...}',
            key="hub_page_data",
        )
        hub_topic_hint = st.text_input(
            "Or load example:", value="", placeholder="e.g. local_seo, linkedin_marketing",
            key="hub_example_hint",
        )
        if hub_topic_hint:
            tm = TemplateManager()
            if hub_topic_hint in tm.list_service_types():
                rendered = tm.render_page_data(hub_topic_hint)
                st.info(f"Loaded template for: {hub_topic_hint}")
                st.json(rendered)

    with col_hub_right:
        spoke_topics_input = st.text_area(
            "Spoke Topics (one per line):",
            height=150,
            placeholder="LinkedIn Algorithm 2024: How to Maximise Reach\nExecutive Ghostwriting on LinkedIn\n...",
            key="hub_spoke_topics",
        )
        guide_title_input = st.text_input(
            "Thought Leadership Guide Title (optional):",
            placeholder="Ultimate Guide to LinkedIn Marketing",
            key="hub_guide_title",
        )

    if st.button("Preview Hub & Spoke Prompts", key="btn_hub_spoke"):
        if not hub_json_input.strip() or not spoke_topics_input.strip():
            st.error("Please provide both hub page data and spoke topics.")
        else:
            try:
                hub_data = json.loads(hub_json_input)
                spoke_topics = [t.strip() for t in spoke_topics_input.strip().splitlines() if t.strip()]
                builder = PromptBuilder()

                with st.expander("Hub Prompt", expanded=True):
                    st.code(builder.build_hub_prompt(hub_data), language="markdown")

                st.subheader(f"Spoke Prompts ({len(spoke_topics)} spokes)")
                spoke_prompts = builder.build_spoke_prompts(hub_data, spoke_topics)
                for sp in spoke_prompts:
                    with st.expander(f"Spoke {sp['spoke_number']}: {sp['topic']}"):
                        st.code(sp["prompt"], language="markdown")

                if guide_title_input:
                    with st.expander("Thought Leadership Guide Prompt"):
                        st.code(
                            builder.build_thought_leadership_prompt(hub_data, guide_title_input),
                            language="markdown",
                        )
            except json.JSONDecodeError as exc:
                st.error(f"Invalid hub page data JSON: {exc}")
            except ValueError as exc:
                st.error(f"Validation error: {exc}")

    st.markdown("---")
    st.info(
        "💡 For full hub-and-spoke generation with LLM calls, use the CLI:\n\n"
        "```bash\n"
        "python generator.py hub-and-spoke \\\n"
        "  --config examples/hub_and_spoke_linkedin_marketing.json \\\n"
        "  --output-dir output/cluster/ \\\n"
        "  --openai-key $OPENAI_API_KEY\n"
        "```"
    )

# ---------------------------------------------------------------------------
# Tab 3: Competitor Analysis
# ---------------------------------------------------------------------------

with tab_competitor:
    st.header("Competitor Analysis")
    st.caption(
        "Analyse competitor pages to identify content gaps, differentiation opportunities, "
        "and recommended spoke topics."
    )

    service_topic_input = st.text_input(
        "Service Topic:", placeholder="e.g. Digital PR Agency", key="ca_service_topic"
    )

    st.subheader("Competitors")
    st.caption("Add competitor data. At minimum provide a name and any content you have.")

    num_competitors = st.number_input(
        "Number of competitors:", min_value=1, max_value=10, value=2, key="ca_num_competitors"
    )

    competitors: list[dict] = []
    for i in range(int(num_competitors)):
        with st.expander(f"Competitor {i + 1}", expanded=(i == 0)):
            c_name = st.text_input(f"Name", key=f"ca_name_{i}")
            c_url = st.text_input(f"URL (optional)", key=f"ca_url_{i}")
            c_content = st.text_area(
                f"Page content / excerpt (optional)",
                height=100,
                key=f"ca_content_{i}",
            )
            c_keywords = st.text_input(
                f"Keywords (comma-separated, optional)",
                key=f"ca_keywords_{i}",
            )
            if c_name:
                competitors.append({
                    "name": c_name,
                    "url": c_url,
                    "content": c_content,
                    "keywords": [k.strip() for k in c_keywords.split(",") if k.strip()],
                })

    our_strengths_input = st.text_area(
        "Your Strengths (one per line, optional):",
        height=100,
        placeholder="Data journalism approach\nJournalist relationships with 200+ outlets",
        key="ca_our_strengths",
    )

    if st.button("Run Competitor Analysis", key="btn_competitor_analysis"):
        if not service_topic_input or not competitors:
            st.error("Please provide a service topic and at least one competitor.")
        else:
            our_strengths = [
                s.strip()
                for s in our_strengths_input.strip().splitlines()
                if s.strip()
            ]
            analyzer = CompetitorAnalyzer()
            report = analyzer.analyze(service_topic_input, competitors, our_strengths)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Competitors Analysed", len(report.competitors))
                st.metric("Content Gaps Found", len(report.content_gaps))
            with col2:
                st.metric("Differentiation Opportunities", len(report.differentiation_opportunities))
                st.metric("Recommended Spoke Topics", len(report.recommended_spoke_topics))

            st.subheader("Analysis Summary")
            st.write(report.summary)

            with st.expander("Common Themes Across Competitors"):
                for t in report.common_themes:
                    st.markdown(f"- {t}")

            with st.expander("Content Gaps (What Competitors Don't Cover)"):
                for g in report.content_gaps:
                    st.markdown(f"- ✅ {g}")

            with st.expander("Differentiation Opportunities"):
                for o in report.differentiation_opportunities:
                    st.markdown(f"- 🎯 {o}")

            with st.expander("Unique Positioning Recommendations"):
                for p in report.unique_positioning:
                    st.markdown(f"- 💡 {p}")

            with st.expander("Recommended Spoke Topics"):
                for s in report.recommended_spoke_topics:
                    st.markdown(f"- 📝 {s}")

    st.markdown("---")
    st.info(
        "💡 For CLI usage:\n\n"
        "```bash\n"
        "python generator.py competitor-analysis \\\n"
        "  --config examples/competitor_analysis_digital_pr.json\n"
        "```"
    )

# ---------------------------------------------------------------------------
# Tab 4: Multi-Format Generator
# ---------------------------------------------------------------------------

with tab_multiformat:
    st.header("Multi-Format Content Generator")
    st.caption(
        "Generate platform-specific content (LinkedIn, Twitter, YouTube, Reddit, Email, HTML, Markdown) "
        "from a single content source."
    )

    source_json_input = st.text_area(
        "Content Source (JSON):",
        height=200,
        placeholder='{"topic": "...", "primary_keyword": "...", "key_points": [...], "cta": "..."}',
        key="mf_source",
    )

    available_formats = MultiFormatGenerator.supported_formats()
    selected_formats = st.multiselect(
        "Formats to generate:",
        options=available_formats,
        default=available_formats,
        key="mf_formats",
    )

    if st.button("Generate Multi-Format Content", key="btn_multi_format"):
        if not source_json_input.strip():
            st.error("Please enter a content source JSON.")
        elif not selected_formats:
            st.error("Please select at least one format.")
        else:
            try:
                source = json.loads(source_json_input)
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON: {exc}")
            else:
                gen = MultiFormatGenerator()
                try:
                    bundle = gen.generate_all(source, formats=selected_formats)
                    st.success(f"Generated {len(bundle.outputs)} format(s) for: {bundle.source_topic}")

                    for fmt_name, output in bundle.outputs.items():
                        with st.expander(f"📄 {fmt_name.upper()} — {output.platform_notes}"):
                            st.code(output.content, language="html" if fmt_name == "html" else "markdown")
                            if output.estimated_reach:
                                st.caption(f"Estimated reach: {output.estimated_reach}")
                except ValueError as exc:
                    st.error(f"Generation error: {exc}")

    st.markdown("---")
    st.info(
        "💡 For CLI usage:\n\n"
        "```bash\n"
        "python generator.py multi-format \\\n"
        "  --source examples/multi_platform_geo_ai_seo.json \\\n"
        "  --formats linkedin twitter email \\\n"
        "  --output-dir output/formats/\n"
        "```"
    )

# ---------------------------------------------------------------------------
# Tab 5: Landing Page Templates
# ---------------------------------------------------------------------------

with tab_template:
    st.header("Service Landing Page Templates")
    st.caption(
        "Browse and render landing page templates for CrowdCreate services. "
        "Each template includes H1/H2 structure, trust factors, testimonials, CTAs, and related services."
    )

    tm = TemplateManager()
    service_types = tm.list_service_types()

    selected_service = st.selectbox(
        "Select Service Type:",
        options=service_types,
        key="tmpl_service_type",
    )

    if selected_service:
        template = tm.get_template(selected_service)

        col_t1, col_t2 = st.columns([2, 1])

        with col_t1:
            st.subheader(template["h1"])
            st.write(template["service_description"])

            with st.expander("H2 Structure"):
                for i, h2 in enumerate(template["h2_sections"], 1):
                    st.markdown(f"{i}. **{h2}**")

            with st.expander("Trust Factors"):
                for tf in template["trust_factors"]:
                    st.markdown(f"✅ {tf}")

            with st.expander("Client Testimonials"):
                for t in template["testimonials"]:
                    st.markdown(f'> *"{t["quote"]}"*')
                    st.caption(f'— {t["author"]}')

        with col_t2:
            st.subheader("CTAs")
            st.button(template["cta"]["primary"], key=f"cta_primary_{selected_service}")
            st.button(template["cta"]["secondary"], key=f"cta_secondary_{selected_service}")

            st.subheader("Related Services")
            for svc in template["related_services"]:
                st.markdown(f"→ {svc}")

            st.subheader("Keywords")
            st.markdown(f"**Primary:** `{template['primary_keyword']}`")
            st.markdown("**Secondary:**")
            for kw in template["secondary_keywords"]:
                st.markdown(f"- `{kw}`")

        with st.expander("HTML Structure Preview"):
            html_preview = tm.render_html_structure(selected_service)
            st.code(html_preview, language="html")

        with st.expander("Page Data JSON (for Prompt Generator)"):
            page_data = tm.render_page_data(selected_service)
            st.json(page_data)

        # Quality score for the HTML preview
        with st.expander("📊 Quality Scores for This Template"):
            scorer = QualityScorer()
            result = scorer.score(html_preview, page_data)
            d = result.as_dict()

            col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
            col_s1.metric("🏛️ Authority", f"{d['authority']:.0f}/100")
            col_s2.metric("🧠 Semantic", f"{d['semantic']:.0f}/100")
            col_s3.metric("🏗️ Structure", f"{d['structure']:.0f}/100")
            col_s4.metric("🎯 Engagement", f"{d['engagement']:.0f}/100")
            col_s5.metric("✨ Uniqueness", f"{d['uniqueness']:.0f}/100")

            st.metric("⭐ Overall Quality Score", f"{d['overall']:.1f}/100")

            for dim, notes in d["explanations"].items():
                with st.expander(f"{dim.capitalize()} Recommendations"):
                    for note in notes:
                        st.write(f"• {note}")

        if st.button(
            f"💾 Save '{template['h1']}' to Page Library",
            key=f"save_template_{selected_service}",
        ):
            pid = db.create_page(
                service_type=selected_service,
                topic=template["h1"],
                primary_keyword=template["primary_keyword"],
                page_type="landing_page",
            )
            db.save_content_version(
                pid,
                content_html=html_preview,
                content_markdown="",
                quality_report=result.as_dict(),
            )
            db.save_quality_scores(pid, d)
            st.success(f"✅ Saved to Page Library (ID: {pid})")

# ---------------------------------------------------------------------------
# Tab 6: Page Library (database-backed)
# ---------------------------------------------------------------------------

with tab_library:
    st.header("📚 Page Library")
    st.caption(
        "Manage all generated pages stored in the persistent database. "
        "Filter, review quality scores, update status, and export content."
    )

    # Dashboard stats
    stats = db.get_dashboard_stats()
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Pages", stats["total_pages"])
    c2.metric("Published", stats["published_pages"])
    c3.metric("Draft", stats["draft_pages"])
    c4.metric("In Review", stats["review_pages"])
    c5.metric("Total Words", f"{stats['total_words']:,}")
    c6.metric("Avg Quality", f"{stats['avg_quality_score']:.1f}")

    st.markdown("---")

    # Client management
    with st.expander("👥 Client Management"):
        col_cl1, col_cl2 = st.columns(2)
        with col_cl1:
            cl_name = st.text_input("Client Name", key="lib_cl_name")
            cl_slug = st.text_input("Client Slug (URL-safe)", key="lib_cl_slug")
            cl_site = st.text_input("Website (optional)", key="lib_cl_site")
            if st.button("Add Client", key="lib_add_client"):
                if cl_name and cl_slug:
                    try:
                        cid = db.create_client(cl_name, cl_slug, cl_site)
                        st.success(f"Client added (ID: {cid})")
                    except Exception as exc:
                        st.error(f"Error: {exc}")
                else:
                    st.warning("Name and slug are required.")
        with col_cl2:
            clients = db.list_clients()
            if clients:
                st.subheader("Existing Clients")
                for c in clients:
                    st.write(f"**{c['name']}** (`{c['slug']}`)")
            else:
                st.info("No clients yet.")

    st.markdown("---")

    # Filter controls
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_status = st.selectbox(
            "Filter by Status",
            ["All", "draft", "review", "published", "archived"],
            key="lib_filter_status",
        )
    with col_f2:
        tm_lib = TemplateManager()
        filter_service = st.selectbox(
            "Filter by Service Type",
            ["All"] + tm_lib.list_service_types(),
            key="lib_filter_service",
        )
    with col_f3:
        clients_list = db.list_clients()
        client_options = {"All": None}
        for cl in clients_list:
            client_options[cl["name"]] = cl["id"]
        selected_client_name = st.selectbox(
            "Filter by Client",
            list(client_options.keys()),
            key="lib_filter_client",
        )

    pages = db.list_pages(
        status=filter_status if filter_status != "All" else None,
        service_type=filter_service if filter_service != "All" else None,
        client_id=client_options.get(selected_client_name),
    )

    if not pages:
        st.info("No pages found. Generate some using the Landing Page Templates tab.")
    else:
        st.write(f"**{len(pages)} page(s) found**")
        for page in pages:
            with st.expander(
                f"[{page['status'].upper()}] {page['topic']} — `{page['primary_keyword']}`",
                expanded=False,
            ):
                col_p1, col_p2, col_p3 = st.columns([2, 1, 1])

                with col_p1:
                    st.write(f"**Service:** {page['service_type']}")
                    st.write(f"**Created:** {page['created_at'][:10]}")
                    st.write(f"**Updated:** {page['updated_at'][:10]}")

                with col_p2:
                    quality = db.get_latest_quality_scores(page["id"])
                    if quality:
                        st.metric("Overall Quality", f"{quality['overall']:.1f}")
                        st.metric("Authority", f"{quality['authority']:.1f}")
                        st.metric("Structure", f"{quality['structure']:.1f}")
                    else:
                        st.info("No quality scores yet.")

                with col_p3:
                    new_status = st.selectbox(
                        "Status",
                        ["draft", "review", "published", "archived"],
                        index=["draft", "review", "published", "archived"].index(
                            page["status"]
                        ),
                        key=f"lib_status_{page['id']}",
                    )
                    if st.button("Update Status", key=f"lib_update_{page['id']}"):
                        db.update_page_status(page["id"], new_status)
                        st.success("Status updated.")
                        st.rerun()
                    if st.button(
                        "🗑️ Delete", key=f"lib_delete_{page['id']}", type="secondary"
                    ):
                        db.delete_page(page["id"])
                        st.warning("Page deleted.")
                        st.rerun()

                # Show latest content version
                version = db.get_latest_version(page["id"])
                if version:
                    st.write(f"**Version {version['version']}** · {version['word_count']} words")
                    with st.expander("View HTML"):
                        st.code(version["content_html"], language="html")
                    if version["content_markdown"]:
                        with st.expander("View Markdown"):
                            st.code(version["content_markdown"], language="markdown")

    # Bulk export section
    st.markdown("---")
    st.subheader("📦 Bulk Export")
    if pages:
        export_format = st.radio(
            "Export format", ["JSON", "HTML files summary"], horizontal=True, key="lib_export_fmt"
        )
        if st.button("Export All Filtered Pages", key="lib_export"):
            if export_format == "JSON":
                export_data = []
                for page in pages:
                    entry = dict(page)
                    version = db.get_latest_version(page["id"])
                    if version:
                        entry["latest_version"] = version
                    scores = db.get_latest_quality_scores(page["id"])
                    if scores:
                        entry["quality_scores"] = scores
                    export_data.append(entry)
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json.dumps(export_data, indent=2, default=_json_default),
                    file_name="page_library_export.json",
                    mime="application/json",
                )
            else:
                html_parts: list[str] = [
                    "<html><body>",
                    "<h1>Page Library Export</h1>",
                ]
                for page in pages:
                    version = db.get_latest_version(page["id"])
                    html_content = version["content_html"] if version else ""
                    html_parts.append(f"<section><h2>{page['topic']}</h2>")
                    html_parts.append(html_content)
                    html_parts.append("</section><hr/>")
                html_parts.append("</body></html>")
                st.download_button(
                    label="⬇️ Download HTML",
                    data="\n".join(html_parts),
                    file_name="page_library_export.html",
                    mime="text/html",
                )
