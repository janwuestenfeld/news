"""Merge the 5-minute chunks of one day into one file, or unpack chunks / day files into the archive layout.

  python merge_day.py merge OUT.jsonl.gz CHUNK [CHUNK ...]
      one line per post, repeats dropped (same source and post id / uri / address), sorted by source then fetch time
  python merge_day.py unpack DIR FILE [FILE ...]
      appends the posts to DIR/telegram/<channel>_full.jsonl, DIR/bluesky/<source>_full.jsonl and
      DIR/pulls/<site>.jsonl (the layout the engine reads), skipping posts already in the file
Prints counts only.
"""
import gzip, json, os, sys


def key(o):
    r = o["rec"]
    if o["platform"] == "bs":
        return (o["src"], (r.get("post") or {}).get("uri", "") + ("|r" if r.get("reason") else ""))
    return (o["src"], str(r.get("id") if o["platform"] == "tg" else r.get("url")))


def read(files):
    for f in files:
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for ln in fh:
                try:
                    yield json.loads(ln)
                except Exception:
                    pass


def merge(out, files):
    seen, rows = set(), []
    for o in read(files):
        k = key(o)
        if k in seen:
            continue
        seen.add(k); rows.append(o)
    rows.sort(key=lambda o: (o["src"], o["fetched_utc"]))
    with gzip.open(out, "wt", encoding="utf-8") as fo:
        for o in rows:
            fo.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(json.dumps({"files": len(files), "posts": len(rows)}))


def unpack(d, files):
    have, n = {}, 0
    for o in read(files):
        p = o["platform"]
        sub, fn = {"tg": ("telegram", o["src"] + "_full.jsonl"), "bs": ("bluesky", o["src"] + "_full.jsonl"),
                   "web": ("pulls", o["src"] + ".jsonl")}[p]
        path = os.path.join(d, sub, fn)
        if path not in have:
            os.makedirs(os.path.dirname(path), exist_ok=True); s = set()
            if os.path.exists(path):
                for ln in open(path, encoding="utf-8"):
                    try:
                        r = json.loads(ln); s.add(key({"platform": p, "src": o["src"], "rec": r})[1])
                    except Exception:
                        pass
            have[path] = s
        k = key(o)[1]
        if k in have[path]:
            continue
        have[path].add(k)
        with open(path, "a", encoding="utf-8") as fo:
            fo.write(json.dumps(o["rec"], ensure_ascii=False) + "\n")
        n += 1
    print(json.dumps({"files": len(files), "appended": n, "archives": len(have)}))


if __name__ == "__main__":
    if sys.argv[1] == "merge":
        merge(sys.argv[2], sys.argv[3:])
    else:
        unpack(sys.argv[2], sys.argv[3:])
