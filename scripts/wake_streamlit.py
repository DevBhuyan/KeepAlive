#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul 25 00:49:54 2026

@author: dev
"""


from http.cookies import SimpleCookie
import os
import requests
from time import perf_counter
from datetime import datetime


class StreamlitClient:

    def __init__(self, timeout=30):
        self.timeout = timeout

    def status(self,
               url):

        try:

            response = requests.get(
                url.rstrip("/") + "/api/v2/app/status"
            )

            response.raise_for_status()

            payload = response.json()

            raw = payload.get("status")

            if raw in [0, 5]:
                state = "healthy"

            elif raw == 12:
                state = "sleeping"

            else:
                state = f"streamlit:{raw}"

            return {
                "url": url,
                "status": state,
                "code": response.status_code,
                "streamlit_status": raw,
                "headers": dict(response.headers),
                "time": datetime.now().strftime("%H:%M:%S"),
            }

        except requests.exceptions.Timeout:

            return {
                "url": url,
                "status": "timeout",
                "code": "-",
                "headers": {},
                "time": datetime.now().strftime("%H:%M:%S"),
            }

    def _get_auth(self, url):
        status = self.status(url)

        headers = status["headers"]

        if "x-csrf-token" in headers and "set-cookie" in headers:

            cookie = SimpleCookie()
            cookie.load(headers["set-cookie"])

            return (
                headers["x-csrf-token"],
                cookie["_streamlit_csrf"].value,
            )

        return (
            os.environ["X_CSRF_TOKEN"],
            os.environ["STREAMLIT_CSRF"],
        )

    def resume(self, url):
        token, csrf = self._get_auth(url)

        return requests.post(
            url.rstrip("/") + "/api/v2/app/resume",
            headers={
                "x-csrf-token": token,
            },
            cookies={
                "_streamlit_csrf": csrf,
            },
            timeout=self.timeout,
        )


def wake_up(url: str):

    return StreamlitClient().resume(url)


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("url")

    args = parser.parse_args()

    response = wake_up(args.url)

    print(response.status_code)

    raise SystemExit(0 if response.ok else 1)
