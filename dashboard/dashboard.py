"""
Mission Control Dashboard - Streamlit Web Interface
Track job applications, monitor scraper activity, and manage applications.
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os
from pathlib import Path

# Page Config
st.set_page_config(
    page_title="Japan 2026 Job Sniper",
    page_icon="🎯",
    layout="wide"
)

# Initialize database if not exists
def init_database():
    """Create jobs database if it doesn't exist."""
    conn = sqlite3.connect('../shared/jobs.db')
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

init_database()

# Header
st.title("🇯🇵 Japan 2026 Job Sniper: Mission Control")
st.write(f"**Current Status:** Internship at Johnson Controls (Jan - June)")
st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- SECTION 1: THE RADAR (Upcoming Deadlines) ---
st.header("📡 The Radar: Hiring Timeline Tracks")

st.info("💡 **Strategy:** Rakuten usually hires earliest. Use it as a 'warm-up' interview before Sony.")

# Timeline Data (Based on historical patterns)
timeline_data = [
    {
        "Company": "Mercari",
        "Track": "Global Hiring",
        "Status": "🟢 Open Now",
        "Expected Window": "Dec 2024 - May 2025",
        "Priority": "High"
    },
    {
        "Company": "Woven by Toyota",
        "Track": "New Grad 2026",
        "Status": "🟡 Opens Jan 15",
        "Expected Window": "Jan 15 - Jun 30",
        "Priority": "Critical"
    },
    {
        "Company": "Rakuten",
        "Track": "Project Crimson (India/Global)",
        "Status": "🟡 Expected Feb",
        "Expected Window": "Feb 1 - Mar 15",
        "Priority": "Critical"
    },
    {
        "Company": "Sony Group",
        "Track": "Global Recruitment",
        "Status": "🟡 Expected Mar",
        "Expected Window": "Mar 1 - Apr 30",
        "Priority": "Critical"
    },
    {
        "Company": "Preferred Networks",
        "Track": "New Graduate Hiring",
        "Status": "🔴 TBD",
        "Expected Window": "Mar - May (estimated)",
        "Priority": "Medium"
    },
]

df_timeline = pd.DataFrame(timeline_data)

st.dataframe(
    df_timeline,
    column_config={
        "Company": "Target Company",
        "Track": "Hiring Path",
        "Status": "Current Status",
        "Expected Window": "Application Window",
        "Priority": st.column_config.TextColumn("Priority Level")
    },
    hide_index=True,
    use_container_width=True
)

# --- SECTION 2: LIVE FEED (From The Watcher) ---
st.header("🎯 Live Targets (Found by Scraper)")

# Load jobs from database
try:
    conn = sqlite3.connect('../shared/jobs.db')
    query = """
        SELECT id, company, title, date_found, url, applied_status,
               keywords_matched, resume_generated, notes
        FROM jobs
        ORDER BY date_found DESC
    """
    df_jobs = pd.read_sql(query, conn)
    conn.close()

    if len(df_jobs) == 0:
        st.warning("⏳ No jobs found yet. The watcher is still scanning...")
        st.write("Run `python apply.py --watch` to start monitoring job boards.")
        df_jobs = None

except Exception as e:
    st.error(f"Database error: {e}")
    st.write("Creating sample data for demonstration...")

    # Sample data for first-time users
    df_jobs = pd.DataFrame([
        {
            "id": 1,
            "company": "Sony AI",
            "title": "Research Intern (Reinforcement Learning)",
            "date_found": "2025-01-10 14:30",
            "url": "https://ai.sony/careers/research-intern-2026",
            "applied_status": "Pending",
            "keywords_matched": "2026, Intern, Machine Learning",
            "resume_generated": False,
            "notes": ""
        },
        {
            "id": 2,
            "company": "Woven by Toyota",
            "title": "Software Engineer - New Graduate 2026",
            "date_found": "2025-01-12 09:15",
            "url": "https://woven.toyota/en/careers/software-eng-2026",
            "applied_status": "CV Generated",
            "keywords_matched": "New Graduate, 2026, Software",
            "resume_generated": True,
            "notes": "Priority: High - Mobility focus"
        }
    ])

if df_jobs is not None and len(df_jobs) > 0:
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Jobs Found", len(df_jobs))

    with col2:
        pending = len(df_jobs[df_jobs['applied_status'] == 'Pending'])
        st.metric("Pending Action", pending)

    with col3:
        applied = len(df_jobs[df_jobs['applied_status'] == 'Applied'])
        st.metric("Applied", applied)

    with col4:
        interviews = len(df_jobs[df_jobs['applied_status'] == 'Interview'])
        st.metric("Interviews", interviews, delta="+1" if interviews > 0 else "0")

    st.subheader("📋 Job Application Pipeline")

    # Interactive Data Editor
    edited_df = st.data_editor(
        df_jobs,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "company": st.column_config.TextColumn("Company", width="medium"),
            "title": st.column_config.TextColumn("Job Title", width="large"),
            "date_found": st.column_config.TextColumn("Found On", width="small"),
            "url": st.column_config.LinkColumn("Job Link"),
            "applied_status": st.column_config.SelectboxColumn(
                "Status",
                options=["Pending", "CV Generated", "Applied", "Rejected", "Interview", "Offer"],
                required=True,
                width="small"
            ),
            "keywords_matched": st.column_config.TextColumn("Keywords", width="medium"),
            "resume_generated": st.column_config.CheckboxColumn("Resume Ready?"),
            "notes": st.column_config.TextColumn("Notes", width="large")
        },
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True,
        key="job_editor"
    )

    # Save changes button
    if st.button("💾 Save Changes to Database", type="primary"):
        try:
            conn = sqlite3.connect('../shared/jobs.db')
            cursor = conn.cursor()

            for idx, row in edited_df.iterrows():
                cursor.execute('''
                    UPDATE jobs
                    SET applied_status = ?, notes = ?, resume_generated = ?
                    WHERE id = ?
                ''', (row['applied_status'], row['notes'], row['resume_generated'], row['id']))

            conn.commit()
            conn.close()
            st.success("✅ Changes saved successfully!")
        except Exception as e:
            st.error(f"Error saving changes: {e}")

# --- SECTION 3: AUTOMATION ACTIONS ---
st.header("⚙️ Agent Actions")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🤖 Manual Resume Generation")

    job_url_input = st.text_input("Paste Job URL or Description file path:")
    company_name = st.text_input("Company Name:", placeholder="e.g., Sony AI")

    if st.button("Generate Tailored Resume", type="primary"):
        if job_url_input and company_name:
            st.write("🤖 Agent is analyzing job description...")

            with st.spinner("Generating tailored resume..."):
                # This would call your tailor.py script
                st.info(f"""
                **Next Steps:**
                1. Run: `python apply.py --jd {job_url_input} --company "{company_name}"`
                2. Review the generated PDF in `output/` folder
                3. Update status in the table above
                """)

            st.success("✅ Resume generation queued!")
        else:
            st.error("Please provide both job URL/path and company name")

    st.divider()

    st.subheader("📊 Export Application Data")
    if st.button("Download CSV"):
        if df_jobs is not None and len(df_jobs) > 0:
            csv = df_jobs.to_csv(index=False)
            st.download_button(
                label="📥 Download Applications CSV",
                data=csv,
                file_name=f"job_applications_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

with col2:
    st.subheader("🔧 System Health")

    # Check last scraper run
    try:
        conn = sqlite3.connect('../shared/jobs.db')
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, company, status FROM scraper_logs ORDER BY timestamp DESC LIMIT 1")
        last_run = cursor.fetchone()
        conn.close()

        if last_run:
            st.metric("Watcher Last Run", last_run[0])
            st.write(f"**Company:** {last_run[1]}")
            st.write(f"**Status:** {last_run[2]}")
        else:
            st.metric("Watcher Last Run", "Never")
            st.warning("Watcher hasn't run yet. Start it with: `python apply.py --watch`")
    except:
        st.metric("Watcher Last Run", "Unknown")

    # Total jobs scanned
    try:
        conn = sqlite3.connect('../shared/jobs.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cursor.fetchone()[0]
        conn.close()
        st.metric("Total Jobs Scanned", total_jobs)
    except:
        st.metric("Total Jobs Scanned", "0")

    st.divider()

    # Quick actions
    st.subheader("⚡ Quick Actions")

    if st.button("🔄 Refresh Data"):
        st.rerun()

    if st.button("🗑️ Clear Old Jobs (>30 days)"):
        try:
            conn = sqlite3.connect('../shared/jobs.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE date_found < date('now', '-30 days')")
            conn.commit()
            deleted = cursor.rowcount
            conn.close()
            st.success(f"Deleted {deleted} old job entries")
        except Exception as e:
            st.error(f"Error: {e}")

# --- SECTION 4: INSIGHTS & ANALYTICS ---
st.header("📈 Application Analytics")

if df_jobs is not None and len(df_jobs) > 0:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Applications by Company")
        company_counts = df_jobs['company'].value_counts()
        st.bar_chart(company_counts)

    with col2:
        st.subheader("Status Distribution")
        status_counts = df_jobs['applied_status'].value_counts()
        st.bar_chart(status_counts)

# Footer
st.divider()
st.caption("🎯 Job Sniper Dashboard | Built with Streamlit | Last updated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
st.caption("💡 Tip: Keep this dashboard open in a browser tab and refresh periodically to track progress")
