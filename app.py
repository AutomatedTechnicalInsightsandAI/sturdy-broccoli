"""
app.py — Decoupled SEO Site Factory: Staging Canvas UI

Architecture:
  - Data-First: pages are JSON objects stored in SQLite via Database
  - Quality Scoring: 5-metric engine (Authority, Semantic, Structure, Engagement, Uniqueness)
  - Staging Canvas: grid view of page tiles with quality badges
  - Preview/Edit modal: split-screen editor + live preview + quality breakdown
  - Batch actions: global style editor, bulk status changes
  - Deploy workflow: preflight checks + human gate
"""
from __future__ import annotations

import csv
import io
import json
import re

import streamlit as st

from src.database import Database
from src.quality_scorer import QualityScorer

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="🥦 SEO Site Factory",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------

@st.cache_resource
def get_db() -> Database:
    return Database()


@st.cache_resource
def get_scorer() -> QualityScorer:
    return QualityScorer()


db = get_db()
scorer = get_scorer()

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults = {
        "active_batch_id": None,
        "preview_page_id": None,
        "selected_page_ids": [],
        "canvas_sort": "created_at",
        "canvas_filter": "All",
        "show_create_batch": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

_SCORE_COLORS = {
    "green":  "#16a34a",
    "yellow": "#ca8a04",
    "orange": "#ea580c",
    "red":    "#dc2626",
}

_STATUS_COLORS = {
    "draft":          "#6b7280",
    "reviewed":       "#2563eb",
    "approved":       "#16a34a",
    "needs_revision": "#ea580c",
    "rejected":       "#dc2626",
    "deployed":       "#7c3aed",
}

_STATUS_EMOJI = {
    "draft":          "📝",
    "reviewed":       "👁️",
    "approved":       "✅",
    "needs_revision": "🔄",
    "rejected":       "❌",
    "deployed":       "🚀",
}


def _score_pill(score: int | None, label: str) -> str:
    """Return an HTML badge for a score."""
    if score is None:
        return f'<span style="color:#9ca3af">—</span>'
    color = _SCORE_COLORS[QualityScorer.color_for_score(score)]
    return f'<span style="color:{color};font-weight:700">{label}:{score}</span>'


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

st.title("🥦 SEO Site Factory")

tab_canvas, tab_generate, tab_deploy = st.tabs([
    "📋 Staging Canvas",
    "⚙️ Generate",
    "🚀 Deploy",
])

# ============================================================================
# TAB 1: STAGING CANVAS
# ============================================================================

with tab_canvas:

    # ── Batch selector ──────────────────────────────────────────────────────
    batches = db.list_batches()

    col_batch, col_new = st.columns([4, 1])
    with col_batch:
        if batches:
            batch_options = {f"#{b['id']} — {b['name']}": b["id"] for b in batches}
            # Preserve active selection
            active_name = next(
                (k for k, v in batch_options.items() if v == st.session_state.active_batch_id),
                list(batch_options.keys())[0],
            )
            chosen = st.selectbox("Active Batch", list(batch_options.keys()), index=list(batch_options.keys()).index(active_name))
            st.session_state.active_batch_id = batch_options[chosen]
        else:
            st.info("No batches yet — use the **Generate** tab to create your first batch.")

    with col_new:
        st.write("")  # spacing
        if st.button("＋ New Batch"):
            st.session_state.show_create_batch = True

    # Inline batch creation form
    if st.session_state.show_create_batch:
        with st.form("create_batch_form"):
            new_name = st.text_input("Batch Name", placeholder="Client A – March Run")
            new_desc = st.text_input("Description")
            new_client = st.text_input("Client ID")
            col_submit, col_cancel = st.columns(2)
            with col_submit:
                submitted = st.form_submit_button("Create Batch")
            with col_cancel:
                cancelled = st.form_submit_button("Cancel")
            if submitted and new_name:
                bid = db.create_batch(new_name, description=new_desc, client_id=new_client)
                st.session_state.active_batch_id = bid
                st.session_state.show_create_batch = False
                st.rerun()
            if cancelled:
                st.session_state.show_create_batch = False
                st.rerun()

    if not st.session_state.active_batch_id:
        st.stop()

    batch_id = st.session_state.active_batch_id
    batch_info = db.get_batch(batch_id)
    if not batch_info:
        st.error("Batch not found.")
        st.stop()

    # ── Batch header ────────────────────────────────────────────────────────
    st.markdown(
        f"**Batch:** {batch_info['name']} &nbsp;|&nbsp; "
        f"Total: **{batch_info['total_pages']}** &nbsp;|&nbsp; "
        f"Draft: **{batch_info['pages_draft']}** &nbsp;|&nbsp; "
        f"Approved: **{batch_info['pages_approved']}** &nbsp;|&nbsp; "
        f"Deployed: **{batch_info['pages_deployed']}**"
    )

    # ── Canvas controls ─────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2, 2, 2, 2])
    with ctrl1:
        sort_opt = st.selectbox(
            "Sort by",
            ["created_at", "last_modified_at", "title", "review_status"],
            index=["created_at", "last_modified_at", "title", "review_status"].index(
                st.session_state.canvas_sort
            ),
            key="canvas_sort_sel",
        )
        st.session_state.canvas_sort = sort_opt
    with ctrl2:
        filter_opt = st.selectbox(
            "Filter Status",
            ["All", "draft", "reviewed", "approved", "needs_revision", "rejected", "deployed"],
            index=["All", "draft", "reviewed", "approved", "needs_revision", "rejected", "deployed"].index(
                st.session_state.canvas_filter
            ),
            key="canvas_filter_sel",
        )
        st.session_state.canvas_filter = filter_opt
    with ctrl3:
        select_all = st.button("☑ Select All")
    with ctrl4:
        deselect_all = st.button("☐ Deselect All")

    # Load pages
    pages = db.list_pages(
        batch_id,
        status_filter=None if filter_opt == "All" else filter_opt,
        sort_by=sort_opt,
    )

    # Sort by quality score descending if requested
    if sort_opt == "quality":
        pages.sort(key=lambda p: (p.get("quality_scores") or {}).get("overall_score", 0), reverse=True)

    if select_all:
        st.session_state.selected_page_ids = [p["id"] for p in pages]
    if deselect_all:
        st.session_state.selected_page_ids = []

    # ── Page grid ────────────────────────────────────────────────────────────
    if not pages:
        st.info("No pages in this batch yet. Use the **Generate** tab to add pages.")
    else:
        # 3-column grid layout
        COLS = 3
        rows = [pages[i:i+COLS] for i in range(0, len(pages), COLS)]

        for row in rows:
            cols = st.columns(COLS)
            for col, page in zip(cols, row):
                with col:
                    qs: dict = page.get("quality_scores") or {}
                    overall = qs.get("overall_score")
                    status = page.get("review_status", "draft")
                    status_color = _STATUS_COLORS.get(status, "#6b7280")
                    status_emoji = _STATUS_EMOJI.get(status, "📝")

                    # Tile card
                    with st.container(border=True):
                        # Checkbox + title row
                        chk_col, title_col = st.columns([1, 5])
                        with chk_col:
                            checked = page["id"] in st.session_state.selected_page_ids
                            if st.checkbox("", value=checked, key=f"chk_{page['id']}"):
                                if page["id"] not in st.session_state.selected_page_ids:
                                    st.session_state.selected_page_ids.append(page["id"])
                            else:
                                if page["id"] in st.session_state.selected_page_ids:
                                    st.session_state.selected_page_ids.remove(page["id"])
                        with title_col:
                            st.markdown(f"**{page['title'][:40]}{'…' if len(page['title']) > 40 else ''}**")

                        # Keyword & keyword target
                        kw = page.get("target_keyword") or "—"
                        st.caption(f"🔑 {kw[:35]}")

                        # Quality overall
                        if overall is not None:
                            color = _SCORE_COLORS[QualityScorer.color_for_score(overall)]
                            st.markdown(
                                f'<span style="font-size:1.3em;font-weight:700;color:{color}">'
                                f"◆ {overall}/100</span>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown("◇ Not scored")

                        # Per-metric mini badges
                        if qs:
                            pills = " &nbsp; ".join([
                                _score_pill(qs.get("authority_score"), "Auth"),
                                _score_pill(qs.get("semantic_richness_score"), "Sem"),
                                _score_pill(qs.get("structure_score"), "Str"),
                                _score_pill(qs.get("engagement_potential_score"), "Eng"),
                                _score_pill(qs.get("uniqueness_score"), "Uniq"),
                            ])
                            st.markdown(pills, unsafe_allow_html=True)

                        # Status badge
                        st.markdown(
                            f'<span style="color:{status_color};font-size:0.85em">'
                            f"{status_emoji} {status.replace('_', ' ').title()}</span>",
                            unsafe_allow_html=True,
                        )

                        # Action buttons
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("🔍 Preview", key=f"prev_{page['id']}"):
                                st.session_state.preview_page_id = page["id"]
                        with btn_col2:
                            if st.button("✅ Approve", key=f"appr_{page['id']}"):
                                db.update_page_status(page["id"], "approved")
                                st.rerun()

    # ── Right sidebar: batch actions for selected pages ───────────────────────
    selected_ids = st.session_state.selected_page_ids
    if selected_ids:
        st.markdown("---")
        with st.expander(f"🎨 Batch Actions ({len(selected_ids)} pages selected)", expanded=True):
            ba_col1, ba_col2 = st.columns(2)
            with ba_col1:
                new_color = st.color_picker("Primary Colour", batch_info.get("batch_primary_color", "#2563EB"), key="ba_color")
                new_cta_text = st.text_input("Global CTA Text", batch_info.get("batch_global_cta_text", "Get Started"), key="ba_cta_text")
                new_cta_link = st.text_input("Global CTA Link", batch_info.get("batch_global_cta_link", "/contact"), key="ba_cta_link")
            with ba_col2:
                templates = db.list_templates()
                tmpl_opts = {t["display_name"]: t["id"] for t in templates}
                chosen_tmpl_name = st.selectbox("Apply Template", list(tmpl_opts.keys()), key="ba_template")
                new_status = st.selectbox(
                    "Set Status (selected)",
                    ["(keep current)", "draft", "reviewed", "approved", "needs_revision", "rejected"],
                    key="ba_status",
                )

            regen_cols = st.columns(3)
            with regen_cols[0]:
                regen_sem = st.checkbox("Semantic Richness (add LSI)", key="regen_sem")
            with regen_cols[1]:
                regen_auth = st.checkbox("Authority (add citations)", key="regen_auth")
            with regen_cols[2]:
                regen_uniq = st.checkbox("Unique Angles (differentiate)", key="regen_uniq")

            apply_col, export_col, del_col = st.columns(3)
            with apply_col:
                if st.button("▶ Apply to Selected", key="ba_apply"):
                    tmpl_id = tmpl_opts.get(chosen_tmpl_name)
                    for pid in selected_ids:
                        updates: dict = {
                            "color_override": new_color,
                            "cta_text_override": new_cta_text,
                            "cta_link_override": new_cta_link,
                            "template_id": tmpl_id,
                        }
                        db.update_page(pid, updates)
                        if new_status != "(keep current)":
                            db.update_page_status(pid, new_status)
                    db.update_batch_styles(
                        batch_id,
                        primary_color=new_color,
                        global_cta_text=new_cta_text,
                        global_cta_link=new_cta_link,
                    )
                    st.success(f"✅ Applied to {len(selected_ids)} pages")
                    st.rerun()
            with export_col:
                if st.button("📦 Export JSON", key="ba_export"):
                    export_pages = [db.get_page(pid) for pid in selected_ids]
                    st.download_button(
                        "⬇ Download JSON",
                        data=json.dumps(export_pages, indent=2, default=str),
                        file_name=f"batch_{batch_id}_pages.json",
                        mime="application/json",
                        key="ba_dl",
                    )
            with del_col:
                if st.button("🗑 Delete Selected", key="ba_delete"):
                    for pid in selected_ids:
                        db.delete_page(pid)
                    st.session_state.selected_page_ids = []
                    st.success("Deleted selected pages")
                    st.rerun()

    # ── Preview Modal ─────────────────────────────────────────────────────────
    if st.session_state.preview_page_id:
        preview_page = db.get_page(st.session_state.preview_page_id)
        if not preview_page:
            st.session_state.preview_page_id = None
        else:
            st.markdown("---")
            close_col, title_col = st.columns([1, 9])
            with close_col:
                if st.button("✖ Close", key="close_preview"):
                    st.session_state.preview_page_id = None
                    st.rerun()
            with title_col:
                st.subheader(f"🔍 Page Preview: {preview_page['title']}")

            # Tab bar for Preview / Quality Breakdown
            prev_tab, quality_tab, json_tab = st.tabs(["📄 Live Preview", "📊 Quality Breakdown", "🔧 JSON Editor"])

            with prev_tab:
                left, right = st.columns([1, 1])
                with left:
                    st.markdown("**Edit Fields**")
                    new_title = st.text_input("Title", preview_page.get("title", ""), key="edit_title")
                    new_h1 = st.text_input("H1", preview_page.get("h1", ""), key="edit_h1")
                    new_meta_title = st.text_input("Meta Title", preview_page.get("meta_title", ""), key="edit_mt")
                    new_meta_desc = st.text_area("Meta Description", preview_page.get("meta_description", ""), key="edit_md", height=80)
                    new_kw = st.text_input("Target Keyword", preview_page.get("target_keyword", ""), key="edit_kw")
                    new_wc = st.number_input("Word Count", value=int(preview_page.get("word_count") or 0), key="edit_wc")
                    new_content = st.text_area("Content (Markdown)", preview_page.get("content_markdown", ""), key="edit_content", height=200)
                    new_notes = st.text_area("Reviewer Notes", preview_page.get("reviewer_notes", ""), key="edit_notes", height=60)

                    save_col, rev_col = st.columns(2)
                    with save_col:
                        if st.button("💾 Save Draft", key="save_draft"):
                            old_scores = preview_page.get("quality_scores") or {}
                            db.update_page(preview_page["id"], {
                                "title": new_title,
                                "h1": new_h1,
                                "meta_title": new_meta_title,
                                "meta_description": new_meta_desc,
                                "target_keyword": new_kw,
                                "word_count": new_wc,
                                "content_markdown": new_content,
                                "reviewer_notes": new_notes,
                            })
                            # Re-score after edit
                            updated = db.get_page(preview_page["id"])
                            new_scores = scorer.score(updated)
                            db.update_page_quality_scores(
                                preview_page["id"],
                                new_scores,
                                audit_entry={
                                    "change_type": "manual_edit",
                                    "score_before": old_scores.get("overall_score"),
                                    "score_after": new_scores["overall_score"],
                                },
                            )
                            db.record_revision(
                                preview_page["id"],
                                old_scores,
                                new_scores,
                                change_type="manual_edit",
                                change_reason="Manual edit via preview panel",
                            )
                            st.success("✅ Saved & re-scored!")
                            st.rerun()
                    with rev_col:
                        if st.button("↩ Revert", key="revert_draft"):
                            st.rerun()

                with right:
                    st.markdown("**Live Preview**")
                    # Template selector
                    templates = db.list_templates()
                    tmpl_opts = {t["display_name"]: t for t in templates}
                    chosen_tmpl = st.selectbox("Template", list(tmpl_opts.keys()), key="prev_template")
                    tmpl = tmpl_opts[chosen_tmpl]
                    color = preview_page.get("color_override") or (tmpl.get("color_config") or {}).get("primary", "#2563EB")
                    disp_color = st.color_picker("Brand Colour", color, key="prev_color")

                    # Render a live HTML preview
                    h1_text = preview_page.get("h1") or preview_page.get("title") or ""
                    content_md = preview_page.get("content_markdown") or ""
                    cta_text = preview_page.get("cta_text_override") or "Get Started"
                    cta_link = preview_page.get("cta_link_override") or "/contact"

                    # Convert minimal Markdown to HTML for preview
                    def _md_to_html(md: str) -> str:
                        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', md, flags=re.MULTILINE)
                        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
                        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
                        html = re.sub(r'^\- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
                        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
                        html = re.sub(r'\n\n+', '</p><p>', html)
                        return f"<p>{html}</p>"

                    preview_html = f"""
<html>
<head>
<style>
  body {{ font-family: {(tmpl.get('typography_config') or {}).get('heading_font', 'Inter')}, sans-serif;
          margin: 20px; color: #111827; background: #fff; font-size: 15px; }}
  h1 {{ color: {disp_color}; font-size: 1.6em; border-bottom: 2px solid {disp_color}; padding-bottom: 8px; }}
  h2 {{ color: #1f2937; font-size: 1.2em; margin-top: 18px; }}
  h3 {{ color: #374151; font-size: 1em; margin-top: 12px; }}
  .cta {{ background: {disp_color}; color: white; padding: 10px 20px;
          border-radius: 6px; display: inline-block; margin: 16px 0;
          font-weight: bold; text-decoration: none; }}
  li {{ margin-left: 20px; }}
  p {{ line-height: 1.6; }}
</style>
</head>
<body>
<h1>{h1_text}</h1>
{_md_to_html(content_md[:2000])}
<br>
<a class="cta">{cta_text} →</a>
</body>
</html>"""
                    st.components.v1.html(preview_html, height=450, scrolling=True)

                    # Responsive toggle (visual only)
                    vp_col1, vp_col2, vp_col3 = st.columns(3)
                    with vp_col1:
                        st.button("🖥 Desktop", key="vp_desk")
                    with vp_col2:
                        st.button("📱 Tablet", key="vp_tablet")
                    with vp_col3:
                        st.button("📲 Mobile", key="vp_mobile")

            with quality_tab:
                # Run/refresh quality scores
                qs_data = preview_page.get("quality_scores") or {}
                if not qs_data or st.button("🔄 Refresh Quality Scores", key="refresh_qs"):
                    qs_data = scorer.score(preview_page)
                    db.update_page_quality_scores(preview_page["id"], qs_data)
                    preview_page = db.get_page(preview_page["id"])

                if qs_data:
                    overall = qs_data.get("overall_score", 0)
                    label = QualityScorer.quality_label(overall)
                    color = _SCORE_COLORS[QualityScorer.color_for_score(overall)]

                    st.markdown(
                        f'<h3>Overall Quality: <span style="color:{color}">{overall}/100</span> — {label}</h3>',
                        unsafe_allow_html=True,
                    )

                    breakdown = qs_data.get("breakdown") or {}
                    metric_keys = [
                        ("authority", "Authority (E-E-A-T)", qs_data.get("authority_score", 0)),
                        ("semantic_richness", "Semantic Richness", qs_data.get("semantic_richness_score", 0)),
                        ("structure", "Structure & Schema", qs_data.get("structure_score", 0)),
                        ("engagement", "Engagement Potential", qs_data.get("engagement_potential_score", 0)),
                        ("uniqueness", "Uniqueness vs Competitors", qs_data.get("uniqueness_score", 0)),
                    ]

                    for key, label_str, score in metric_keys:
                        m_data = breakdown.get(key, {})
                        m_color = _SCORE_COLORS[QualityScorer.color_for_score(score)]
                        st.markdown(
                            f'**{label_str}:** <span style="color:{m_color}">{score}/100 ({m_data.get("band", "")})</span>',
                            unsafe_allow_html=True,
                        )
                        st.progress(score / 100)
                        for pos in m_data.get("positives", []):
                            st.markdown(f"&nbsp;&nbsp;✓ {pos}")
                        for sug in m_data.get("suggestions", []):
                            st.markdown(f"&nbsp;&nbsp;➜ *{sug}*")

                    st.markdown("---")
                    # Status change
                    qs_status_col, qs_regen_col = st.columns(2)
                    with qs_status_col:
                        new_status_qs = st.selectbox(
                            "Set Status",
                            ["draft", "reviewed", "approved", "needs_revision", "rejected"],
                            index=["draft", "reviewed", "approved", "needs_revision", "rejected"].index(
                                preview_page.get("review_status", "draft")
                            ),
                            key="qs_status_sel",
                        )
                        if st.button("Update Status", key="qs_update_status"):
                            db.update_page_status(preview_page["id"], new_status_qs)
                            st.success(f"Status → {new_status_qs}")
                            st.rerun()
                    with qs_regen_col:
                        st.markdown("**Recommendations:**")
                        for rec in (qs_data.get("recommendations") or [])[:5]:
                            st.caption(f"• {rec}")

            with json_tab:
                st.markdown("**Full Page Object (JSON)**")
                page_json = {k: v for k, v in preview_page.items()}
                edited_json = st.text_area(
                    "Edit JSON directly",
                    value=json.dumps(page_json, indent=2, default=str),
                    height=400,
                    key="json_editor",
                )
                if st.button("💾 Apply JSON Changes", key="json_apply"):
                    try:
                        parsed = json.loads(edited_json)
                        # Remove read-only fields
                        for ro_key in ("id", "batch_id", "created_at"):
                            parsed.pop(ro_key, None)
                        db.update_page(preview_page["id"], parsed)
                        st.success("✅ JSON applied and saved!")
                        st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {e}")


# ============================================================================
# TAB 2: GENERATE
# ============================================================================

with tab_generate:
    st.header("⚙️ Generate Pages")

    batches = db.list_batches()
    batch_opts_gen = {f"#{b['id']} — {b['name']}": b["id"] for b in batches} if batches else {}

    st.subheader("1. Select or Create Batch")
    gen_batch_col1, gen_batch_col2 = st.columns(2)
    with gen_batch_col1:
        if batch_opts_gen:
            selected_gen_batch = st.selectbox("Batch", list(batch_opts_gen.keys()), key="gen_batch_sel")
            gen_batch_id = batch_opts_gen[selected_gen_batch]
        else:
            st.info("Create a batch first.")
            gen_batch_id = None
    with gen_batch_col2:
        with st.expander("Create New Batch"):
            nb_name = st.text_input("Name", key="nb_name")
            nb_desc = st.text_input("Description", key="nb_desc")
            nb_client = st.text_input("Client ID", key="nb_client")
            if st.button("Create", key="nb_create"):
                if nb_name:
                    new_bid = db.create_batch(nb_name, description=nb_desc, client_id=nb_client)
                    st.session_state.active_batch_id = new_bid
                    st.success(f"Created batch #{new_bid}: {nb_name}")
                    st.rerun()

    st.markdown("---")
    st.subheader("2. Single Page")
    gen_col1, gen_col2 = st.columns(2)
    with gen_col1:
        gen_title = st.text_input("Page Title", placeholder="NFT Consulting Services", key="gen_title")
        gen_h1 = st.text_input("H1", placeholder="Expert NFT Strategy Consulting", key="gen_h1")
        gen_kw = st.text_input("Target Keyword", placeholder="nft consulting services", key="gen_kw")
        gen_meta_title = st.text_input("Meta Title (50–60 chars)", key="gen_meta_title")
        gen_meta_desc = st.text_area("Meta Description (155–160 chars)", key="gen_meta_desc", height=80)
    with gen_col2:
        gen_slug = st.text_input("Slug", placeholder="nft-consulting-services", key="gen_slug")
        gen_role = st.selectbox("Role", ["spoke", "hub"], key="gen_role")
        gen_template = st.selectbox("Template", [t["display_name"] for t in db.list_templates()], key="gen_template")
        gen_lsi = st.text_area("LSI Keywords (one per line)", key="gen_lsi", height=80)
        gen_content = st.text_area("Content (Markdown)", key="gen_content", height=150)

    if st.button("➕ Add Page to Batch", key="gen_add_page") and gen_batch_id:
        lsi_list = [k.strip() for k in gen_lsi.split("\n") if k.strip()]
        tmpl_id_map = {t["display_name"]: t["id"] for t in db.list_templates()}
        page_obj = {
            "title": gen_title or "Untitled",
            "slug": gen_slug or gen_title.lower().replace(" ", "-"),
            "h1": gen_h1 or gen_title,
            "meta_title": gen_meta_title,
            "meta_description": gen_meta_desc,
            "target_keyword": gen_kw,
            "role": gen_role,
            "content_markdown": gen_content,
            "template_id": tmpl_id_map.get(gen_template),
            "semantic_core": {
                "lsi_keywords": lsi_list,
                "entities": [],
                "topic_coverage": {},
            },
            "structure": {"h1": gen_h1 or gen_title, "h2_sections": [], "cta_sections": []},
            "competitor_intelligence": {},
            "quality_scores": {},
        }
        pid = db.create_page(gen_batch_id, page_obj)
        # Auto-score
        scores = scorer.score(page_obj)
        db.update_page_quality_scores(pid, scores)
        st.success(f"✅ Added page #{pid}: {gen_title} (Overall quality: {scores['overall_score']}/100)")
        st.session_state.active_batch_id = gen_batch_id

    st.markdown("---")
    st.subheader("3. Batch Generation (Multiple Pages)")
    batch_json_input = st.text_area(
        "Paste JSON array of page objects",
        placeholder='[{"title": "Page 1", "target_keyword": "kw1", ...}, ...]',
        height=200,
        key="batch_json_input",
    )
    if st.button("🚀 Generate Batch from JSON", key="gen_batch_btn") and gen_batch_id:
        try:
            page_list = json.loads(batch_json_input)
            if not isinstance(page_list, list):
                st.error("Input must be a JSON array.")
            else:
                added = 0
                for p in page_list:
                    pid = db.create_page(gen_batch_id, p)
                    scores = scorer.score(p)
                    db.update_page_quality_scores(pid, scores)
                    added += 1
                st.success(f"✅ Added {added} pages to batch #{gen_batch_id}")
                st.session_state.active_batch_id = gen_batch_id
        except json.JSONDecodeError as e:
            st.error(f"JSON parse error: {e}")

    st.markdown("---")
    st.subheader("4. Score Existing Pages")
    if st.button("📊 Re-score All Pages in Active Batch", key="rescore_all"):
        active_bid = st.session_state.active_batch_id
        if active_bid:
            pages_to_score = db.list_pages(active_bid)
            for p in pages_to_score:
                scores = scorer.score(p)
                db.update_page_quality_scores(p["id"], scores)
            st.success(f"✅ Re-scored {len(pages_to_score)} pages")
        else:
            st.warning("Select an active batch first.")


# ============================================================================
# TAB 3: DEPLOY
# ============================================================================

with tab_deploy:
    st.header("🚀 Deploy")

    batches_dep = db.list_batches()
    if not batches_dep:
        st.info("No batches available.")
        st.stop()

    dep_batch_opts = {f"#{b['id']} — {b['name']}": b["id"] for b in batches_dep}
    dep_chosen = st.selectbox("Select Batch to Deploy", list(dep_batch_opts.keys()), key="dep_batch_sel")
    dep_batch_id = dep_batch_opts[dep_chosen]
    dep_batch_info = db.get_batch(dep_batch_id)

    # Batch summary
    st.markdown(
        f"**Total Pages:** {dep_batch_info['total_pages']} &nbsp;|&nbsp; "
        f"**Approved:** {dep_batch_info['pages_approved']} &nbsp;|&nbsp; "
        f"**Deployed:** {dep_batch_info['pages_deployed']}"
    )

    st.markdown("---")
    st.subheader("Phase 3 — Pre-flight Checks")

    if st.button("🔎 Run Pre-flight Checks", key="run_preflight"):
        preflight = db.get_deploy_preflight(dep_batch_id)
        checks = preflight["checks"]

        all_passed = preflight["passed"]
        for check_name, passed in checks.items():
            icon = "✅" if passed else "❌"
            st.markdown(f"{icon} **{check_name.replace('_', ' ').title()}**")

        if preflight["failures"]:
            st.warning("Pre-flight failures:")
            for fail in preflight["failures"]:
                st.caption(f"• {fail}")

        if all_passed:
            st.success(f"✅ All checks passed! {preflight['total_approved']} page(s) ready to deploy.")
        else:
            st.error("❌ Pre-flight checks failed. Fix issues before deploying.")

    st.markdown("---")
    st.subheader("Deploy (Human Gate)")
    approved_pages = db.list_pages(dep_batch_id, status_filter="approved")

    if not approved_pages:
        st.info("No approved pages in this batch. Approve pages in the Staging Canvas first.")
    else:
        st.write(f"**{len(approved_pages)} approved page(s) ready to deploy:**")
        for p in approved_pages[:10]:
            qs = p.get("quality_scores") or {}
            overall = qs.get("overall_score", "—")
            st.markdown(f"• **{p['title']}** — Quality: {overall}/100 — Status: {p['review_status']}")
        if len(approved_pages) > 10:
            st.caption(f"…and {len(approved_pages) - 10} more.")

        col_export, col_deploy = st.columns(2)
        with col_export:
            # Export options
            export_format = st.selectbox("Export Format", ["JSON", "Markdown", "CSV Metadata"], key="export_fmt")
            if st.button("📦 Export Approved Pages", key="export_approved"):
                if export_format == "JSON":
                    data = json.dumps(approved_pages, indent=2, default=str)
                    mime = "application/json"
                    fname = f"batch_{dep_batch_id}_approved.json"
                elif export_format == "Markdown":
                    lines = []
                    for p in approved_pages:
                        lines.append(f"# {p.get('h1', p['title'])}\n\n")
                        lines.append(p.get("content_markdown", "") + "\n\n---\n\n")
                    data = "".join(lines)
                    mime = "text/markdown"
                    fname = f"batch_{dep_batch_id}_approved.md"
                else:  # CSV
                    buf = io.StringIO()
                    writer = csv.DictWriter(buf, fieldnames=[
                        "id", "title", "slug", "h1", "meta_title", "meta_description",
                        "target_keyword", "word_count", "review_status",
                    ])
                    writer.writeheader()
                    for p in approved_pages:
                        writer.writerow({k: p.get(k, "") for k in writer.fieldnames})
                    data = buf.getvalue()
                    mime = "text/csv"
                    fname = f"batch_{dep_batch_id}_metadata.csv"

                st.download_button(
                    f"⬇ Download {export_format}",
                    data=data,
                    file_name=fname,
                    mime=mime,
                    key="dl_approved",
                )

        with col_deploy:
            st.warning(
                "⚠️ Deployment is permanent. This will mark all approved pages as **deployed** "
                "and record a deployment timestamp."
            )
            confirm = st.checkbox("I confirm I want to deploy all approved pages", key="deploy_confirm")
            if confirm and st.button("🚀 Deploy All Approved Pages", key="deploy_btn", type="primary"):
                count = db.deploy_batch(dep_batch_id)
                st.success(f"🎉 Successfully deployed {count} pages!")
                st.balloons()
                st.rerun()

    st.markdown("---")
    st.subheader("Hub-and-Spoke Map")
    all_batch_pages = db.list_pages(dep_batch_id)
    hub_pages = [p for p in all_batch_pages if p.get("role") == "hub"]
    spoke_pages = [p for p in all_batch_pages if p.get("role") == "spoke"]

    if not all_batch_pages:
        st.info("No pages in this batch.")
    else:
        st.write(f"**{len(hub_pages)} hub page(s)** | **{len(spoke_pages)} spoke page(s)**")
        for hub in hub_pages:
            qs = hub.get("quality_scores") or {}
            st.markdown(f"🔵 **HUB:** {hub['title']} (Quality: {qs.get('overall_score', '—')}/100)")
            hub_spokes = [p for p in spoke_pages if p.get("hub_page_id") == hub["id"]]
            for spoke in hub_spokes:
                sqs = spoke.get("quality_scores") or {}
                st.markdown(f"&nbsp;&nbsp;└── 🟢 **SPOKE:** {spoke['title']} (Quality: {sqs.get('overall_score', '—')}/100)")
        orphan_spokes = [p for p in spoke_pages if not any(p["id"] in [s.get("id") for s in []] for _ in hub_pages)]
        for p in orphan_spokes:
            if not p.get("hub_page_id"):
                st.markdown(f"⚠️ **ORPHAN SPOKE:** {p['title']} (no hub assigned)")
