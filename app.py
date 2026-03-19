import streamlit as st
import json
from datetime import datetime

# Initialize session state for storage
if "pages" not in st.session_state:
    st.session_state.pages = []

if "deployments" not in st.session_state:
    st.session_state.deployments = []

st.set_page_config(page_title="Sturdy Broccoli CMS", layout="wide")
st.title("🥦 Sturdy Broccoli CMS")

# Navigation tabs
tab_create, tab_library, tab_dashboard = st.tabs(["Create", "Library", "Dashboard"])

# ============================================================================
# TAB 1: CREATE
# ============================================================================
with tab_create:
    st.header("Create New Page")
    
    col1, col2 = st.columns(2)
    
    with col1:
        topic = st.text_input("Topic", placeholder="e.g., Redis WebSocket Scaling")
        keyword = st.text_input("Primary Keyword", placeholder="e.g., redis websocket scaling strategy")
    
    with col2:
        page_type = st.selectbox("Page Type", ["Blog Post", "Landing Page", "Case Study"])
        reading_level = st.selectbox("Reading Level", ["Beginner", "Intermediate", "Advanced"])
    
    if st.button("Generate Page", key="btn_generate"):
        if topic and keyword:
            # Simulate content generation
            new_page = {
                "id": len(st.session_state.pages) + 1,
                "title": topic,
                "keyword": keyword,
                "type": page_type,
                "reading_level": reading_level,
                "status": "draft",
                "created_at": datetime.now().isoformat(),
                "content": f"# {topic}\n\nThis is a generated page about {topic} with focus on '{keyword}'.",
                "seo_score": 78,
                "word_count": 1500
            }
            st.session_state.pages.append(new_page)
            st.success(f"✅ Generated: {topic}")
            st.write(f"**Keyword:** {keyword}")
            st.write(f"**SEO Score:** 78/100")
    
    # Batch operations
    st.markdown("---")
    st.subheader("Batch Operations")
    
    num_pages = st.number_input("Number of pages to generate", min_value=1, max_value=10, value=1)
    
    if st.button("Generate Batch"):
        for i in range(num_pages):
            new_page = {
                "id": len(st.session_state.pages) + 1,
                "title": f"Batch Page {i+1}",
                "keyword": f"keyword-{i+1}",
                "type": "Blog Post",
                "reading_level": "Intermediate",
                "status": "draft",
                "created_at": datetime.now().isoformat(),
                "content": f"Generated batch page {i+1}",
                "seo_score": 75 + i,
                "word_count": 1200 + i*100
            }
            st.session_state.pages.append(new_page)
        st.success(f"✅ Generated {num_pages} pages!")

# ============================================================================
# TAB 2: LIBRARY
# ============================================================================
with tab_library:
    st.header("Content Library")
    
    if len(st.session_state.pages) == 0:
        st.info("No pages yet. Create some in the 'Create' tab!")
    else:
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Filter by Status", ["All", "draft", "published"])
        with col2:
            type_filter = st.selectbox("Filter by Type", ["All", "Blog Post", "Landing Page", "Case Study"])
        with col3:
            sort_by = st.selectbox("Sort by", ["Created (Newest)", "SEO Score (High)", "Word Count"])
        
        # Apply filters
        filtered_pages = st.session_state.pages
        if status_filter != "All":
            filtered_pages = [p for p in filtered_pages if p["status"] == status_filter]
        if type_filter != "All":
            filtered_pages = [p for p in filtered_pages if p["type"] == type_filter]
        
        # Sort
        if sort_by == "SEO Score (High)":
            filtered_pages = sorted(filtered_pages, key=lambda x: x["seo_score"], reverse=True)
        elif sort_by == "Word Count":
            filtered_pages = sorted(filtered_pages, key=lambda x: x["word_count"], reverse=True)
        
        # Display pages
        for page in filtered_pages:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.write(f"**{page['title']}**")
                st.caption(f"Keyword: {page['keyword']} | Type: {page['type']}")
            
            with col2:
                st.metric("SEO", f"{page['seo_score']}/100")
            
            with col3:
                if page["status"] == "draft":
                    st.warning("Draft")
                else:
                    st.success("Published")
            
            with col4:
                if st.button("Publish", key=f"publish_{page['id']}"):
                    page["status"] = "published"
                    st.rerun()

# ============================================================================
# TAB 3: DASHBOARD
# ============================================================================
with tab_dashboard:
    st.header("Dashboard")
    
    # Calculate metrics
    total_pages = len(st.session_state.pages)
    published_pages = len([p for p in st.session_state.pages if p["status"] == "published"])
    draft_pages = len([p for p in st.session_state.pages if p["status"] == "draft"])
    avg_seo = sum([p["seo_score"] for p in st.session_state.pages]) / total_pages if total_pages > 0 else 0
    total_words = sum([p["word_count"] for p in st.session_state.pages])
    
    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Pages", total_pages)
    
    with col2:
        st.metric("Published", published_pages)
    
    with col3:
        st.metric("Drafts", draft_pages)
    
    with col4:
        st.metric("Avg SEO Score", f"{avg_seo:.0f}")
    
    with col5:
        st.metric("Total Words", f"{total_words:,}")
    
    # Recent activity
    st.subheader("Recent Activity")
    if len(st.session_state.pages) > 0:
        recent = sorted(st.session_state.pages, key=lambda x: x["created_at"], reverse=True)[:5]
        for page in recent:
            st.write(f"✅ **{page['title']}** ({page['status']}) - SEO: {page['seo_score']}/100")
    else:
        st.info("No activity yet")
    
    # Deployment section
    st.markdown("---")
    st.subheader("Deployment")
    
    if draft_pages > 0:
        st.info(f"You have {draft_pages} draft page(s) ready to publish")
        if st.button("Publish All Drafts"):
            for page in st.session_state.pages:
                if page["status"] == "draft":
                    page["status"] = "published"
            st.success("✅ All drafts published!")
            st.rerun()
    else:
        st.success("All pages are published!")
