"""News Pulse, collection test: one run fetches every source's new posts since the last run and writes them to one
compressed chunk file. Nothing is scored or published.

  python collect_run.py --state state.json --out OUTDIR [--seed seed_state.json] [--budget 240]

Sources: sources.json (built by make_seed.py from conf/sources_results.csv: the index panel plus accruing, backup and
announcement sources, and four website sources). Paths:
  Telegram  public web preview t.me/s/<channel>?after=<id> (parser = collect/collect.py parse(), unchanged)
  Bluesky   public API app.bsky.feed.getAuthorFeed (same call as collect/bluesky_pull.py: limit=100, posts_no_replies)
  websites  the live ends of pulls/pull_new_sources.py (copy in collect/): Trading Economics stream, Interfax next ids,
            investingLive weekly sitemap, BNO yearly sitemap; article pages read for title and time (same meta() rule)
Writes OUTDIR/chunk_<UTC stamp>.jsonl.gz (only when there are new posts) (one line per new post: {"src", "platform", "fetched_utc", "rec": <raw record as
the archives store it>}), OUTDIR/state_new.json (last id / time / recently seen keys per source, no text) and
OUTDIR/health.json (per source: last success, consecutive failures, last status). The log prints per source only
platform, status, new posts, requests and seconds; never text.
"""
import argparse, datetime as dt, gzip, json, os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor
import requests

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "collect"))
import collect as TG                      # Telegram parser (unchanged)
import pull_new_sources as WS             # website helpers: meta(), ts(), iso(), urls_with_lastmod()

UA = {"User-Agent": "news-pulse-collector/1.0 (research; github.com/janwuestenfeld/news)"}
BSKY = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
BS_KEEP_H = 48            # Bluesky: keys of posts seen in the last 48 h are kept to drop repeats
BS_FIRST_PAGES = int(os.environ.get("BS_FIRST_PAGES", 30))       # pages per account when catching up from the seed (100 posts a page)
BS_PAGES = 5
TG_PAGES = 60             # 20 posts a page
WEB_PAGES = 25            # article pages per website and run (the rest follows next run)
T0 = time.time()


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def stamp(t=None):
    return (t or now_utc()).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url, timeout=25, tries=3, pause=3):
    """returns (status code or error name, text)"""
    code = None
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            code = r.status_code
            if code == 200:
                return 200, r.text
            if code in (404, 410):
                return code, None
            if code == 429:
                time.sleep(min(20, 5 * (k + 1)))
                continue
        except Exception as e:
            code = type(e).__name__
        time.sleep(pause * (k + 1))
    return code, None


class Budget:
    def __init__(self, s):
        self.end = T0 + s

    def left(self):
        return self.end - time.time()


# ---------------------------------------------------------------- Telegram
def tg_source(s, st, B):
    t0 = time.time(); ch = s["channel"]; after = st.get(ch); new = {}; n_req = 0; code = None
    if after is None:                      # no state: start from the newest page
        code, txt = get(f"https://t.me/s/{ch}"); n_req += 1
        posts = TG.parse(txt) if txt else []
        for p in posts:
            new[p["id"]] = p
    else:
        while n_req < TG_PAGES and B.left() > 20:
            code, txt = get(f"https://t.me/s/{ch}?after={after}"); n_req += 1
            if txt is None:
                break
            posts = [p for p in TG.parse(txt) if p["id"] > after]
            if not posts:
                break
            for p in posts:
                new.setdefault(p["id"], p)
            after = max(p["id"] for p in posts)
            time.sleep(1.0)
    R = [new[k] for k in sorted(new)]
    ok = code == 200
    if R:
        st[ch] = R[-1]["id"]
    elif ok and after is not None:
        st[ch] = after
    return R, dict(status=code, new=len(R), req=n_req, secs=round(time.time() - t0, 1), ok=ok,
                   complete=ok and n_req < TG_PAGES)


# ---------------------------------------------------------------- Bluesky
def bs_source(s, st, B):
    """newest posts down to 2 h before the newest post already seen; if the page cap stops the walk earlier (catching
    up after a gap), the walk is continued from where it stopped in the next runs (bf_cursor) until it reaches the gap's
    start, so no post in between is lost"""
    t0 = time.time(); name = s["src"]; o = st.setdefault(name, {})
    seen = o.setdefault("seen", {})                      # rkey -> createdAt (ISO), last 48 h
    last = o.get("last_t") or stamp(now_utc() - dt.timedelta(hours=24))
    floor = (dt.datetime.fromisoformat(last.replace("Z", "+00:00")) - dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    n_req, code, new = 0, None, []

    def walk(cursor, floor, cap):
        nonlocal n_req, code
        pages = 0
        while pages < cap and B.left() > 15:
            url = f"{BSKY}?actor={s['actor']}&limit=100&filter=posts_no_replies"
            if cursor:
                url += "&cursor=" + requests.utils.quote(cursor)
            code, txt = get(url); n_req += 1; pages += 1
            if txt is None:
                return cursor, False
            d = json.loads(txt); feed = d.get("feed", []); oldest = None
            for item in feed:
                p = item.get("post", {}); ca = (p.get("record") or {}).get("createdAt", "")[:19]
                rk = p.get("uri", "").rsplit("/", 1)[-1] + ("|r" if item.get("reason") else "")
                oldest = ca if oldest is None or ca < oldest else oldest
                if rk in seen or ca < floor:
                    continue
                seen[rk] = ca; new.append(item)
            cursor = d.get("cursor")
            if not feed or not cursor or (oldest or "") < floor:
                return None, True
            time.sleep(0.2)
        return cursor, False

    first = "pages_done" not in o
    cur, done = walk(None, floor, BS_FIRST_PAGES if first else BS_PAGES)
    if code == 200 and not done and cur and "bf_cursor" not in o:
        o["bf_cursor"], o["bf_floor"] = cur, floor          # walk stopped before the gap's start: continue next run
    elif "bf_cursor" in o and code == 200 and B.left() > 30:
        cur2, done2 = walk(o["bf_cursor"], o["bf_floor"], BS_FIRST_PAGES)
        if done2:
            o.pop("bf_cursor"); o.pop("bf_floor")
        elif cur2:
            o["bf_cursor"] = cur2
    ok = code == 200
    if ok:
        o["pages_done"] = 1
        if seen:
            o["last_t"] = max(max(seen.values()) + "Z", o.get("last_t") or "")
        cut = (now_utc() - dt.timedelta(hours=BS_KEEP_H)).strftime("%Y-%m-%dT%H:%M:%S")
        o["seen"] = {k: v for k, v in seen.items() if v >= cut}
    return new, dict(status=code, new=len(new), req=n_req, secs=round(time.time() - t0, 1), ok=ok,
                     catching_up="bf_cursor" in o)


# ---------------------------------------------------------------- websites
def web_rec(src, url, t, raw, title, id_=None):
    return dict(source=src, id=id_ if id_ is not None else url, url=url, t_utc=t, t_raw=raw, title=(title or "").strip(),
                fetched_utc=stamp())


def article_pages(src, urls, seen, B, pace):
    out, n, code = [], 0, 200
    for u in urls:
        if n >= WEB_PAGES or B.left() < 20:
            break
        c, t = get(u); n += 1; time.sleep(pace)
        if t is None:
            if c in (404, 410):
                seen[u] = stamp()
            else:
                code = c
            continue
        m = WS.meta(t); raw = m.get("article:published_time") or m.get("ld"); v = WS.ts(raw)
        seen[u] = WS.iso(v) or stamp()
        if m.get("og:title"):
            out.append(web_rec(src, u, WS.iso(v), raw, m.get("og:title")))
    return out, n, code


def web_source(s, st, B):
    t0 = time.time(); w = s["site"]; o = st.setdefault(w, {}); R = []; n_req = 0; code = None
    if w == "tradingeconomics":
        last = int(o.get("last_id", 0)); start = 0
        while n_req < 10 and B.left() > 20:
            code, t = get(f"https://tradingeconomics.com/ws/stream.ashx?start={start}&size=100"); n_req += 1
            if t is None:
                break
            arr = json.loads(t); ids = []
            for it in arr:
                i = int(it.get("ID") or 0); ids.append(i)
                if i > last:
                    v = WS.ts(it.get("date"))
                    R.append(web_rec(w, "https://tradingeconomics.com" + (it.get("url") or "") + "#" + str(i), WS.iso(v),
                                     it.get("date"), it.get("title"), id_=i))
            if not arr or min(ids) <= last or last == 0:
                break
            start += 90; time.sleep(6)
        if R:
            o["last_id"] = max(int(r["id"]) for r in R)
        R = list({r["id"]: r for r in R}.values())
    elif w == "interfax":
        i = int(o.get("last_id", 0)) + 1; miss = 0; code = 200
        while miss < 8 and n_req < 40 and B.left() > 20:
            u = f"https://interfax.com/newsroom/top-stories/{i}/"
            c, t = get(u, tries=2); n_req += 1; time.sleep(1.0)
            ti = WS.re.search(r"<title>(.*?)</title>", t, WS.re.S) if t else None
            d = WS.re.search(r"(\d{1,2} \w{3} 20\d\d),? (\d\d:\d\d)", t) if t else None
            if c not in (200, 404, 410):
                code = c
            if not (ti and d):
                miss += 1; i += 1; continue
            miss = 0
            loc = dt.datetime.strptime(d.group(1) + " " + d.group(2), "%d %b %Y %H:%M")
            v = (loc - dt.timedelta(hours=3)).replace(tzinfo=dt.timezone.utc)
            R.append(web_rec(w, u, WS.iso(v), d.group(0) + " site time", WS.html.unescape(ti.group(1).strip()), id_=i))
            o["last_id"] = i; i += 1
    else:
        seen = o.setdefault("seen", {}) if isinstance(o.get("seen"), dict) else {u: stamp() for u in o.get("seen", [])}
        o["seen"] = seen
        today = now_utc().date()
        if w == "investinglive":
            weeks = {(today - dt.timedelta(days=k)).isocalendar()[:2] for k in (0, 3)}
            sm = [f"https://www.investinglive.com/sitemaps/news/articles/{y}-W{wk:02d}.xml" for y, wk in sorted(weeks)]
            pace, keep_d = 2.5, 21
        else:
            sm = [f"https://bnonews.com/?feed=sitemap-posttype-post&m={today.year}"]
            if today.month == 1:
                sm.append(f"https://bnonews.com/?feed=sitemap-posttype-post&m={today.year - 1}")
            pace, keep_d = 1.0, 75
        urls = []
        for u in sm:
            code, x = get(u); n_req += 1
            for loc, lm in WS.urls_with_lastmod(x or ""):
                if w == "bno":
                    m = WS.re.search(r"/(20\d\d)/(\d\d)/", loc)
                    if not m or (dt.date(int(m.group(1)), int(m.group(2)), 1) < (today.replace(day=1) - dt.timedelta(days=32)).replace(day=1)):
                        continue
                if loc not in seen:
                    urls.append(loc)
        R, n2, c2 = article_pages(w, urls[::-1] if w == "bno" else urls, seen, B, pace); n_req += n2
        if c2 != 200:
            code = c2
        cut = stamp(now_utc() - dt.timedelta(days=keep_d))
        o["seen"] = {k: v for k, v in seen.items() if v >= cut or k in set(urls)}
        o["pending"] = max(0, len([u for u in urls if u not in seen]))
    return R, dict(status=code, new=len(R), req=n_req, secs=round(time.time() - t0, 1), ok=code == 200)


# ---------------------------------------------------------------- run
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--seed", default=os.path.join(HERE, "seed_state.json")); ap.add_argument("--budget", type=float, default=240)
    ap.add_argument("--only", default="", help="comma list of platforms (tg,bs,web) for a test")
    a = ap.parse_args()
    B = Budget(a.budget); os.makedirs(a.out, exist_ok=True)
    if os.path.exists(a.state) and os.path.getsize(a.state) > 10:
        S = json.load(open(a.state)); origin = "state"
    else:
        S = json.load(open(a.seed)); origin = "seed"
        S["bs"] = {k: {"last_t": v} for k, v in S.get("bs", {}).items()}
    for k in ("tg", "bs", "web", "health"):
        S.setdefault(k, {})
    SRC = json.load(open(os.path.join(HERE, "sources.json")))
    only = set(a.only.split(",")) if a.only else {"tg", "bs", "web"}
    res, lock = {}, threading.Lock()

    def run(s):
        f = {"tg": tg_source, "bs": bs_source, "web": web_source}[s["platform"]]
        try:
            R, info = f(s, S[s["platform"]], B)
        except Exception as e:
            R, info = [], dict(status=type(e).__name__, new=0, req=0, secs=0, ok=False)
        with lock:
            res[s["src"]] = (s, R, info)

    tg = [s for s in SRC if s["platform"] == "tg" and "tg" in only]
    bs = [s for s in SRC if s["platform"] == "bs" and "bs" in only]
    web = [s for s in SRC if s["platform"] == "web" and "web" in only]
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(lambda L=web: [run(s) for s in L])]                  # websites, one after another
        futs.append(ex.submit(lambda L=tg: [run(s) for s in L]))               # Telegram, one channel at a time
        for s in bs:                                                           # Bluesky, four at a time
            futs.append(ex.submit(run, s))
        for f in futs:
            f.result()
    t_end = now_utc(); fetched = stamp(t_end)
    chunk = os.path.join(a.out, f"chunk_{t_end.strftime('%Y%m%dT%H%M%SZ')}.jsonl.gz")
    n_all = 0
    with gzip.open(chunk, "wt", encoding="utf-8") as fo:
        for name in sorted(res):
            s, R, info = res[name]
            for r in R:
                fo.write(json.dumps({"src": name, "platform": s["platform"], "fetched_utc": fetched, "rec": r}, ensure_ascii=False) + "\n")
                n_all += 1
    H = S["health"]
    for name, (s, R, info) in res.items():
        h = H.setdefault(name, {"fails": 0})
        h["last_status"] = info["status"]; h["last_new"] = info["new"]
        if info["ok"]:
            h["fails"] = 0; h["last_ok_utc"] = fetched
            if info["new"]:
                h["last_new_utc"] = fetched
        else:
            h["fails"] = h.get("fails", 0) + 1
    S["last_run_utc"] = fetched; S["runs"] = S.get("runs", 0) + 1
    json.dump(S, open(os.path.join(a.out, "state_new.json"), "w"), separators=(",", ":"))
    json.dump({"last_run_utc": fetched, "runs": S["runs"], "sources": H}, open(os.path.join(a.out, "health.json"), "w"), indent=0)
    # log: counts, status and seconds only
    print(f"start from: {origin}")
    print(f"{'platform':8} {'source':22} {'status':>8} {'new':>5} {'req':>4} {'secs':>6}")
    for name in sorted(res, key=lambda n: (res[n][0]["platform"], n)):
        s, R, info = res[name]
        print(f"{s['platform']:8} {name:22} {str(info['status']):>8} {info['new']:>5} {info['req']:>4} {info['secs']:>6}")
    bad = [n for n, (s, R, i) in res.items() if not i["ok"]]
    size = os.path.getsize(chunk)
    if n_all == 0:
        os.remove(chunk); size = 0
    print(f"TOTAL new={n_all} sources={len(res)} failed={len(bad)} seconds={round(time.time() - T0, 1)} chunk_bytes={size}")
    stale = [n for n, h in H.items() if h.get("fails", 0) >= 36]
    if stale:
        print(f"WARNING sources failing for 3 h or more: {len(stale)}")


if __name__ == "__main__":
    main()
