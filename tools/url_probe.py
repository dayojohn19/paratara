import re
from urllib import request, error

BASE = "http://127.0.0.1:8000"
SOURCE = "/tmp/project_urls.txt"
OUT = "/tmp/url_probe_results.txt"


def normalize(path: str) -> str:
    path = re.sub(r"<int:[^>]+>", "1", path)
    path = re.sub(r"<slug:[^>]+>", "sample-slug", path)
    path = re.sub(r"<str:[^>]+>", "sample", path)
    path = re.sub(r"<path:[^>]+>", "sample/path", path)
    return path


def collect_paths() -> list[str]:
    paths: list[str] = []
    with open(SOURCE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("/"):
                continue
            path = line.split()[0]
            paths.append(normalize(path))

    seen = set()
    unique = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def probe(path: str):
    url = BASE + path
    try:
        req = request.Request(url, method="GET")
        with request.urlopen(req, timeout=6) as resp:
            return resp.getcode()
    except error.HTTPError as e:
        return e.code
    except Exception:
        return "ERR"


def main():
    paths = collect_paths()
    results = [(path, probe(path)) for path in paths]

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(f"Total tested: {len(results)}\n")
        f.write(f"Network errors: {sum(1 for _, code in results if code == 'ERR')}\n")
        for path, code in results:
            f.write(f"{code}\t{path}\n")

    print(f"Wrote {len(results)} results to {OUT}")


if __name__ == "__main__":
    main()
