#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 13 21:16:43 2026

@author: dev
"""

from http.cookies import SimpleCookie
from symbols import (
    EMOJIS,
    sidebar_header
)
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests
import streamlit as st
from streamlit import session_state as ss
from streamlit_autorefresh import st_autorefresh


load_dotenv(override=True)
st_autorefresh(interval=300000, key="refresh")  # every 5 minutes


PROJECT_FILE = "projects.json"


if "editing" not in ss:
    ss.editing = {}


if "projects" not in ss:
    with open(PROJECT_FILE) as f:
        ss.projects = json.load(f)

URLS = ss.projects

TIMEOUT = 10


st.set_page_config(
    page_title="Deployment Health Dashboard",
    page_icon="🩺",
    layout="wide",
)


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


def sidebar():
    st.sidebar.header(sidebar_header)

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


def wake_streamlit(url, initial_headers):
    """Wakes up a sleeping Streamlit app using headers extracted during status check."""
    if 'x-csrf-token' in initial_headers and 'set-cookie' in initial_headers:
        X_CSRF_TOKEN = initial_headers['x-csrf-token']
        cookies = initial_headers['set-cookie']

        cookie = SimpleCookie()
        cookie.load(cookies)
        STREAMLIT_CSRF = cookie["_streamlit_csrf"].value

        headers = {"x-csrf-token": X_CSRF_TOKEN}
        cookies = {"_streamlit_csrf": STREAMLIT_CSRF}
    else:
        headers = {"x-csrf-token": os.environ.get('X_CSRF_TOKEN', '')}
        cookies = {"_streamlit_csrf": os.environ.get('STREAMLIT_CSRF', '')}

    resume_url = url.rstrip("/") + "/api/v2/app/resume"

    try:
        requests.post(resume_url, headers=headers,
                      cookies=cookies, timeout=TIMEOUT)
    except Exception:
        pass  # Suppress wake errors to keep dashboard responsive


def _check_streamlit_status(url, name=None, start=None):
    if start is None:
        start = time.perf_counter()
    if not name:
        name = url

    try:
        response = requests.get(
            url.rstrip("/") + "/api/v2/app/status",
            timeout=TIMEOUT,
        )

        latency = (time.perf_counter() - start) * 1000
        response.raise_for_status()
        payload = response.json()
        raw = payload.get("status")

        if raw in [0, 5, 6]:
            state = "healthy"
        elif raw == 12:
            state = "waking up"
            # Pass the current response headers directly to avoid infinite recursion loops
            wake_streamlit(url, response.headers)
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


def check(name, url):
    start = time.perf_counter()
    hostname = urlparse(url).hostname or ""

    if hostname.endswith(".streamlit.app"):
        return _check_streamlit_status(url, name, start)

    else:
        try:
            response = requests.get(
                url,
                timeout=TIMEOUT if 'render' not in hostname else 120,
                allow_redirects=True,
            )

            latency = (time.perf_counter() - start) * 1000
            state = "healthy" if response.status_code == 200 else "unhealthy"

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


def display_status(result: dict, show_iframe: bool = False):
    if result["status"] == "healthy":
        icon = "🟢"
    elif result["status"] in ["timeout", "waking up"]:
        icon = "🟡"
    else:
        icon = "🔴"

    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"### {icon} {result['name']} (`{result['status']}`)")
            st.write(result["url"])
        with col2:
            st.link_button("Open", result["url"])

        c1, c2, c3 = st.columns(3)
        status_text = {200: "OK", 404: "Not Found",
                       500: "Server Error"}.get(result["code"], "")
        c1.metric("HTTP", result["code"], status_text)

        if result["latency"]:
            lat = result["latency"]
            delta = "🟢 Fast" if lat < 1000 else "🟡 Warm" if lat < 3000 else "🔴 Cold Start"
            c2.metric("Latency", f"{lat:.0f} ms", delta)


# --- MAIN RENDER BLOCK ---
sidebar()

st.title("🩺 Deployment Health Dashboard")

if not URLS:
    st.info(
        "No projects added yet. Use the sidebar to add your first project deployment.")
else:
    # Use modern st.status layout block to handle multi-threading errors cleanly
    with st.status("Checking deployment health...", expanded=True) as status_box:
        with ThreadPoolExecutor(max_workers=max(1, len(URLS))) as executor:
            # Map items across the thread pool cleanly
            results = list(executor.map(
                lambda item: check(item[0], item[1]), URLS.items()))

        status_box.update(label="All checks completed!",
                          state="complete", expanded=False)

    # Render results grid
    for res in results:
        display_status(res)
