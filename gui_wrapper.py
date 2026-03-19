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
from src.agency_dashboard import AgencyDashboard
from src.batch_validator import BatchValidator
from src.staging_environment import StagingEnvironment
from src.staging_review import StagingReviewManager


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

tab_prompt, tab_hub, tab_competitor, tab_multiformat, tab_template, tab_library, tab_staging, tab_validator, tab_agency = st.tabs([
    "📝 Prompt Generator",
    "🕸️ Hub & Spoke",
    "🔍 Competitor Analysis",
    "📢 Multi-Format",
    "🏗️ Landing Page Templates",
    "📚 Page Library",
    "🎭 Staging Review",
    "✅ Batch Validator",
    "💼 Agency Dashboard",
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

# ---------------------------------------------------------------------------
# Tab 7: Staging Review — Client approval workflow
# ---------------------------------------------------------------------------

with tab_staging:
    st.header("🎭 Staging Review")
    st.caption(
        "Review generated pages before deployment. Approve or reject pages, "
        "add client feedback, and track revision history."
    )

    if "staging_env" not in st.session_state:
        st.session_state.staging_env = StagingEnvironment(db)
        st.session_state.staging_review_mgr = StagingReviewManager(db)

    staging_env: StagingEnvironment = st.session_state.staging_env
    staging_review_mgr: StagingReviewManager = st.session_state.staging_review_mgr

    # -- Batch selector -------------------------------------------------------
    batches = staging_review_mgr.list_batches()
    if not batches:
        st.info("No staging batches found. Create a batch first via the Hub & Spoke tab.")
    else:
        batch_options = {f"{b['name']} (id:{b['id']})": b["id"] for b in batches}
        selected_label = st.selectbox("Select Batch", list(batch_options.keys()))
        selected_batch_id = batch_options[selected_label]

        gallery = staging_env.get_batch_gallery(selected_batch_id)
        batch_meta = gallery["batch"]
        pages = gallery["pages"]

        if batch_meta:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Pages", batch_meta.get("total_pages", len(pages)))
            col2.metric("Approved", batch_meta.get("pages_approved", 0))
            col3.metric("Draft", batch_meta.get("pages_draft", 0))

        st.divider()

        # -- Status filter ----------------------------------------------------
        status_filter = st.radio(
            "Filter by Status",
            ["All", "draft", "approved", "needs_revision", "rejected", "deployed"],
            horizontal=True,
        )
        filtered_pages = (
            pages
            if status_filter == "All"
            else [p for p in pages if p.get("status") == status_filter]
        )

        # -- Page gallery -------------------------------------------------
        if not filtered_pages:
            st.info(f"No pages with status '{status_filter}'.")
        else:
            # Bulk action controls
            all_ids = [p["id"] for p in filtered_pages if p.get("id")]
            st.write(f"**{len(filtered_pages)} page(s) shown**")
            col_a, col_r, _ = st.columns([1, 1, 4])
            if col_a.button("✅ Approve All Visible"):
                count = staging_env.bulk_approve(all_ids, reviewer="manager")
                st.success(f"Approved {count} pages.")
                st.rerun()
            if col_r.button("❌ Reject All Visible"):
                count = staging_env.bulk_reject(all_ids, reviewer="manager")
                st.warning(f"Rejected {count} pages.")
                st.rerun()

            for page in filtered_pages:
                with st.expander(
                    f"📄 {page.get('title', 'Untitled')} — {page.get('status', '?')}"
                ):
                    st.write(f"**Slug:** `{page.get('slug')}`")
                    st.write(f"**Keyword:** {page.get('primary_keyword', '—')}")
                    st.write(f"**Word Count:** {page.get('word_count', 0)}")
                    st.write(f"**Template:** {page.get('assigned_template', '—')}")
                    if page.get("meta_description"):
                        st.write(f"**Meta:** {page['meta_description']}")

                    # Individual approve/reject
                    c1, c2 = st.columns(2)
                    pid = page.get("id")
                    if pid:
                        if c1.button("✅ Approve", key=f"approve_{pid}"):
                            staging_env.bulk_approve([pid], reviewer="manager")
                            st.rerun()
                        if c2.button("❌ Reject", key=f"reject_{pid}"):
                            staging_env.bulk_reject([pid], reviewer="manager")
                            st.rerun()

                        # Comment box
                        comment = st.text_input(
                            "Add comment", key=f"comment_{pid}", placeholder="Enter feedback…"
                        )
                        if st.button("💬 Save Comment", key=f"save_comment_{pid}") and comment:
                            staging_env.add_page_comment(pid, comment, reviewer="client")
                            st.success("Comment saved.")

        st.divider()

        # -- Deployment readiness --------------------------------------------
        readiness = staging_env.get_deploy_readiness(selected_batch_id)
        if readiness["ready"]:
            st.success(
                f"✅ All {readiness['approved_count']} pages approved — "
                "ready for deployment!"
            )
        else:
            st.warning(
                f"⚠️ {readiness['approved_count']}/{readiness['total_count']} "
                f"pages approved. {len(readiness['blocked_pages'])} page(s) blocked."
            )


# ---------------------------------------------------------------------------
# Tab 8: Batch Validator — Hub-and-Spoke structure checker
# ---------------------------------------------------------------------------

with tab_validator:
    st.header("✅ Batch Validator")
    st.caption(
        "Validate your hub-and-spoke SILO structure before deployment. "
        "Checks internal links, keyword density, schema markup, and orphaned pages."
    )

    if "batch_validator" not in st.session_state:
        st.session_state.batch_validator = BatchValidator()
        st.session_state.validator_review_mgr = StagingReviewManager(db)

    validator: BatchValidator = st.session_state.batch_validator
    val_review_mgr: StagingReviewManager = st.session_state.validator_review_mgr

    val_batches = val_review_mgr.list_batches()
    if not val_batches:
        st.info("No batches found. Generate pages first.")
    else:
        val_batch_options = {
            f"{b['name']} (id:{b['id']})": b["id"] for b in val_batches
        }
        val_selected_label = st.selectbox(
            "Select Batch to Validate", list(val_batch_options.keys()), key="val_batch"
        )
        val_batch_id = val_batch_options[val_selected_label]

        hub_slug_input = st.text_input(
            "Hub Page Slug (leave blank for auto-detect)",
            placeholder="e.g. postgresql-optimisation",
        )

        if st.button("🔍 Run Validation"):
            val_pages = val_review_mgr.get_batch_pages(val_batch_id)

            # Convert content_pages format to batch_validator format
            normalised = []
            for p in val_pages:
                normalised.append(
                    {
                        "slug": p.get("slug"),
                        "title": p.get("title"),
                        "h1_content": p.get("h1_content"),
                        "primary_keyword": p.get("primary_keyword", ""),
                        "content_markdown": p.get("content_markdown", ""),
                        "internal_links": p.get("internal_links") or [],
                        "schema_json_ld": None,
                        "hub_page_id": p.get("hub_page_id"),
                        "is_hub": p.get("hub_page_id") is None,
                    }
                )

            result = validator.validate(
                normalised,
                hub_slug=hub_slug_input.strip() or None,
            )

            # Display result
            if result.valid:
                st.success("✅ Hub-and-Spoke structure is valid!")
            else:
                st.error("❌ Validation failed — see issues below.")

            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Spokes", result.spoke_count)
            col_b.metric(
                "Internal Links",
                f"{result.valid_internal_links}/{result.total_internal_links}",
            )
            col_c.metric("Keyword Density", f"{result.keyword_density:.1f}%")
            col_d.metric("Schema Valid", "✅" if result.schema_valid else "❌")

            st.subheader("Validation Report")
            st.code(result.to_report(), language="text")

            if result.orphaned_pages:
                st.warning(f"Orphaned pages: {', '.join(result.orphaned_pages)}")

            if result.issues:
                st.subheader(f"Issues ({len(result.issues)})")
                for issue in result.issues:
                    icon = "❌" if issue.severity == "error" else "⚠️"
                    page_ref = f"`{issue.page_slug}` — " if issue.page_slug else ""
                    st.write(f"{icon} {page_ref}{issue.message}")


# ---------------------------------------------------------------------------
# Tab 9: Agency Dashboard — Client pipeline + revenue tracking
# ---------------------------------------------------------------------------

with tab_agency:
    st.header("💼 Agency Dashboard")
    st.caption(
        "Track your client pipeline, batch statuses, revenue, "
        "and deployment history."
    )

    if "agency_dashboard" not in st.session_state:
        st.session_state.agency_dashboard = AgencyDashboard(db)

    agency: AgencyDashboard = st.session_state.agency_dashboard

    # -- Revenue KPIs ---------------------------------------------------------
    stats = agency.get_revenue_stats()
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("💰 Total Revenue", f"${stats['total_revenue']:,.0f}")
    k2.metric("📝 Draft", stats["draft_batches"])
    k3.metric("🎭 Staged", stats["staged_batches"])
    k4.metric("✅ Approved", stats["approved_batches"])
    k5.metric("🚀 Deployed", stats["deployed_batches"])

    st.divider()

    # -- Add new client -------------------------------------------------------
    with st.expander("➕ Add New Client"):
        with st.form("add_client_form"):
            c_name = st.text_input("Client Name", placeholder="Acme Corp")
            c_slug = st.text_input("Slug", placeholder="acme-corp")
            c_industry = st.text_input("Industry", placeholder="SaaS")
            c_email = st.text_input("Email", placeholder="contact@acme.com")
            c_website = st.text_input("Website", placeholder="https://acme.com")
            c_value = st.number_input(
                "Contract Value ($)", min_value=0.0, step=500.0, value=2000.0
            )
            if st.form_submit_button("Save Client"):
                if c_name and c_slug:
                    try:
                        agency.create_client(
                            name=c_name,
                            slug=c_slug,
                            industry=c_industry,
                            email=c_email,
                            website=c_website,
                            contract_value=c_value,
                        )
                        st.success(f"Client '{c_name}' created.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Error: {exc}")
                else:
                    st.warning("Name and slug are required.")

    # -- Add new batch --------------------------------------------------------
    with st.expander("➕ Create New Staging Batch"):
        with st.form("add_batch_form"):
            b_name = st.text_input("Batch Name", placeholder="Q2 Campaign — Landing Pages")
            b_client = st.text_input("Client Name", placeholder="Acme Corp")
            b_pages = st.number_input("Total Pages", min_value=1, value=10, step=1)
            b_price = st.number_input(
                "Price Paid ($)", min_value=0.0, step=500.0, value=3000.0
            )
            if st.form_submit_button("Create Batch"):
                if b_name:
                    bid = agency.create_staging_batch(
                        batch_name=b_name,
                        client_name=b_client,
                        total_pages=int(b_pages),
                        price_paid=b_price,
                    )
                    st.success(f"Batch '{b_name}' created (id: {bid}).")
                    st.rerun()

    st.divider()

    # -- Pipeline view --------------------------------------------------------
    st.subheader("📊 Batch Pipeline")
    pipeline = agency.get_pipeline_summary()
    if not pipeline:
        st.info("No batches yet. Create one above.")
    else:
        for batch in pipeline:
            status_icon = {
                "draft": "📝",
                "staged": "🎭",
                "approved": "✅",
                "deployed": "🚀",
            }.get(batch.get("status", "draft"), "📄")

            with st.expander(
                f"{status_icon} {batch.get('batch_name')} — "
                f"{batch.get('client_name', '—')} | "
                f"${batch.get('price_paid', 0):,.0f}"
            ):
                col_s, col_p, col_r = st.columns(3)
                col_s.write(f"**Status:** {batch.get('status')}")
                col_p.write(f"**Pages:** {batch.get('total_pages', 0)}")
                col_r.write(f"**Reviews:** {batch.get('review_count', 0)}")

                if batch.get("deployed_url"):
                    st.write(f"**Live URL:** {batch['deployed_url']}")

                # Status advancement
                current = batch.get("status", "draft")
                next_status_map = {
                    "draft": "staged",
                    "staged": "approved",
                    "approved": "deployed",
                }
                next_status = next_status_map.get(current)
                if next_status:
                    deploy_url = ""
                    if next_status == "deployed":
                        deploy_url = st.text_input(
                            "Deployed URL",
                            key=f"deploy_url_{batch['id']}",
                            placeholder="https://client-site.com",
                        )
                    if st.button(
                        f"Advance to {next_status.upper()} →",
                        key=f"advance_{batch['id']}",
                    ):
                        agency.advance_batch_status(
                            batch["id"], next_status, deployed_url=deploy_url
                        )
                        if next_status == "deployed":
                            agency.record_deployment(
                                batch_id=batch["id"],
                                deployed_by="admin",
                                deployed_url=deploy_url,
                            )
                        st.success(f"Batch advanced to '{next_status}'.")
                        st.rerun()

                # Client comments
                new_comment = st.text_input(
                    "Add Client Comment",
                    key=f"batch_comment_{batch['id']}",
                    placeholder="Client feedback…",
                )
                comment_status = st.radio(
                    "Comment Status",
                    ["pending", "approved", "rejected"],
                    horizontal=True,
                    key=f"comment_status_{batch['id']}",
                )
                if (
                    st.button("💬 Save Comment", key=f"save_batch_comment_{batch['id']}")
                    and new_comment
                ):
                    agency.add_client_review(
                        batch["id"], new_comment, status=comment_status
                    )
                    st.success("Comment saved.")

    st.divider()

    # -- Client list ----------------------------------------------------------
    st.subheader("👥 Clients")
    clients = agency.list_clients()
    if not clients:
        st.info("No clients yet. Add one above.")
    else:
        for client in clients:
            st.write(
                f"**{client['name']}** — {client.get('industry', '—')} | "
                f"${client.get('contract_value', 0):,.0f} | "
                f"{client.get('email', '—')} | {client.get('status', 'active')}"
            )
