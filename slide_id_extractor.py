#!/usr/bin/env python3

import os
import sys

import requests


def request(method, url, **kwargs):
    status = ""
    body = ""

    try:
        r = requests.request(method, url, **kwargs)
        status = r.status_code
        body = r.text

        if 200 <= r.status_code <= 299:
            return r
        else:
            raise Exception("Bad status code: ", status)

    except Exception as e:
        print("Request failed")
        print(f"Status: {status}")
        print(f"URL: {url}")
        print(f"Body: {body}")
        status = str(e)

        raise e


def main():

    if len(sys.argv) < 2:
        print(
            """
USAGE
uv run slide_id_extractor.py [course_id]

Requires your access token obtained from Ed, 
and the numerical ID of the course in question.
You can set environment variables ED_TOKEN=<token> 
and ED_HOST=<url> if you don't want to be prompted for them.

Sends a list of lessons and slides in the course, with their IDs, to stdout.
"""
        )
        sys.exit(1)

    token = os.getenv("ED_TOKEN")
    host = os.getenv("ED_HOST")
    if not token:
        prompt = "Enter your Ed access token: "
        token = input(prompt)
    if not host:
        prompt = "Enter your Ed host (default: https://us.edstem.org/api): "
        host = input(prompt)
        if not host:
            host = "https://us.edstem.org/api"
    course_id = sys.argv[1]

    r = request(
        "GET",
        f"{host}/courses/{course_id}/lessons",
        headers={"Authorization": "Bearer " + str(token)},
    )
    lessons = r.json()

    for l in lessons["lessons"]:
        print("Lesson:", l["title"], l["id"])
        r = request(
            "GET",
            f"{host}/lessons/{l['id']}",
            headers={"Authorization": "Bearer " + str(token)},
        )
        ld = r.json()
        for s in ld["lesson"]["slides"]:
            print("    Slide:", s["title"], s["id"])


if __name__ == "__main__":
    main()
