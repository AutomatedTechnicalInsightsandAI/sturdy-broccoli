"""
gui_wrapper.py — Streamlit GUI for the sturdy-broccoli content engine.

Run with:
    streamlit run gui_wrapper.py
"""
from __future__ import annotations

import io
import json

import streamlit as st

from src.prompt_builder import PromptBuilder
from src.template_manager import TemplateManager
from src.competitor_analyzer import CompetitorAnalyzer
from src.multi_format_generator import MultiFormatGenerator
from src.staging_manager import StagingManager
from src.tailwind_templates import list_templates as _list_tpl_names

st.set_page_config(
    page_title="Sturdy Broccoli — Enterprise SEO Content Factory",
    page_icon="🥦",
    layout="wide",
)

st.title("🥦 Sturdy Broccoli — Enterprise SEO Content Factory")

tab_prompt, tab_hub, tab_competitor, tab_multiformat, tab_template, tab_factory = st.tabs([
    "📝 Prompt Generator",
    "🕸️ Hub & Spoke",
    "🔍 Competitor Analysis",
    "📢 Multi-Format",
    "🏗️ Landing Page Templates",
    "🏭 SEO Site Factory",
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

# ---------------------------------------------------------------------------
# Tab 6: SEO Site Factory  (Three-Tier Batch Pipeline)
# ---------------------------------------------------------------------------

# ── Session-state initialisation ─────────────────────────────────────────────

if "factory_batch_id" not in st.session_state:
    st.session_state.factory_batch_id = None
if "factory_selected_pages" not in st.session_state:
    st.session_state.factory_selected_pages = []
if "factory_preview_page_id" not in st.session_state:
    st.session_state.factory_preview_page_id = None
if "factory_deploy_manifest" not in st.session_state:
    st.session_state.factory_deploy_manifest = None

_TEMPLATE_DISPLAY = _list_tpl_names()
_TEMPLATE_KEYS = list(_TEMPLATE_DISPLAY.keys())
_TEMPLATE_LABELS = [_TEMPLATE_DISPLAY[k] for k in _TEMPLATE_KEYS]
_STATUS_COLORS = {
    "pending_review": "🔴",
    "reviewed": "🟡",
    "approved": "🟢",
    "deployed": "🔵",
    "archived": "⚫",
}
_STATUS_ORDER = ["pending_review", "reviewed", "approved", "deployed", "archived"]


@st.cache_resource
def _get_staging_manager() -> StagingManager:
    return StagingManager()


_mgr = _get_staging_manager()


def _qs_badge(scores: dict) -> str:
    """Return a short quality score string for tile display."""
    if not scores:
        return "N/A"
    overall = scores.get("overall", 0)
    color = "🟢" if overall >= 70 else ("🟡" if overall >= 40 else "🔴")
    return f"{color} {overall}/100"


def _render_batch_tile(page: dict, col) -> None:
    """Render a single page tile inside the given Streamlit column."""
    pid = page["id"]
    status_icon = _STATUS_COLORS.get(page["status"], "⚪")
    qs = page.get("quality_scores") or {}
    badge = _qs_badge(qs)
    is_selected = pid in st.session_state.factory_selected_pages

    with col:
        with st.container(border=True):
            # Header row: checkbox + status
            hcol1, hcol2 = st.columns([3, 1])
            with hcol1:
                checked = st.checkbox(
                    f"{status_icon} **{page['title'][:45]}{'…' if len(page['title']) > 45 else ''}**",
                    value=is_selected,
                    key=f"sel_{pid}",
                )
            with hcol2:
                st.caption(page["status"].replace("_", " ").title())

            # Update selection list
            if checked and pid not in st.session_state.factory_selected_pages:
                st.session_state.factory_selected_pages.append(pid)
            elif not checked and pid in st.session_state.factory_selected_pages:
                st.session_state.factory_selected_pages.remove(pid)

            # Content preview
            st.caption(f"🔑 {page.get('primary_keyword', '—')}")
            h1 = page.get("h1_content") or page.get("title", "")
            st.markdown(f"**H1:** {h1[:70]}{'…' if len(h1) > 70 else ''}")
            desc = page.get("meta_description", "")
            if desc:
                st.caption(desc[:100] + ("…" if len(desc) > 100 else ""))

            # Template + quality row
            tpl_name = _TEMPLATE_DISPLAY.get(page.get("assigned_template", ""), page.get("assigned_template", ""))
            qcol1, qcol2 = st.columns(2)
            with qcol1:
                st.caption(f"🏗️ {tpl_name}")
            with qcol2:
                st.caption(f"⭐ {badge}")

            # Action buttons
            acol1, acol2, acol3 = st.columns(3)
            with acol1:
                if st.button("👁 Preview", key=f"preview_{pid}", use_container_width=True):
                    st.session_state.factory_preview_page_id = pid
                    st.rerun()
            with acol2:
                if page["status"] in ("pending_review", "reviewed"):
                    if st.button("✅ Approve", key=f"approve_{pid}", use_container_width=True):
                        _mgr.approve_pages([pid])
                        st.rerun()
            with acol3:
                if st.button("🗑 Delete", key=f"delete_{pid}", use_container_width=True):
                    _mgr.delete_page(pid)
                    if pid in st.session_state.factory_selected_pages:
                        st.session_state.factory_selected_pages.remove(pid)
                    st.rerun()


with tab_factory:
    st.header("🏭 SEO Site Factory")
    st.caption(
        "Three-tier pipeline: Generate → Stage → Deploy. "
        "Manage 50+ landing pages from generation through deployment."
    )

    # ── Preview modal (rendered above the dashboard when a page is selected) ──
    if st.session_state.factory_preview_page_id is not None:
        pid = st.session_state.factory_preview_page_id
        page = _mgr.get_page(pid)
        if page:
            with st.container(border=True):
                st.subheader(f"📄 Full Preview — {page['title']}")
                close_col, tpl_col, color_col, cta_col = st.columns([1, 2, 1, 2])
                with close_col:
                    if st.button("✕ Close Preview", key="close_preview"):
                        st.session_state.factory_preview_page_id = None
                        st.rerun()

                preview_state = page.get("preview_state") or {}
                current_tpl = preview_state.get("current_layout", page.get("assigned_template", "modern_saas"))
                current_color = preview_state.get("color_override", "blue")
                current_cta = preview_state.get("cta_link", "#get-started")

                with tpl_col:
                    tpl_idx = _TEMPLATE_KEYS.index(current_tpl) if current_tpl in _TEMPLATE_KEYS else 0
                    chosen_tpl_label = st.selectbox(
                        "Template",
                        _TEMPLATE_LABELS,
                        index=tpl_idx,
                        key=f"modal_tpl_{pid}",
                    )
                    chosen_tpl = _TEMPLATE_KEYS[_TEMPLATE_LABELS.index(chosen_tpl_label)]

                with color_col:
                    chosen_color = st.selectbox(
                        "Brand Color",
                        ["blue", "indigo", "purple", "green", "red", "orange", "teal", "slate"],
                        index=["blue", "indigo", "purple", "green", "red", "orange", "teal", "slate"].index(current_color)
                        if current_color in ["blue", "indigo", "purple", "green", "red", "orange", "teal", "slate"]
                        else 0,
                        key=f"modal_color_{pid}",
                    )

                with cta_col:
                    chosen_cta = st.text_input("CTA Link", value=current_cta, key=f"modal_cta_{pid}")

                # Split-screen: editor (left) + live preview (right)
                editor_col, preview_col = st.columns([1, 1])

                with editor_col:
                    st.subheader("✏️ Markdown Editor")
                    new_md = st.text_area(
                        "Content (Markdown)",
                        value=page.get("content_markdown", ""),
                        height=400,
                        key=f"md_editor_{pid}",
                    )
                    save_col, approve_col = st.columns(2)
                    with save_col:
                        if st.button("💾 Save", key=f"save_md_{pid}"):
                            _mgr.update_page_markdown(pid, new_md)
                            _mgr.save_preview_state(pid, template=chosen_tpl, color=chosen_color, cta_link=chosen_cta)
                            st.success("Saved!")
                            st.rerun()
                    with approve_col:
                        if page["status"] not in ("approved", "deployed"):
                            if st.button("✅ Approve", key=f"modal_approve_{pid}"):
                                _mgr.update_page_markdown(pid, new_md)
                                _mgr.save_preview_state(pid, template=chosen_tpl, color=chosen_color, cta_link=chosen_cta)
                                _mgr.approve_pages([pid])
                                st.success("Approved!")
                                st.rerun()

                    # Quality score breakdown
                    qs = page.get("quality_scores") or {}
                    if qs:
                        st.subheader("📊 Quality Scores")
                        metrics = [
                            ("Authority", qs.get("authority", 0)),
                            ("Semantic Richness", qs.get("semantic", 0)),
                            ("Structure", qs.get("structure", 0)),
                            ("Engagement", qs.get("engagement", 0)),
                            ("Uniqueness", qs.get("uniqueness", 0)),
                        ]
                        q1, q2, q3, q4, q5 = st.columns(5)
                        for (label, val), qcol in zip(metrics, [q1, q2, q3, q4, q5]):
                            qcol.metric(label, f"{val}/100")

                with preview_col:
                    st.subheader("🌐 Live Preview")
                    try:
                        html_preview = _mgr.render_page_preview(
                            pid,
                            template_override=chosen_tpl,
                            color_override=chosen_color,
                            cta_link_override=chosen_cta,
                        )
                        st.components.v1.html(html_preview, height=500, scrolling=True)
                    except Exception as exc:
                        st.error(f"Preview error: {exc}")

        st.divider()

    # ── Deployment result display ────────────────────────────────────────────
    if st.session_state.factory_deploy_manifest:
        manifest = st.session_state.factory_deploy_manifest
        with st.container(border=True):
            st.subheader("🚀 Deployment Summary")
            st.success(
                f"✅ {manifest['deployed_count']} page(s) deployed at {manifest['deployed_at']}"
            )
            if manifest.get("warnings"):
                st.warning("⚠️ Warnings:\n" + "\n".join(f"- {w}" for w in manifest["warnings"]))

            st.markdown("**Deployed URLs:**")
            for p in manifest["pages"]:
                st.markdown(f"- `{p['url']}` — {p['title']}")

            csv_data = _mgr.generate_deployment_csv(manifest)
            dcol1, dcol2 = st.columns(2)
            with dcol1:
                st.download_button(
                    "⬇️ Download CSV Report",
                    data=csv_data,
                    file_name="deployment_report.csv",
                    mime="text/csv",
                    key="dl_csv",
                )
            with dcol2:
                if st.button("✕ Close", key="close_manifest"):
                    st.session_state.factory_deploy_manifest = None
                    st.rerun()

        st.divider()

    # ── Tier 1: Batch Generation ─────────────────────────────────────────────
    with st.expander("🔧 Tier 1 — Generate New Batch", expanded=(st.session_state.factory_batch_id is None)):
        st.caption("Generate 50+ landing pages and push them to the Pending Review staging queue.")
        g1, g2 = st.columns(2)
        with g1:
            gen_service = st.text_input("Service Name", placeholder="e.g. Local SEO", key="gen_service")
            gen_keyword = st.text_input("Primary Keyword", placeholder="e.g. local seo agency", key="gen_keyword")
        with g2:
            gen_count = st.number_input("Number of Pages", min_value=1, max_value=100, value=10, key="gen_count")
            gen_batch_name = st.text_input("Batch Name", placeholder="e.g. Local SEO — March 2025", key="gen_batch_name")

        gen_desc = st.text_area("Batch Description (optional)", height=60, key="gen_desc")

        if st.button("🚀 Generate Batch (Stub Pages)", key="btn_gen_batch", type="primary"):
            if not gen_service or not gen_keyword:
                st.error("Please provide a service name and primary keyword.")
            else:
                bname = gen_batch_name or f"{gen_service} Batch — {gen_keyword}"
                with st.spinner(f"Generating {gen_count} pages…"):
                    stubs = _mgr.generate_stub_pages(gen_service, gen_keyword, count=int(gen_count))
                    batch_id = _mgr.create_batch_from_pages(bname, stubs, batch_description=gen_desc)
                st.session_state.factory_batch_id = batch_id
                st.session_state.factory_selected_pages = []
                st.success(
                    f"✅ Batch '{bname}' created with {gen_count} pages — all in **Pending Review**."
                )
                st.rerun()

        st.info(
            "💡 For production LLM-generated content, run the CLI:\n"
            "```bash\npython generator.py batch --pages-file examples/batch_pages.json "
            "--output-dir output/ --openai-key $OPENAI_API_KEY\n```"
        )

    # ── Batch selector ────────────────────────────────────────────────────────
    batches = _mgr.list_batches()
    if batches:
        st.subheader("📦 Select Active Batch")
        batch_labels = [f"#{b['id']} — {b['name']} ({b['total_pages']} pages)" for b in batches]
        current_idx = 0
        if st.session_state.factory_batch_id:
            ids = [b["id"] for b in batches]
            if st.session_state.factory_batch_id in ids:
                current_idx = ids.index(st.session_state.factory_batch_id)
        chosen_label = st.selectbox("Active Batch:", batch_labels, index=current_idx, key="batch_selector")
        chosen_batch = batches[batch_labels.index(chosen_label)]
        if chosen_batch["id"] != st.session_state.factory_batch_id:
            st.session_state.factory_batch_id = chosen_batch["id"]
            st.session_state.factory_selected_pages = []
            st.rerun()

    # ── Main dashboard (only when a batch is selected) ─────────────────────
    if st.session_state.factory_batch_id:
        batch = _mgr.get_batch(st.session_state.factory_batch_id)
        if not batch:
            st.warning("Batch not found. Please generate or select a batch.")
        else:
            # ── Progress bar ──────────────────────────────────────────────
            total = max(batch["total_pages"], 1)
            prog_pending = batch["pages_pending"] / total
            prog_approved = batch["pages_approved"] / total
            prog_deployed = batch["pages_deployed"] / total

            st.subheader(f"📊 {batch['name']}")
            pcol1, pcol2, pcol3, pcol4 = st.columns(4)
            pcol1.metric("Total Pages", batch["total_pages"])
            pcol2.metric("🔴 Pending", batch["pages_pending"])
            pcol3.metric("🟢 Approved", batch["pages_approved"])
            pcol4.metric("🔵 Deployed", batch["pages_deployed"])

            st.progress(prog_approved + prog_deployed, text=f"Progress: {round((prog_approved + prog_deployed) * 100)}% approved/deployed")

            # ── Tier 2 & 3 layout: canvas + sidebar ──────────────────────
            canvas_col, sidebar_col = st.columns([3, 1])

            # ── Right sidebar: Batch Style Editor ────────────────────────
            with sidebar_col:
                with st.container(border=True):
                    st.subheader("🎨 Batch Style Editor")
                    n_sel = len(st.session_state.factory_selected_pages)
                    st.caption(
                        f"{'No pages' if n_sel == 0 else f'{n_sel} page(s)'} selected"
                    )

                    # Global template
                    global_tpl_label = st.selectbox(
                        "Apply Template to Selection",
                        ["— keep individual —"] + _TEMPLATE_LABELS,
                        key="sidebar_tpl",
                    )

                    # Brand color
                    brand_color_options = ["blue", "indigo", "purple", "green", "red", "orange", "teal", "slate"]
                    brand_color = st.selectbox("Brand Color", brand_color_options, key="sidebar_color")

                    # CTA link
                    cta_link = st.text_input("Global CTA Link", placeholder="https://yourdomain.com/contact", key="sidebar_cta")

                    # Font family (informational only — applied via preview_state)
                    font_family = st.selectbox(
                        "Font Family",
                        ["Default (system)", "Inter", "Georgia", "Roboto", "Lato"],
                        key="sidebar_font",
                    )

                    if st.button("✅ Apply to Selected", key="apply_style", use_container_width=True, type="primary"):
                        if not st.session_state.factory_selected_pages:
                            st.warning("Select at least one page first.")
                        else:
                            chosen_tpl_key = None
                            if global_tpl_label != "— keep individual —":
                                chosen_tpl_key = _TEMPLATE_KEYS[_TEMPLATE_LABELS.index(global_tpl_label)]
                            count = _mgr.apply_batch_style(
                                st.session_state.factory_selected_pages,
                                template=chosen_tpl_key,
                                brand_color=brand_color,
                                cta_link=cta_link or None,
                                font_family=font_family if font_family != "Default (system)" else None,
                            )
                            st.success(f"Applied to {count} page(s)!")
                            st.rerun()

                    st.divider()

                    # Bulk status controls
                    st.caption("**Bulk Status**")
                    bs1, bs2 = st.columns(2)
                    with bs1:
                        if st.button("✅ Approve All Selected", key="bulk_approve", use_container_width=True):
                            if st.session_state.factory_selected_pages:
                                _mgr.approve_pages(st.session_state.factory_selected_pages)
                                st.rerun()
                            else:
                                st.warning("Select pages first.")
                    with bs2:
                        if st.button("🔍 Mark Reviewed", key="bulk_review", use_container_width=True):
                            if st.session_state.factory_selected_pages:
                                _mgr.review_pages(st.session_state.factory_selected_pages)
                                st.rerun()
                            else:
                                st.warning("Select pages first.")

                    st.divider()

                    # Select All / Clear
                    all_pages_in_batch = _mgr.list_pages(batch_id=st.session_state.factory_batch_id)
                    all_ids = [p["id"] for p in all_pages_in_batch]
                    sa1, sa2 = st.columns(2)
                    with sa1:
                        if st.button("☑ Select All", key="sel_all", use_container_width=True):
                            st.session_state.factory_selected_pages = all_ids
                            st.rerun()
                    with sa2:
                        if st.button("✕ Clear", key="sel_clear", use_container_width=True):
                            st.session_state.factory_selected_pages = []
                            st.rerun()

                    st.divider()

                    # Deploy batch button
                    n_approved = batch["pages_approved"]
                    deploy_disabled = n_approved == 0
                    if deploy_disabled:
                        st.caption("🔒 Deploy requires at least 1 Approved page.")
                    if st.button(
                        f"🚀 Deploy Batch ({n_approved} approved)",
                        key="deploy_btn",
                        disabled=deploy_disabled,
                        use_container_width=True,
                        type="primary",
                    ):
                        st.session_state._deploy_confirm = True
                        st.rerun()

                    if getattr(st.session_state, "_deploy_confirm", False):
                        st.warning(
                            f"You are about to publish **{n_approved} page(s)** to production.\n\n"
                            "This action cannot be undone."
                        )
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            if st.button("✅ Confirm Deploy", key="confirm_deploy", type="primary"):
                                manifest = _mgr.deploy_batch(st.session_state.factory_batch_id)
                                st.session_state.factory_deploy_manifest = manifest
                                st.session_state._deploy_confirm = False
                                st.rerun()
                        with dc2:
                            if st.button("✕ Cancel", key="cancel_deploy"):
                                st.session_state._deploy_confirm = False
                                st.rerun()

            # ── Batch Canvas (grid view) ──────────────────────────────────
            with canvas_col:
                # Filter controls
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    filter_status = st.selectbox(
                        "Filter by Status",
                        ["All"] + [s.replace("_", " ").title() for s in _STATUS_ORDER],
                        key="filter_status",
                    )
                with fc2:
                    filter_tpl = st.selectbox(
                        "Filter by Template",
                        ["All"] + _TEMPLATE_LABELS,
                        key="filter_tpl",
                    )
                with fc3:
                    sort_by = st.selectbox(
                        "Sort by",
                        ["Created (oldest first)", "Quality Score ↓", "Title A→Z", "Status"],
                        key="sort_pages",
                    )

                # Fetch + filter
                status_filter_val = None
                if filter_status != "All":
                    status_filter_val = _STATUS_ORDER[
                        [s.replace("_", " ").title() for s in _STATUS_ORDER].index(filter_status)
                    ]
                tpl_filter_val = None
                if filter_tpl != "All":
                    tpl_filter_val = _TEMPLATE_KEYS[_TEMPLATE_LABELS.index(filter_tpl)]

                pages = _mgr.list_pages(
                    batch_id=st.session_state.factory_batch_id,
                    status=status_filter_val,
                    template=tpl_filter_val,
                )

                # Sort
                if sort_by == "Quality Score ↓":
                    pages = sorted(
                        pages,
                        key=lambda p: (p.get("quality_scores") or {}).get("overall", 0),
                        reverse=True,
                    )
                elif sort_by == "Title A→Z":
                    pages = sorted(pages, key=lambda p: p["title"].lower())
                elif sort_by == "Status":
                    pages = sorted(pages, key=lambda p: _STATUS_ORDER.index(p["status"]))

                st.caption(f"Showing {len(pages)} page(s)")

                if not pages:
                    st.info("No pages match the current filters.")
                else:
                    # 3-column grid
                    rows = [pages[i:i+3] for i in range(0, len(pages), 3)]
                    for row in rows:
                        cols = st.columns(3)
                        for page, col in zip(row, cols):
                            _render_batch_tile(page, col)
    else:
        st.info("👆 Generate a new batch above or select an existing batch to get started.")
