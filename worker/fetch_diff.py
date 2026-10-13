import difflib
import hashlib
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()
from datetime import datetime, timezone
from pathlib import Path

from tavily import TavilyClient

DATA = Path("data")
DATA.mkdir(exist_ok=True)


def slug(url):
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def main(urls):
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    result = client.extract(urls=urls, extract_depth="basic")
    for item in result["results"]:
        url, text = item["url"], item["raw_content"]
        path = DATA / f"{slug(url)}.json"
        old = json.loads(path.read_text()) if path.exists() else None
        new_hash = hashlib.sha256(text.encode()).hexdigest()
        if old and old["hash"] == new_hash:
            print("unchanged:", url)
            continue
        if old:
            diff = "\n".join(difflib.unified_diff(
                old["text"].splitlines(), text.splitlines(), lineterm="", n=1))
            print("CHANGED:", url)
            print(diff[:2000])
        else:
            print("first snapshot:", url)
        path.write_text(json.dumps({
            "url": url,
            "hash": new_hash,
            "text": text,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }))
    for bad in result.get("failed_results", []):
        print("FAILED:", bad)


if __name__ == "__main__":
    main(sys.argv[1:])