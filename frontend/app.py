"""Streamlit front end. Run with: make app"""

import re
from urllib.parse import urlparse

import streamlit as st

from profiler.llm import DEFAULT_MODEL, list_models
from profiler.pipeline import ProfileResult, profile_url

st.set_page_config(page_title="Portfolio Profiler", page_icon="🔎", layout="wide")
st.title("Portfolio Profiler")
st.caption(
    "Reads a portfolio website (requests + BeautifulSoup, Selenium when the site needs JavaScript) "
    "and asks an Ollama model who the person is and what they do."
)


def show_profile(result: ProfileResult) -> None:
    profile = result.profile
    st.divider()
    st.header(profile.name or result.url)
    if profile.headline:
        st.subheader(profile.headline)
    details = " · ".join(part for part in (profile.location, profile.email) if part)
    if details:
        st.caption(details)
    if profile.summary:
        st.write(profile.summary)
    if profile.skills:
        st.markdown("**Skills:** " + ", ".join(profile.skills))

    if profile.experience:
        st.markdown("### Experience")
        for job in profile.experience:
            dates = " – ".join(part for part in (job.start, job.end) if part)
            st.markdown(f"**{job.title or 'Role'}** · {job.company or 'Unknown'}" + (f" ({dates})" if dates else ""))
            if job.description:
                st.write(job.description)

    if profile.education:
        st.markdown("### Education")
        for item in profile.education:
            st.markdown(" · ".join(part for part in (item.degree, item.institution, item.years) if part))

    if profile.projects:
        st.markdown("### Projects")
        for project in profile.projects:
            st.markdown(f"**{project.name or 'Project'}**" + (f" – {project.url}" if project.url else ""))
            if project.description:
                st.write(project.description)

    if profile.links:
        st.markdown("### Links")
        for link in profile.links:
            st.markdown(f"- {link}")

    browser_note = "browser used" if result.used_browser else "plain requests only"
    st.caption(f"Pages read: {len(result.pages)} ({browser_note})")
    with st.expander("Raw JSON and pages read"):
        st.json(profile.model_dump())
        st.write(result.pages)

    host = re.sub(r"\W+", "_", urlparse(result.url).netloc.removeprefix("www."))
    st.download_button(
        "Download JSON",
        profile.model_dump_json(indent=2),
        file_name=f"{host}.json",
        mime="application/json",
        key=f"download-{result.url}",
    )


with st.sidebar:
    st.header("Settings")
    installed = list_models()
    options = installed if DEFAULT_MODEL in installed else [DEFAULT_MODEL, *installed]
    model = st.selectbox("Ollama model", options)
    if not installed:
        st.warning("Couldn't list models from Ollama. Is it running?")
    max_pages = st.slider("Max pages per site", 1, 10, 5)

urls_text = st.text_area("Portfolio URLs (one per line)", placeholder="https://drbipinnepal.com/", height=110)

if st.button("Analyze", type="primary"):
    urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
    if not urls:
        st.warning("Enter at least one URL.")
    else:
        st.session_state["results"] = {}
        for url in urls:
            with st.status(f"Analyzing {url}", expanded=True) as status:
                try:
                    result = profile_url(url, model, max_pages, progress=st.write)
                except Exception as exc:  # show the problem instead of crashing the page
                    status.update(label=f"Failed: {url}", state="error")
                    st.error(str(exc))
                else:
                    status.update(label=f"Done: {url}", state="complete", expanded=False)
                    st.session_state["results"][result.url] = result

for saved_result in st.session_state.get("results", {}).values():
    show_profile(saved_result)
