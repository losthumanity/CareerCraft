"""
Mission Control Dashboard - Streamlit Web Interface
Track job applications, monitor scraper activity, and manage applications.
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os
import altair as alt

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Japan 2026 Job Sniper",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS STYLING ---
st.markdown("""
<style>
    /* Card Styling */
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    [data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: bold;
    }

    /* Dark mode adjustments (if user uses dark mode, these colors adapt) */
    @media (prefers-color-scheme: dark) {
        .stMetric {
            background-color: #262730;
            border: 1px solid #464b5c;
        }
    }

    /* Header Styling */
    h1 { color: #FF4B4B; }
    h2 { border-bottom: 2px solid #f0f2f6; padding-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE MANAGEMENT ---
DB_PATH = '../shared/jobs.db'

def init_database():
    """Create jobs database if it doesn't exist."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            keywords_matched TEXT,
            date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            applied_status TEXT DEFAULT 'Pending',
            notes TEXT,
            resume_generated BOOLEAN DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraper_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            company TEXT,
            status TEXT,
            jobs_found INTEGER DEFAULT 0,
            error_message TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB
init_database()

# --- DATA LOADING FUNCTIONS ---
def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT id, company, title, date_found, url, applied_status,
                   keywords_matched, resume_generated, notes
            FROM jobs
            ORDER BY date_found DESC
        """
        df = pd.read_sql(query, conn)

        # Convert date to datetime object for better handling
        df['date_found'] = pd.to_datetime(df['date_found'])
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame() # Return empty if error

def get_last_scraper_run():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, company, status, jobs_found FROM scraper_logs ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row
    except:
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/197/197484.png", width=50) # Placeholder flag icon
    st.title("Sniper Control")

    st.markdown("### 👤 User Profile")
    st.info("**Current:** Internship @ Johnson Controls")
    st.caption(f"Last Login: {datetime.now().strftime('%H:%M %d-%b')}")

    st.divider()

    st.markdown("### ⚙️ Quick Actions")
    if st.button("🔄 Force Refresh", use_container_width=True):
        st.rerun()

    st.divider()

    # Scraper Health Check
    last_run = get_last_scraper_run()
    st.markdown("### 🤖 Watcher Status")
    if last_run:
        st.write(f"**Last Run:** {last_run[0]}")
        st.write(f"**Target:** {last_run[1]}")
        status_color = "green" if last_run[2] == "Success" else "red"
        st.markdown(f"**Status:** :{status_color}[{last_run[2]}]")
        st.metric("New Jobs Found", last_run[3])
    else:
        st.warning("Watcher hasn't run yet.")

# --- MAIN LAYOUT ---
st.title("🇯🇵 Japan 2026 Job Sniper")

# Create Tabs for cleaner UI
tab1, tab2, tab3 = st.tabs(["📡 Mission Radar", "📋 Job Database", "📈 Analytics & Tools"])

# ================= TAB 1: MISSION RADAR (Overview) =================
with tab1:
    # Top Stats Row
    df_jobs = load_data()

    col1, col2, col3, col4 = st.columns(4)
    if not df_jobs.empty:
        with col1:
            st.metric("Total Targets", len(df_jobs), delta="Total Scanned")
        with col2:
            pending = len(df_jobs[df_jobs['applied_status'] == 'Pending'])
            st.metric("Action Required", pending, delta="Pending", delta_color="inverse")
        with col3:
            applied = len(df_jobs[df_jobs['applied_status'] == 'Applied'])
            st.metric("Applications Sent", applied)
        with col4:
            # Calculate Resume Readiness
            ready = len(df_jobs[df_jobs['resume_generated'] == 1])
            st.metric("CVs Generated", ready)

    st.divider()

    st.subheader("🗓️ Strategic Timeline")

    # Timeline Data (Hardcoded strategy)
    timeline_data = [
        {"Company": "Mercari", "Status": "Open", "Priority": "High", "Window": "Now - May"},
        {"Company": "Woven (Toyota)", "Status": "Upcoming", "Priority": "Critical", "Window": "Jan 15 - Jun"},
        {"Company": "Rakuten", "Status": "Upcoming", "Priority": "Critical", "Window": "Feb - Mar"},
        {"Company": "Sony Group", "Status": "Upcoming", "Priority": "Critical", "Window": "Mar - Apr"},
        {"Company": "Preferred Networks", "Status": "TBD", "Priority": "Medium", "Window": "Mar - May"},
    ]

    # Display Timeline as Cards instead of a boring table
    cols = st.columns(len(timeline_data))
    for i, item in enumerate(timeline_data):
        with cols[i]:
            if item["Status"] == "Open":
                status_icon = "🟢"
                bg_color = "rgba(76, 175, 80, 0.1)"
            elif item["Status"] == "Upcoming":
                status_icon = "🟡"
                bg_color = "rgba(255, 193, 7, 0.1)"
            else:
                status_icon = "🔴"
                bg_color = "rgba(255, 255, 255, 0.05)"

            st.markdown(f"""
            <div style="background-color: {bg_color}; padding: 10px; border-radius: 8px; border: 1px solid #ddd; height: 180px;">
                <h4>{item['Company']}</h4>
                <p><b>{status_icon} {item['Status']}</b></p>
                <p style="font-size: 12px; color: gray;">{item['Window']}</p>
                <hr style="margin: 5px 0;">
                <p style="font-size: 14px;">Priority: <b>{item['Priority']}</b></p>
            </div>
            """, unsafe_allow_html=True)

# ================= TAB 2: JOB DATABASE (Management) =================
with tab2:
    st.subheader("🎯 Live Targets")

    if df_jobs.empty:
        st.info("No data found. Please run the scraper first.")
    else:
        # Filters
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            company_filter = st.multiselect("Filter by Company", options=df_jobs['company'].unique())
        with f_col2:
            status_filter = st.multiselect("Filter by Status", options=df_jobs['applied_status'].unique())

        # Apply Filters
        filtered_df = df_jobs.copy()
        if company_filter:
            filtered_df = filtered_df[filtered_df['company'].isin(company_filter)]
        if status_filter:
            filtered_df = filtered_df[filtered_df['applied_status'].isin(status_filter)]

        # Data Editor with Advanced Column Config
        edited_df = st.data_editor(
            filtered_df,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "company": st.column_config.TextColumn("Company", width="medium"),
                "title": st.column_config.TextColumn("Job Title", width="large"),
                "date_found": st.column_config.DatetimeColumn("Found", format="D MMM, HH:mm", width="medium", disabled=True),
                "url": st.column_config.LinkColumn("Link", display_text="Open Job"),
                "applied_status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Pending", "CV Generated", "Applied", "Interview", "Offer", "Rejected"],
                    width="medium",
                    required=True
                ),
                "resume_generated": st.column_config.CheckboxColumn("CV Ready?"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                "keywords_matched": None # Hide this to save space
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="job_editor"
        )

        # Save Button
        col_save, col_space = st.columns([1, 4])
        with col_save:
            if st.button("💾 Save Changes", type="primary", use_container_width=True):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()

                    # Update changes
                    for idx, row in edited_df.iterrows():
                        # We must query by ID to ensure we update the correct row regardless of filtering
                        cursor.execute('''
                            UPDATE jobs
                            SET applied_status = ?, notes = ?, resume_generated = ?
                            WHERE id = ?
                        ''', (row['applied_status'], row['notes'], row['resume_generated'], row['id']))

                    conn.commit()
                    conn.close()
                    st.toast("Database updated successfully!", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")

# ================= TAB 3: ANALYTICS & TOOLS (Actions) =================
with tab3:
    col_tools, col_charts = st.columns([1, 2])

    # --- LEFT: TOOLS ---
    with col_tools:
        st.subheader("🛠️ Agent Actions")

        with st.container(border=True):
            st.write("resume_generator.py")
            job_url_input = st.text_input("Job URL", placeholder="Paste link here...")
            company_name = st.text_input("Company", placeholder="e.g. Sony")

            if st.button("🚀 Generate Tailored CV", use_container_width=True):
                if job_url_input and company_name:
                    with st.spinner("Analyzing job description..."):
                        # Placeholder for your logic
                        st.info(f"Command to run:\n`python apply.py --jd {job_url_input} --company {company_name}`")
                else:
                    st.error("Missing input data.")

        st.write("") # Spacer

        with st.container(border=True):
            st.write("Database Maintenance")
            if st.button("📥 Export to CSV", use_container_width=True):
                 if not df_jobs.empty:
                    csv = df_jobs.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Click to Download",
                        csv,
                        "jobs_export.csv",
                        "text/csv",
                        key='download-csv'
                    )

            if st.button("🗑️ Clean Old Jobs", use_container_width=True):
                st.warning("This requires admin confirmation (feature mocked).")

    # --- RIGHT: CHARTS ---
    with col_charts:
        st.subheader("📊 Application Insights")

        if not df_jobs.empty:
            # 1. Status Donut Chart
            status_counts = df_jobs['applied_status'].value_counts().reset_index()
            status_counts.columns = ['status', 'count']

            chart_donut = alt.Chart(status_counts).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="count", type="quantitative"),
                color=alt.Color(field="status", type="nominal"),
                tooltip=["status", "count"]
            ).properties(title="Pipeline Status")

            # 2. Jobs Found Over Time (Heatmap/Bar)
            df_jobs['date_only'] = df_jobs['date_found'].dt.date
            date_counts = df_jobs.groupby('date_only').size().reset_index(name='jobs')

            chart_bar = alt.Chart(date_counts).mark_bar().encode(
                x='date_only:T',
                y='jobs:Q',
                tooltip=['date_only', 'jobs']
            ).properties(title="Jobs Found Timeline")

            c1, c2 = st.columns(2)
            with c1: st.altair_chart(chart_donut, use_container_width=True)
            with c2: st.altair_chart(chart_bar, use_container_width=True)

        else:
            st.write("Not enough data for analytics.")

# Footer
st.markdown("---")
st.caption(f"🚀 Job Sniper Dashboard v2.0 | Built for Japanese Market 2026")