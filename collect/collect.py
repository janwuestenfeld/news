"""Wire Intensity Monitor: incremental collector for the four public Telegram channels.

Reads the public web preview t.me/s/<channel>?after=<id>, which returns the next (up to 20) posts with an id
above <id> in ascending order, skipping ids that do not exist (deleted posts, service messages), so empty id
ranges cost nothing. Pages forward until a page brings no id above the last one. The page parser is the one of
telegram/tg_full2.py (history collector), unchanged, so new records have the same fields.

  collect(since: {abbr: id}) -> ({abbr: DataFrame(id, t, text, ...)}, {abbr: status})

Posts are kept in memory for the pipeline. With --archive DIR (Mac only) the new records are also appended to
DIR/<channel>_full.jsonl, only ids above the largest id already in the file. The workflow never writes text.
"""
import re, html, json, os, sys, time, datetime as dt
import requests
import pandas as pd

CHANNELS = {"WB": "WalterBloomberg", "FJ": "FinancialJuice", "BMN": "BreakingMarketNews", "MF": "marketfeed",
            "WG": "watcherguru", "CR": "clashreport", "CT": "Cointelegraph", "IP": "insiderpaper"}
PAUSE_S = 1.0           # between page requests
MAX_PAGES = 400         # per channel and run (8,000 posts); the rest follows in the next run
TIMEOUT_S = 30


def get(url, tries=4):
    err = None
    for k in range(tries):
        try:
            r = requests.get(url, timeout=TIMEOUT_S)
            if r.status_code == 200:
                return r.text, None
            err = f"http {r.status_code}"
            if r.status_code == 429:
                time.sleep(30 * (k + 1)); continue
        except Exception as e:                      # network error: retried
            err = type(e).__name__
        time.sleep(5 * (k + 1))
    return None, err


def parse(t):
    """telegram/tg_full2.py parse(), unchanged"""
    out = []
    for blk in re.findall(r'<div class="tgme_widget_message_wrap.*?(?=<div class="tgme_widget_message_wrap|\Z)', t, re.S):
        m = re.search(r'data-post="[^/]+/(\d+)"', blk)
        if not m: continue
        tm = re.search(r'<time datetime="([^"]+)"', blk)
        tx = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', blk, re.S)
        vw = re.search(r'<span class="tgme_widget_message_views">([^<]+)</span>', blk)
        fw = re.search(r'tgme_widget_message_forwarded_from_name[^>]*>(.*?)</', blk, re.S)
        text = html.unescape(re.sub(r"<br\s*/?>", "\n", tx.group(1))) if tx else ""
        text = re.sub(r"<[^>]+>", "", text).strip()
        out.append({"id": int(m.group(1)), "t": tm.group(1) if tm else None, "text": text,
                    "views": vw.group(1) if vw else None, "edited": "edited" in blk[:3000] and "tgme_widget_message_meta" in blk,
                    "forwarded_from": html.unescape(re.sub(r"<[^>]+>", "", fw.group(1))).strip() if fw else None,
                    "has_link": bool(tx and "<a " in tx.group(1)), "has_media": ("tgme_widget_message_photo" in blk or "tgme_widget_message_video" in blk),
                    "scraped_utc": dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")})
    return out


def collect_channel(ch, since, max_pages=MAX_PAGES):
    """all posts of channel ch with id > since. Returns (records, status)."""
    recs, after, pages, err, head = {}, int(since), 0, None, None
    while pages < max_pages:
        t, e = get(f"https://t.me/s/{ch}?after={after}")
        pages += 1
        if t is None:
            err = e; break
        posts = [p for p in parse(t) if p["id"] > after]
        if not posts:
            break
        for p in posts:
            recs.setdefault(p["id"], p)
        after = max(p["id"] for p in posts)
        time.sleep(PAUSE_S)
    complete = err is None and pages < max_pages
    R = sorted(recs.values(), key=lambda p: p["id"])
    st = {"channel": ch, "since_id": int(since), "new": len(R), "pages": pages, "complete": complete, "error": err,
          "first_id": R[0]["id"] if R else None, "last_id": R[-1]["id"] if R else None,
          "last_post_utc": R[-1]["t"] if R else None}
    return R, st


def collect(since, archive=None, now=None):
    now = pd.Timestamp(now or dt.datetime.now(dt.timezone.utc))
    posts, status = {}, {}
    for ab, ch in CHANNELS.items():
        if ab not in since:
            continue
        R, st = collect_channel(ch, since[ab])
        D = pd.DataFrame(R, columns=["id", "t", "text", "views", "edited", "forwarded_from", "has_link", "has_media", "scraped_utc"])
        if len(D):
            D["t"] = pd.to_datetime(D.t, utc=True)
        posts[ab] = D
        if archive and R:
            st["archived"] = append_archive(os.path.join(archive, f"{ch}_full.jsonl"), R)
        status[ab] = st
    return posts, status


def append_archive(path, R):
    """append records with an id above the largest id already in the file"""
    top = -1
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                try: top = max(top, json.loads(line)["id"])
                except Exception: pass
    new = [p for p in R if p["id"] > top]
    if new:
        with open(path, "a") as fo:
            for p in new:
                fo.write(json.dumps(p) + "\n")
    return len(new)


def feed_status(meta, status, now):
    """per feed: last post time, gap to now, whether this run reached the channel's newest post"""
    now = pd.Timestamp(now)
    out = {}
    for ab in CHANNELS:
        last = pd.Timestamp(meta["last_t"][ab])
        st = status.get(ab, {})
        out[ab] = {"channel": CHANNELS[ab], "last_id": int(meta["last_id"][ab]), "last_post_utc": str(last),
                   "gap_min": round((now - last).total_seconds() / 60, 1), "new_this_run": st.get("new", 0),
                   "complete": st.get("complete", False), "error": st.get("error")}
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="fetch posts after the given ids (no pipeline); prints status")
    ap.add_argument("--since", nargs="+", help="ABBR=ID, e.g. WB=37707 FJ=144243 (default with --archive: largest id in each file)")
    ap.add_argument("--archive", help="append new records to DIR/<channel>_full.jsonl")
    a = ap.parse_args()
    if a.since:
        since = {k: int(v) for k, v in (s.split("=") for s in a.since)}
    elif a.archive:
        since = {}
        for ab, ch in CHANNELS.items():
            top = -1
            with open(os.path.join(a.archive, f"{ch}_full.jsonl")) as fh:
                for line in fh:
                    try: top = max(top, json.loads(line)["id"])
                    except Exception: pass
            since[ab] = top
    else:
        ap.error("give --since or --archive")
    _, status = collect(since, archive=a.archive)
    print(json.dumps(status, indent=1))
