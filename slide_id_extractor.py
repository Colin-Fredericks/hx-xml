#!/usr/bin/env python3
# ED_TOKEN=<token> ED_HOST='https://us.edstem.org/api' ./script.py [course_id]

import os
import sys
import time
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
    token = os.getenv("ED_TOKEN")
    host = os.getenv("ED_HOST")
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
