import difflib
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
DATA = Path("data")


def slug(url):
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def normalize(text):
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def load_urls(argv):
    if argv:
        return argv
    lines = Path("targets.txt").read_text(encoding="utf-8").splitlines()
    return [x.strip() for x in lines if x.strip() and not x.startswith("#")]


def main(argv):
    client = TavilyClient()
    result = client.extract(urls=load_urls(argv), extract_depth="basic")
    now = datetime.now(timezone.utc)
    for item in result["results"]:
        url = item["url"]
        text = normalize(item["raw_content"])
        digest = hashlib.sha256(text.encode()).hexdigest()
        folder = DATA / slug(url)
        (folder / "history").mkdir(parents=True, exist_ok=True)
        latest = folder / "latest.json"
        old = json.loads(latest.read_text(encoding="utf-8")) if latest.exists() else None
        if old and old["hash"] == digest:
            print("unchanged:", url)
            continue
        record = {"url": url, "hash": digest, "text": text, "fetched_at": now.isoformat()}
        payload = json.dumps(record)
        latest.write_text(payload, encoding="utf-8")
        (folder / "history" / f"{now:%Y%m%dT%H%M%SZ}.json").write_text(payload, encoding="utf-8")
        if old:
            diff = "\n".join(difflib.unified_diff(
                old["text"].splitlines(), text.splitlines(), lineterm="", n=1))
            print("CHANGED:", url)
            print(diff[:2000])
        else:
            print("first snapshot:", url)
    for bad in result.get("failed_results", []):
        print("FAILED:", bad)


if __name__ == "__main__":
    main(sys.argv[1:])