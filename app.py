#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 13 21:16:43 2026

@author: dev
"""

from urllib.parse import urlparse
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests
import streamlit as st
from streamlit import session_state as ss
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=300000, key="refresh")  # every 5 minutes


# ==========================================================
# CONFIG
# ==========================================================


PROJECT_FILE = "projects.json"


if "editing" not in ss:
    ss.editing = {}


def save_projects():

    ss.projects = URLS

    with open(PROJECT_FILE, "w") as f:
        json.dump(URLS, f, indent=4)


def start_edit(name=None):
    ss["editing"] = {
        "original": name,
        "name": name or "",
        "url": URLS.get(name, "") if name else "",
    }


if "projects" not in ss:

    with open(PROJECT_FILE) as f:
        ss.projects = json.load(f)

URLS = ss.projects

TIMEOUT = 15

# ==========================================================
# PAGE
# ==========================================================

st.set_page_config(
    page_title="Deployment Health Dashboard",
    page_icon="🩺",
    layout="wide",
)


def sidebar():
    st.sidebar.header("⚙️ Projects")

    title = (
        "✏ Edit Project"
        if "editing" in ss
        else "➕ Add Project"
    )

    st.sidebar.subheader(title)

    if st.sidebar.button("➕ Add Project", use_container_width=True):
        start_edit()

    if ss["editing"]:

        st.sidebar.divider()

        name = st.sidebar.text_input(
            "Project Name",
            value=ss["editing"]["name"],
        )

        url = st.sidebar.text_input(
            "URL",
            value=ss["editing"]["url"],
        )

        c1, c2 = st.sidebar.columns(2)

        if c1.button("💾 Save", use_container_width=True):

            old = ss["editing"]["original"]

            if old is not None and old != name:
                del URLS[old]

            URLS[name] = url

            save_projects()

            del ss["editing"]

            st.rerun()

        if c2.button("Cancel", use_container_width=True):

            del ss["editing"]

            st.rerun()

    else:

        st.sidebar.divider()

        for project in sorted(URLS):

            with st.sidebar.container(border=True):

                EMOJIS = {
                    "OpenBalancer": "🚀",
                    "Portfolio": "🌐",
                    "Finance Toolkit": "💰",
                    "Ethical AI Dashboard": "⚖️",
                    "RAG4ALL": "📚",
                }

                st.markdown(
                    f"**{EMOJIS.get(project,'📦')} {project}**"
                )
                st.caption(URLS[project])

                c1, c2 = st.sidebar.columns(2)

                if c1.button("✏ Edit", key=f"edit_{project}"):

                    start_edit(project)
                    st.rerun()

                if c2.button("🗑 Delete", key=f"delete_{project}"):

                    del URLS[project]

                    save_projects()

                    st.rerun()


def wake_streamlit(url):

    url = url.rstrip("/") + "/api/v2/app/resume"

    headers = {
        "x-csrf-token": "NFBIVFNobWkxRU84M1BuWHBhNTJDOGRXdFRrOVpUMjZiGBEsMgcfE10gHk9GBjsBNhR/eS1OCwMzATkAIy5IVA==",
    }

    cookies = {
        "_streamlit_csrf": "MTc4NDMxNjQyOXxJbFpyYUZwbFIwWjJZMjV3YzFwV1JqTmtWbHBXVjFWYU1WTnJkSFZrYlRsVlVqRldVMDlZYkRabGJVazlJZz09fLo1j7A8nsBGpmdTDKBFCNQPxcuqbUc0_kC87tL7FFjr",
    }

    requests.post(url,
                  headers=headers,
                  cookies=cookies)


def _check_streamlit_status(name, url, start):

    try:

        response = requests.get(
            url.rstrip("/") + "/api/v2/app/status",
            timeout=TIMEOUT,
        )

        latency = (time.perf_counter() - start) * 1000

        response.raise_for_status()

        payload = response.json()

        raw = payload.get("status")

        if raw in [0, 5]:
            state = "healthy"

        elif raw == 12:
            state = "sleeping"
            wake_streamlit(url)

        else:
            state = f"streamlit:{raw}"

        return {
            "name": name,
            "url": url,
            "status": state,
            "code": response.status_code,
            "streamlit_status": raw,
            "latency": latency,
            "headers": dict(response.headers),
            "time": datetime.now().strftime("%H:%M:%S"),
        }

    except requests.exceptions.Timeout:

        return {
            "name": name,
            "url": url,
            "status": "timeout",
            "code": "-",
            "latency": None,
            "headers": {},
            "time": datetime.now().strftime("%H:%M:%S"),
        }


def check(name, url):

    start = time.perf_counter()

    hostname = urlparse(url).hostname or ""

    if hostname.endswith(".streamlit.app"):

        try:
            return _check_streamlit_status(name, url, start)

        except Exception as e:

            return {
                "name": name,
                "url": url,
                "status": "error",
                "code": str(type(e).__name__),
                "latency": None,
                "headers": {},
                "time": datetime.now().strftime("%H:%M:%S"),
            }

    else:

        try:
            response = requests.get(
                url,
                timeout=TIMEOUT,
                allow_redirects=True,
            )

            latency = (time.perf_counter() - start) * 1000

            if response.status_code == 200:
                state = "healthy"

            else:
                state = "unhealthy"

            return {
                "name": name,
                "url": url,
                "status": state,
                "code": response.status_code,
                "latency": latency,
                "headers": dict(response.headers),
                "time": datetime.now().strftime("%H:%M:%S"),
            }

        except requests.exceptions.Timeout:

            return {
                "name": name,
                "url": url,
                "status": "timeout",
                "code": "-",
                "latency": None,
                "headers": {},
                "time": datetime.now().strftime("%H:%M:%S"),
            }

        except Exception as e:

            return {
                "name": name,
                "url": url,
                "status": "error",
                "code": str(type(e).__name__),
                "latency": None,
                "headers": {},
                "time": datetime.now().strftime("%H:%M:%S"),
            }


def display_status(result: dict,
                   show_iframe: bool = False):

    if result["status"] == "healthy":
        icon = "🟢"
        colour = "green"

    elif result["status"] == "timeout":
        icon = "🟡"
        colour = "orange"

    else:
        icon = "🔴"
        colour = "red"

    with st.container(border=True):

        col1, col2 = st.columns([4, 1])

        with col1:

            st.markdown(
                f"### {icon} {result['name']}"
            )

            st.write(result["url"])

        with col2:

            st.link_button("Open", result["url"])

        c1, c2, c3 = st.columns(3)

        status_text = {
            200: "OK",
            404: "Not Found",
            500: "Server Error",
        }.get(result["code"], "")

        c1.metric(
            "HTTP",
            result["code"],
            status_text,
        )

        if result["latency"]:

            lat = result["latency"]

            if lat < 1000:
                delta = "🟢 Fast"
            elif lat < 3000:
                delta = "🟡 Warm"
            else:
                delta = "🔴 Cold Start"

            c2.metric(
                "Latency",
                f"{lat:.0f} ms",
                delta,
            )

        else:

            c2.metric(
                "Latency",
                "--",
            )

        c3.metric(
            "Checked",
            result["time"],
        )

        if result["status"] == "healthy":

            st.success("Healthy")

        elif result["status"] == "timeout":

            st.warning("Waiting / Timed out")

        else:

            st.error("Unhealthy")

        with st.expander("Details"):

            st.write(f"**Status:** {result['status']}")
            st.write(f"**HTTP:** {result['code']}")
            st.write(f"**Latency:** {result['latency']:.0f} ms")
            st.write(f"**Checked:** {result['time']}")

            with st.expander("Headers"):
                st.json(result["headers"])

        if show_iframe:

            try:
                st.iframe(
                    result["url"],
                    height=600,
                )

            except:
                st.info("Embedding is not supported by this app")


def show_summary(results: dict):

    healthy = sum(r["status"] == "healthy" for r in results)
    unhealthy = len(results) - healthy

    latencies = [r["latency"] for r in results if r["latency"]]

    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Projects", len(results))
    c2.metric("Healthy", healthy)
    c3.metric("Issues", unhealthy)
    c4.metric("Avg Latency", f"{avg_latency:.0f} ms")

    st.divider()


def main():

    st.title("🩺 Deployment Health Dashboard")
    st.caption("Checks the health of all deployed open-source projects.")

    left, right = st.columns([1, 5])

    with left:
        if st.button("🔄 Refresh"):
            st.rerun()

    with right:
        show_iframe = st.checkbox("Embed previews (if allowed)", value=False)

    # ==========================================================
    # HEALTH CHECK
    # ==========================================================

    # ==========================================================
    # RUN ALL CHECKS CONCURRENTLY
    # ==========================================================

    with st.spinner("Checking deployments..."):

        with ThreadPoolExecutor(max_workers=len(URLS)) as executor:

            results = list(
                executor.map(
                    lambda item: check(item[0], item[1]),
                    URLS.items(),
                )
            )

    # ==========================================================
    # SUMMARY
    # ==========================================================

    show_summary(results)

    # ==========================================================
    # PROJECT CARDS
    # ==========================================================

    for result in sorted(results, key=lambda x: x["name"]):

        display_status(result, show_iframe)

    st.divider()

    st.caption(
        f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


if __name__ == "__main__":

    sidebar()
    main()
