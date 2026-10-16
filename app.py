
import streamlit as st
import requests
import sqlite3
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime
from difflib import unified_diff
from urllib.parse import urlparse

DB_NAME = "website_history.db"

st.set_page_config(
    page_title="Website Change Detector",
    page_icon="🌐",
    layout="wide"
)


# Create permanent database
def setup_database():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_name TEXT NOT NULL,
                url TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                content TEXT NOT NULL,
                checked_at TEXT NOT NULL
            )
        """)


def get_history(url):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("""
            SELECT id, website_name, content_hash, content, checked_at
            FROM snapshots
            WHERE url = ?
            ORDER BY id DESC
        """, (url,)).fetchall()


def save_snapshot(name, url, content_hash, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO snapshots
            (website_name, url, content_hash, content, checked_at)
            VALUES (?, ?, ?, ?, ?)
        """, (name, url, content_hash, content, timestamp))

    return timestamp


setup_database()

st.markdown("""
<style>
.stApp {
    background-color: #f8fafc;
}
h1 {
    color: #1d4ed8;
}
</style>
""", unsafe_allow_html=True)

st.title("🌐 Website Change Detector")
st.write("Monitor public webpages and keep a permanent record of changes.")

st.divider()

with st.sidebar:
    st.header("📌 About")
    st.write("Check websites and compare their content over time.")
    st.write("✅ Permanent history")
    st.write("✅ Change detection")
    st.write("✅ Text comparison")
    st.write("✅ Previous snapshots")

st.subheader("🔎 Monitor a Website")

website_name = st.text_input(
    "Website name",
    placeholder="Example: My favourite website"
)

url = st.text_input(
    "Website URL",
    placeholder="https://example.com"
)

if st.button("🔍 Check Website", type="primary"):
    valid_url = False

    try:
        parsed = urlparse(url.strip())
        valid_url = (
            parsed.scheme in ("http", "https")
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )
    except ValueError:
        valid_url = False

    if not website_name.strip():
        st.error("Please enter a website name.")

    elif not valid_url:
        st.error("Enter a valid HTTP or HTTPS website URL.")

    else:
        try:
            with st.spinner("Checking website..."):
                response = requests.get(
                    url.strip(),
                    timeout=15,
                    headers={"User-Agent": "WebsiteChangeDetector/1.0"}
                )
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                for element in soup(["script", "style", "noscript"]):
                    element.decompose()

                current_text = soup.get_text(" ", strip=True)

                if not current_text:
                    st.error("No readable webpage text was found.")
                    st.stop()

                current_hash = hashlib.sha256(
                    current_text.encode("utf-8")
                ).hexdigest()

            history = get_history(url.strip())

            if not history:
                save_snapshot(
                    website_name.strip(),
                    url.strip(),
                    current_hash,
                    current_text
                )
                st.success("First snapshot saved permanently!")

            elif history[0][2] == current_hash:
                st.success("No text changes detected.")
                st.info("No duplicate snapshot was saved.")

            else:
                previous_text = history[0][3]

                save_snapshot(
                    website_name.strip(),
                    url.strip(),
                    current_hash,
                    current_text
                )

                st.warning("A website change was detected!")

                differences = unified_diff(
                    previous_text.split(),
                    current_text.split(),
                    fromfile="Previous version",
                    tofile="Current version",
                    lineterm=""
                )

                st.subheader("📋 Detected Differences")
                st.code(
                    "\n".join(differences),
                    language="diff"
                )

            with st.expander("📄 View Current Website Text"):
                st.write(current_text[:10000])

        except requests.RequestException as error:
            st.error(f"Website check failed: {error}")

st.divider()

st.subheader("📚 Website History")

history_url = st.text_input(
    "Enter a URL to view its history",
    placeholder="https://example.com",
    key="history_url"
)

if st.button("View History"):
    history = get_history(history_url.strip())

    if not history:
        st.info("No saved history found for this URL.")

    else:
        st.write(f"*{len(history)} saved version(s)*")

        for index, item in enumerate(history):
            snapshot_id, name, content_hash, content, checked_at = item

            with st.expander(
                f"{name} — {checked_at} — Version {snapshot_id}"
            ):
                st.write("*URL:*", history_url)
                st.write("*Content hash:*", content_hash[:16] + "...")
                st.write(content[:5000])

st.caption(
    "Website Change Detector | Python, Streamlit and SQLite"
)