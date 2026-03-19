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
from src.database import Database
from src.staging_review import StagingReviewManager

st.set_page_config(
    page_title="Sturdy Broccoli — Enterprise SEO Content Factory",
    page_icon="🥦",
    layout="wide",
)

st.title("🥦 Sturdy Broccoli — Enterprise SEO Content Factory")

# ---------------------------------------------------------------------------
# Shared database / manager (cached so it's initialised once per session)
# ---------------------------------------------------------------------------


@st.cache_resource
def _get_manager() -> StagingReviewManager:
    db = Database()
    db.init_schema()
    return StagingReviewManager(db)


_mgr = _get_manager()

tab_prompt, tab_hub, tab_competitor, tab_multiformat, tab_template, tab_batch, tab_deploy = st.tabs([
    "📝 Prompt Generator",
    "🕸️ Hub & Spoke",
    "🔍 Competitor Analysis",
    "📢 Multi-Format",
    "🏗️ Landing Page Templates",
    "📋 Batch Manager",
    "🚀 Deployer",
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
# Helpers shared across Batch Manager and Deployer tabs
# ---------------------------------------------------------------------------

_QUALITY_BADGE_THRESHOLDS = {
    "authority":   ("Authority",   "\U0001f7e2", "\U0001f7e1", "\U0001f534"),
    "semantic":    ("Semantic",    "\U0001f7e2", "\U0001f7e1", "\U0001f534"),
    "structure":   ("Structure",   "\U0001f7e2", "\U0001f7e1", "\U0001f534"),
    "engagement":  ("Engagement",  "\U0001f535", "\U0001f7e1", "\U0001f534"),
    "uniqueness":  ("Uniqueness",  "\U0001f7e2", "\U0001f7e1", "\U0001f534"),
}

_STATUS_EMOJI = {
    "draft":          "\U0001f4dd",
    "approved":       "\u2705",
    "needs_revision": "\u26a0\ufe0f",
    "rejected":       "\u274c",
    "deployed":       "\U0001f680",
}


def _quality_badge(metric: str, score: float) -> str:
    label, high, mid, low = _QUALITY_BADGE_THRESHOLDS.get(
        metric, (metric.title(), "\U0001f7e2", "\U0001f7e1", "\U0001f534")
    )
    icon = high if score >= 90 else (mid if score >= 70 else low)
    return f"{icon} {label}: {score:.0f}/100"


def _render_page_tile(page: dict, selected_ids: list, mgr: object) -> None:
    page_id = page["id"]
    qs = page.get("quality_scores") or {}

    col_check, col_title = st.columns([1, 10])
    with col_check:
        checked = st.checkbox(
            "",
            value=page_id in selected_ids,
            key=f"sel_{page_id}",
            label_visibility="collapsed",
        )
        if checked and page_id not in selected_ids:
            selected_ids.append(page_id)
        elif not checked and page_id in selected_ids:
            selected_ids.remove(page_id)

    with col_title:
        status_icon = _STATUS_EMOJI.get(page.get("review_status", "draft"), "\U0001f4dd")
        st.markdown(f"**{status_icon} {page.get('title', 'Untitled')}**")

    h1 = page.get("h1_content") or ""
    if h1:
        st.caption(f'H1: "{h1[:80]}{"..." if len(h1) > 80 else ""}"')

    if qs:
        badge_cols = st.columns(5)
        for idx, metric in enumerate(
            ["authority", "semantic", "structure", "engagement", "uniqueness"]
        ):
            score = qs.get(metric, 0)
            if score:
                badge_cols[idx].caption(_quality_badge(metric, score))

    meta_col1, meta_col2, meta_col3 = st.columns(3)
    with meta_col1:
        if page.get("competitor_benchmark"):
            st.caption(f"\U0001f4ca Benchmarked: {page['competitor_benchmark']}")
    with meta_col2:
        if page.get("template_display_name"):
            st.caption(f"\U0001f3d7\ufe0f Template: {page['template_display_name']}")
    with meta_col3:
        overall = (qs or {}).get("overall", 0)
        if overall:
            st.caption(f"\u2b50 Overall: {overall:.0f}/100")

    act_col1, act_col2, act_col3, act_col4 = st.columns([3, 1, 1, 1])
    with act_col1:
        status_options = ["draft", "approved", "needs_revision", "rejected"]
        current = page.get("review_status", "draft")
        idx = status_options.index(current) if current in status_options else 0
        new_status = st.selectbox(
            "Status",
            options=status_options,
            index=idx,
            key=f"status_{page_id}",
            label_visibility="collapsed",
        )
        if new_status != current:
            if st.button("Apply", key=f"apply_status_{page_id}"):
                mgr.update_page_status(page_id, new_status)
                st.rerun()

    with act_col2:
        if st.button("\u270f\ufe0f Edit", key=f"edit_{page_id}"):
            st.session_state["preview_page_id"] = page_id
            st.session_state["preview_mode"] = "edit"

    with act_col3:
        if st.button("\U0001f441\ufe0f View", key=f"view_{page_id}"):
            st.session_state["preview_page_id"] = page_id
            st.session_state["preview_mode"] = "view"

    with act_col4:
        if st.button("\U0001f5d1\ufe0f", key=f"del_{page_id}", help="Remove from batch"):
            st.session_state[f"confirm_delete_{page_id}"] = True

    if st.session_state.get(f"confirm_delete_{page_id}"):
        st.warning(f"Delete **{page.get('title')}**?")
        d_c1, d_c2 = st.columns(2)
        with d_c1:
            if st.button("Yes, delete", key=f"confirm_del_yes_{page_id}"):
                mgr._db.execute("DELETE FROM content_pages WHERE id = ?", (page_id,))
                mgr._db.execute(
                    "UPDATE batches SET total_pages = MAX(0, total_pages - 1) WHERE id = ?",
                    (page.get("batch_id"),),
                )
                mgr._db.commit()
                st.session_state.pop(f"confirm_delete_{page_id}", None)
                st.rerun()
        with d_c2:
            if st.button("Cancel", key=f"confirm_del_no_{page_id}"):
                st.session_state.pop(f"confirm_delete_{page_id}", None)
                st.rerun()

    st.divider()


# ---------------------------------------------------------------------------
# Tab 6: Batch Manager
# ---------------------------------------------------------------------------

with tab_batch:
    import random as _random

    st.header("\U0001f4cb Batch Manager")
    st.caption(
        "Review, approve, and manage generated content pages before deployment. "
        "Every page must pass human review \u2014 no auto-publish."
    )

    for _k, _v in [
        ("bm_selected_ids", []),
        ("preview_page_id", None),
        ("preview_mode", "view"),
    ]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    with st.sidebar:
        st.markdown("### \U0001f4e6 Batches")
        batches = _mgr.list_batches()
        batch_names = [f"{b['name']} (#{b['id']})" for b in batches]

        if batches:
            selected_batch_label = st.selectbox(
                "Select Batch", batch_names, key="bm_batch_select"
            )
            selected_batch_idx = batch_names.index(selected_batch_label)
            active_batch = batches[selected_batch_idx]
        else:
            active_batch = None

        st.markdown("---")
        st.markdown("### \u2795 New Batch")
        new_batch_name = st.text_input("Batch name", key="bm_new_batch_name")
        new_batch_desc = st.text_input("Description (optional)", key="bm_new_batch_desc")
        if st.button("Create Batch", key="bm_create_batch"):
            if new_batch_name.strip():
                _mgr.create_batch(new_batch_name.strip(), new_batch_desc.strip())
                st.success(f"Batch '{new_batch_name}' created!")
                st.rerun()
            else:
                st.error("Batch name is required.")

        st.markdown("---")
        if active_batch:
            st.markdown("### Add Demo Page")
            if st.button("Add sample page", key="bm_add_sample"):
                _services = [
                    "NFT Consulting", "Local SEO", "Digital PR",
                    "LinkedIn Marketing", "Capital Raise Advisory",
                    "Investor Marketing", "GEO / AI SEO", "E-commerce SEO",
                ]
                _svc = _random.choice(_services)
                _mgr.add_page(
                    batch_id=active_batch["id"],
                    title=f"{_svc} Services",
                    h1_content=f"Expert {_svc} for Growth-Stage Companies",
                    meta_title=f"{_svc} | CrowdCreate",
                    meta_description=(
                        f"CrowdCreate delivers results-driven {_svc} "
                        "tailored to your market."
                    ),
                    content_markdown=(
                        f"## What We Do\nWe provide {_svc}.\n\n"
                        "## Why Choose Us\nProven track record."
                    ),
                    template_name=_random.choice(
                        ["modern_saas", "professional_service", "enterprise"]
                    ),
                    quality_scores={
                        "authority":   _random.randint(70, 98),
                        "semantic":    _random.randint(65, 95),
                        "structure":   _random.randint(75, 99),
                        "engagement":  _random.randint(60, 90),
                        "uniqueness":  _random.randint(55, 90),
                    },
                    competitor_benchmark="consensys.net",
                )
                st.rerun()

    if active_batch is None:
        st.info("Create a batch using the sidebar to get started.")
    else:
        b = _mgr.get_batch(active_batch["id"])
        if b is None:
            st.warning("Batch not found.")
        else:
            st.subheader(f"\U0001f5c2\ufe0f {b['name']}")
            if b.get("description"):
                st.caption(b["description"])

            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            mc1.metric("Total Pages",              b.get("total_pages", 0))
            mc2.metric("\u2705 Approved",          b.get("pages_approved", 0))
            mc3.metric("\U0001f4dd Draft / Review", b.get("pages_draft", 0))
            mc4.metric("\U0001f680 Deployed",      b.get("pages_deployed", 0))
            mc5.metric("\u274c Rejected",          b.get("pages_rejected", 0))

            _total = b.get("total_pages", 1) or 1
            _approved = b.get("pages_approved", 0)
            st.progress(
                _approved / _total,
                text=f"Approval progress: {_approved}/{_total}",
            )

            st.markdown("---")

            fc1, fc2, fc3, fc4 = st.columns(4)
            with fc1:
                status_filter = st.selectbox(
                    "Filter by status",
                    ["All", "draft", "approved", "needs_revision", "rejected", "deployed"],
                    key="bm_status_filter",
                )
            with fc2:
                sort_by = st.selectbox(
                    "Sort by",
                    ["created_at", "title", "review_status", "last_modified_at"],
                    key="bm_sort_by",
                )
            with fc3:
                sort_dir = st.radio(
                    "Order", ["ASC", "DESC"], horizontal=True, key="bm_sort_dir"
                )
            with fc4:
                min_q = st.number_input(
                    "Min quality score",
                    min_value=0,
                    max_value=100,
                    value=0,
                    key="bm_min_quality",
                )

            pages = _mgr.get_batch_pages(
                b["id"],
                status_filter=status_filter if status_filter != "All" else None,
                sort_by=sort_by,
                sort_dir=sort_dir,
                min_quality=float(min_q) if min_q > 0 else None,
            )

            selected_ids: list = st.session_state["bm_selected_ids"]

            sel_c1, sel_c2, sel_c3 = st.columns([2, 2, 6])
            with sel_c1:
                if st.checkbox("Select all", key="bm_select_all"):
                    st.session_state["bm_selected_ids"] = [p["id"] for p in pages]
                    selected_ids = st.session_state["bm_selected_ids"]
            with sel_c2:
                if st.button("Deselect all", key="bm_deselect_all"):
                    st.session_state["bm_selected_ids"] = []
                    selected_ids = []
            with sel_c3:
                if selected_ids:
                    st.info(f"**{len(selected_ids)} page(s) selected**")

            st.markdown("---")

            if not pages:
                st.info(
                    "No pages match the current filters. "
                    "Add sample pages using the sidebar."
                )
            else:
                grid_cols = st.columns(2)
                for _i, _page in enumerate(pages):
                    with grid_cols[_i % 2]:
                        _render_page_tile(_page, selected_ids, _mgr)

            st.session_state["bm_selected_ids"] = selected_ids

            # Preview / edit modal
            preview_id = st.session_state.get("preview_page_id")
            if preview_id:
                preview_page = _mgr.get_page(preview_id)
                if preview_page:
                    st.markdown("---")
                    _mode_lbl = (
                        "\u270f\ufe0f Editing"
                        if st.session_state["preview_mode"] == "edit"
                        else "\U0001f441\ufe0f Previewing"
                    )
                    st.subheader(f"{_mode_lbl}: {preview_page.get('title')}")

                    pm_tab_edit, pm_tab_preview, pm_tab_arch = st.tabs(
                        [
                            "\U0001f4dd Content Editor",
                            "\U0001f5bc\ufe0f Live Preview",
                            "\U0001f578\ufe0f Content Architecture",
                        ]
                    )

                    with pm_tab_edit:
                        e_c1, e_c2 = st.columns(2)
                        with e_c1:
                            new_h1 = st.text_input(
                                "H1",
                                value=preview_page.get("h1_content") or "",
                                key=f"ed_h1_{preview_id}",
                            )
                            new_meta_title = st.text_input(
                                "Meta Title",
                                value=preview_page.get("meta_title") or "",
                                key=f"ed_mt_{preview_id}",
                            )
                            new_meta_desc = st.text_area(
                                "Meta Description",
                                value=preview_page.get("meta_description") or "",
                                height=80,
                                key=f"ed_md_{preview_id}",
                            )
                        with e_c2:
                            _templates = _mgr.list_templates()
                            _tmpl_names = [t["name"] for t in _templates]
                            _tmpl_display = [t["display_name"] for t in _templates]
                            _cur_tmpl = preview_page.get("template_name") or "modern_saas"
                            _tmpl_idx = (
                                _tmpl_names.index(_cur_tmpl)
                                if _cur_tmpl in _tmpl_names
                                else 0
                            )
                            new_tmpl = st.selectbox(
                                "Template",
                                options=_tmpl_names,
                                format_func=lambda n: _tmpl_display[_tmpl_names.index(n)],
                                index=_tmpl_idx,
                                key=f"ed_tmpl_{preview_id}",
                            )
                            brand_color = st.color_picker(
                                "Brand Colour Override",
                                value=preview_page.get("brand_color_override") or "#2563EB",
                                key=f"ed_color_{preview_id}",
                            )
                            cta_text = st.text_input(
                                "CTA Text",
                                value=preview_page.get("cta_text_override") or "Get Started Today",
                                key=f"ed_cta_text_{preview_id}",
                            )
                            cta_link = st.text_input(
                                "CTA Link",
                                value=preview_page.get("cta_link_override") or "#contact",
                                key=f"ed_cta_link_{preview_id}",
                            )

                        new_content = st.text_area(
                            "Content (Markdown)",
                            value=preview_page.get("content_markdown") or "",
                            height=250,
                            key=f"ed_content_{preview_id}",
                        )

                        sc1, sc2, sc3 = st.columns(3)
                        with sc1:
                            if st.button("\U0001f4be Save Draft", key=f"save_{preview_id}"):
                                _mgr.update_page_content(
                                    preview_id,
                                    h1_content=new_h1,
                                    meta_title=new_meta_title,
                                    meta_description=new_meta_desc,
                                    content_markdown=new_content,
                                    changed_by="user",
                                    change_reason="UI edit",
                                )
                                _mgr.switch_template(preview_id, new_tmpl)
                                _mgr.apply_branding_to_pages(
                                    [preview_id],
                                    brand_color=brand_color,
                                    cta_text=cta_text,
                                    cta_link=cta_link,
                                )
                                st.success("Saved!")
                                st.rerun()
                        with sc2:
                            if st.button("\u21a9\ufe0f Revert", key=f"revert_{preview_id}"):
                                _revs = _mgr.get_page_revisions(preview_id)
                                if _revs:
                                    _mgr.update_page_content(
                                        preview_id,
                                        content_markdown=_revs[0]["content_markdown"],
                                        changed_by="user",
                                        change_reason="Reverted",
                                    )
                                    st.success("Reverted to last saved version.")
                                    st.rerun()
                                else:
                                    st.warning("No revision history yet.")
                        with sc3:
                            if st.button(
                                "\u2716\ufe0f Close Editor", key=f"close_{preview_id}"
                            ):
                                st.session_state["preview_page_id"] = None
                                st.rerun()

                    with pm_tab_preview:
                        import streamlit.components.v1 as _components
                        from src.staging_review import _render_page_html as _rph

                        _tmpl_row = _mgr.get_template(
                            preview_page.get("template_name") or "modern_saas"
                        )
                        _tmpl_html = (
                            _tmpl_row.get("template_html", "") if _tmpl_row else ""
                        )
                        _rendered = _rph(preview_page, _tmpl_html)
                        _full_html = (
                            "<!DOCTYPE html><html lang='en'><head>"
                            "<meta charset='UTF-8'>"
                            "<script src='https://cdn.tailwindcss.com'></script>"
                            f"</head><body>{_rendered}</body></html>"
                        )
                        st.radio(
                            "Preview device",
                            ["Desktop (1200px)", "Tablet (768px)", "Mobile (375px)"],
                            horizontal=True,
                            key=f"device_{preview_id}",
                        )
                        _components.html(_full_html, height=600, scrolling=True)

                    with pm_tab_arch:
                        st.subheader("\U0001f578\ufe0f Hub & Spoke Architecture")
                        _arch = _mgr.validate_hub_spoke_links(preview_page["batch_id"])

                        _hub_e = next(
                            (h for h in _arch["hub_pages"] if h["id"] == preview_id), None
                        )
                        _spk_e = next(
                            (s for s in _arch["spoke_pages"] if s["id"] == preview_id), None
                        )

                        if _hub_e:
                            st.success(
                                f"\U0001f3af **HUB**: {preview_page['title']} "
                                f"({_hub_e['spoke_count']} spoke(s))"
                            )
                        elif _spk_e:
                            _hub_pg = _mgr.get_page(_spk_e["hub_id"])
                            _hub_t = (
                                _hub_pg["title"] if _hub_pg else f"Page {_spk_e['hub_id']}"
                            )
                            st.info(f"\U0001f4cc **SPOKE** \u2192 Hub: {_hub_t}")
                        else:
                            st.warning(
                                "This page is not part of a hub-and-spoke cluster."
                            )

                        if _arch["link_statuses"]:
                            st.markdown("**Internal Link Status:**")
                            for _ls in _arch["link_statuses"]:
                                _li = "\u2705" if _ls["status"] == "linked" else "\u26a0\ufe0f"
                                st.markdown(
                                    f"{_li} `{_ls['from_title']}` \u2192 "
                                    f"`{_ls['to_title']}` "
                                    f"({_ls['direction']}, anchor: *{_ls['anchor']}*)"
                                )

                        if _arch["issues"]:
                            st.markdown("**\u26a0\ufe0f Issues:**")
                            for _iss in _arch["issues"]:
                                _si = (
                                    "\U0001f534"
                                    if _iss["severity"] == "red"
                                    else "\U0001f7e1"
                                )
                                st.markdown(f"{_si} {_iss['message']}")

                        if _arch["silo_violations"]:
                            st.markdown("**\U0001f534 SILO Violations:**")
                            for _sv in _arch["silo_violations"]:
                                st.markdown(f"\U0001f534 {_sv['message']}")

                        if _arch["is_healthy"]:
                            st.success(
                                "\u2705 Link structure is healthy \u2014 no SILO violations."
                            )

            # Batch actions (2+ pages selected)
            if len(selected_ids) >= 2:
                st.markdown("---")
                with st.expander(
                    f"\u26a1 BATCH ACTIONS \u2014 {len(selected_ids)} pages selected",
                    expanded=True,
                ):
                    st.subheader("\U0001f3a8 Global Styles")
                    ba_c1, ba_c2 = st.columns(2)
                    with ba_c1:
                        batch_color = st.color_picker(
                            "Brand Primary Colour", value="#2563EB", key="ba_color"
                        )
                        st.caption("\u2139\ufe0f Affects CTA buttons and H1 underlines")
                        batch_cta_text = st.text_input(
                            "Global CTA Text", value="Get Started Today", key="ba_cta_text"
                        )
                        batch_cta_link = st.text_input(
                            "Global CTA Link",
                            value="https://example.com/contact",
                            key="ba_cta_link",
                        )
                    with ba_c2:
                        batch_font = st.selectbox(
                            "Font Family",
                            ["Poppins", "Inter", "Playfair Display", "Georgia", "Roboto"],
                            key="ba_font",
                        )
                        batch_logo = st.text_input(
                            "Logo URL (optional)",
                            placeholder="https://cdn.example.com/logo.png",
                            key="ba_logo",
                        )

                    if st.button(
                        "\u2728 Apply Branding to Selected", key="ba_apply_branding"
                    ):
                        _mgr.apply_branding_to_pages(
                            selected_ids,
                            brand_color=batch_color,
                            logo_url=batch_logo or None,
                            cta_text=batch_cta_text,
                            cta_link=batch_cta_link,
                        )
                        _mgr.update_batch_branding(
                            b["id"],
                            primary_color=batch_color,
                            font_family=batch_font,
                            global_cta_text=batch_cta_text,
                            global_cta_link=batch_cta_link,
                            logo_url=batch_logo or None,
                        )
                        st.success(
                            f"\u2705 Branding applied to {len(selected_ids)} pages!"
                        )
                        st.rerun()

                    st.markdown("---")
                    st.subheader("\U0001f4cb Bulk Status")
                    bulk_status = st.selectbox(
                        "Set status for all selected",
                        ["approved", "needs_revision", "rejected", "draft"],
                        key="ba_bulk_status",
                    )
                    bulk_notes = st.text_input(
                        "Reviewer notes (optional)", key="ba_bulk_notes"
                    )
                    if st.button("Apply Status to Selected", key="ba_apply_status"):
                        _mgr.bulk_update_status(
                            selected_ids, bulk_status, reviewer_notes=bulk_notes
                        )
                        st.success(
                            f"\u2705 Marked {len(selected_ids)} page(s) as '{bulk_status}'."
                        )
                        st.session_state["bm_selected_ids"] = []
                        st.rerun()

                    st.markdown("---")
                    st.subheader("\u2b07\ufe0f Export Selected")
                    if st.button(
                        "\U0001f4e6 Export as ZIP (HTML + CSV)", key="ba_export"
                    ):
                        _exp = _mgr.deploy_pages(selected_ids)
                        st.download_button(
                            label=f"\u2b07\ufe0f Download {_exp['page_count']} pages",
                            data=_exp["zip_bytes"],
                            file_name="batch_export.zip",
                            mime="application/zip",
                            key="ba_download",
                        )
                        st.success(
                            f"\u2705 {_exp['page_count']} page(s) exported "
                            "and marked as deployed."
                        )
                        st.session_state["bm_selected_ids"] = []
                        st.rerun()


# ---------------------------------------------------------------------------
# Tab 7: Deployer
# ---------------------------------------------------------------------------

with tab_deploy:
    st.header("\U0001f680 Deployer")
    st.caption(
        "Run pre-flight checks and deploy approved pages. "
        "No page reaches \u2018deployed\u2019 without explicit approval."
    )

    _dep_batches = _mgr.list_batches()
    if not _dep_batches:
        st.info(
            "No batches found. Create a batch in the Batch Manager tab first."
        )
    else:
        _dep_batch_names = [f"{b['name']} (#{b['id']})" for b in _dep_batches]
        _dep_batch_label = st.selectbox(
            "Select Batch to Deploy", _dep_batch_names, key="dep_batch_select"
        )
        _dep_batch_idx = _dep_batch_names.index(_dep_batch_label)
        _dep_batch = _dep_batches[_dep_batch_idx]

        _app_pages = _mgr.get_batch_pages(_dep_batch["id"], status_filter="approved")

        st.subheader(f"Approved pages ready to deploy: {len(_app_pages)}")

        if not _app_pages:
            st.warning(
                "No approved pages in this batch. "
                "Go to Batch Manager and approve pages before deploying."
            )
        else:
            _dep_ids = [p["id"] for p in _app_pages]

            st.markdown("### \u2705 Pre-flight Checklist")
            _pf = _mgr.run_preflight_checks(_dep_ids)
            for _chk in _pf["checks"]:
                _ci = "\u2705" if _chk["passed"] else "\u274c"
                st.markdown(f"{_ci} **{_chk['name']}**")
                st.caption(f"  {_chk['detail']}")

            if _pf["blocking_issues"]:
                st.error(
                    "\U0001f6ab Cannot deploy \u2014 blocking issues:\n"
                    + "\n".join(f"\u2022 {i}" for i in _pf["blocking_issues"])
                )
            else:
                st.success("\U0001f389 All pre-flight checks passed!")

            st.markdown("---")
            st.markdown("### \U0001f4cb Deployment Summary")
            st.info(
                f"You are about to publish **{len(_app_pages)} page(s)** "
                f"from batch **\u2018{_dep_batch['name']}\u2019**."
            )

            with st.expander("Pages to be deployed"):
                for _dp in _app_pages:
                    _dqs = _dp.get("quality_scores") or {}
                    st.markdown(
                        f"- **{_dp['title']}**  "
                        f"*(Overall: {_dqs.get('overall', 'N/A')}/100)*"
                    )

            _dep_by = st.text_input("Your name (for audit trail)", key="dep_deployed_by")

            if st.button(
                "\U0001f680 Deploy All Approved Pages",
                key="dep_deploy_btn",
                disabled=not _pf["passed"],
            ):
                with st.spinner(f"Deploying {len(_dep_ids)} pages\u2026"):
                    _dr = _mgr.deploy_pages(_dep_ids, deployed_by=_dep_by)
                st.success(
                    f"\u2705 Successfully deployed {_dr['page_count']} page(s)!"
                )
                st.download_button(
                    label="\u2b07\ufe0f Download Deployment ZIP (HTML + metadata CSV)",
                    data=_dr["zip_bytes"],
                    file_name=(
                        f"deployment_{_dep_batch['name'].replace(' ', '_')}.zip"
                    ),
                    mime="application/zip",
                    key="dep_download",
                )
                st.balloons()
