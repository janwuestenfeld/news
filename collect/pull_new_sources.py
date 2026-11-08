"""History pull for the new sources found by the X_sources search (6 Nov 2026).
One thread per site, one request per second per site, resumable.
Output: pulls/<source>.jsonl, one line per item:
  {source, id, url, t_utc, t_raw, title, fetched_utc}
Usage: python3 pull_new_sources.py [source ...]   (default: all)
"""
import urllib.request, urllib.error, gzip, re, json, os, sys, time, html, threading, datetime as dt

OUT = os.path.expanduser("~/Documents/WIM_adversarial_review_20261105/pulls/")
UA = "wim-headline-archive/0.1 (research)"
START = dt.datetime(2025, 7, 31, tzinfo=dt.timezone.utc)
LOCK = threading.Lock()

def now(): return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def log(src, msg):
    with LOCK:
        with open(OUT + "pull.log", "a") as f: f.write(f"{now()} {src}: {msg}\n")

class Site:
    PACE = {"tradingeconomics": 6.0, "theblock": 3.0, "investinglive": 2.5}
    def __init__(self, name, pace=None):
        self.name, self.pace, self.last = name, pace or self.PACE.get(name, 1.0), 0.0
        self.path = OUT + name + ".jsonl"
        self.done = set()
        if os.path.exists(self.path):
            for l in open(self.path):
                try: self.done.add(json.loads(l)["url"])
                except Exception: pass
        self.n_new = 0
        log(name, f"start, {len(self.done)} already on file")
    def get(self, url, tries=4):
        for k in range(tries):
            w = self.pace - (time.time() - self.last)
            if w > 0: time.sleep(w)
            self.last = time.time()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
                with urllib.request.urlopen(req, timeout=40) as r:
                    b = r.read()
                    if b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
                    return b.decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                if e.code in (404, 410): return None
                if e.code in (403, 405, 429, 503):
                    log(self.name, f"HTTP {e.code} on {url}; pause {60*(k+1)} s")
                    time.sleep(60 * (k + 1)); continue
                log(self.name, f"HTTP {e.code} on {url}"); time.sleep(5)
            except Exception as e:
                if "Tunnel connection failed: 403" in str(e):
                    return None  # redirect to an off-site host (e.g. SCMP student pages); not a headline
                log(self.name, f"ERR {str(e)[:80]} on {url}"); time.sleep(10 * (k + 1))
        log(self.name, f"GAVE UP {url}")
        return None
    def write(self, url, t_utc, t_raw, title, id_=None):
        with LOCK:
            if url in self.done or not title: return
            self.done.add(url); self.n_new += 1
            self._append(url, t_utc, t_raw, title, id_)
    def _append(self, url, t_utc, t_raw, title, id_):
        rec = dict(source=self.name, id=id_ if id_ is not None else url, url=url, t_utc=t_utc, t_raw=t_raw,
                   title=title.strip(), fetched_utc=now())
        with open(self.path, "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if self.n_new % 500 == 0:
            with open(OUT + "pull.log", "a") as f: f.write(f"{now()} {self.name}: {self.n_new} new items, last {t_utc}\n")

def ts(x):
    if not x: return None
    try:
        v = dt.datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", x.strip()).replace("Z", "+00:00"))
        if v.tzinfo is None: v = v.replace(tzinfo=dt.timezone.utc)
        return v.astimezone(dt.timezone.utc)
    except Exception: return None
def iso(v): return v.strftime("%Y-%m-%dT%H:%M:%SZ") if v else None

def meta(t):
    out = {}
    for key in ["og:title", "article:published_time"]:
        m = (re.search(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*content=["\']([^"\']+)' % re.escape(key), t)
             or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']%s["\']' % re.escape(key), t))
        if m: out[key] = html.unescape(m.group(1))
    m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', t)
    if m: out["ld"] = m.group(1)
    return out

def urls_with_lastmod(xml):
    for blk in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>\s*(.*?)\s*</loc>", blk, re.S)
        lm = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", blk, re.S)
        if loc: yield html.unescape(loc.group(1)), (lm.group(1) if lm else None)

def page_items(s, urls, workers=1):
    """Fetch each article page for og:title and published time."""
    if workers > 1:
        import copy
        todo = [u for u in urls if u not in s.done]
        parts = [todo[i::workers] for i in range(workers)]
        subs = []
        for part in parts:
            w = copy.copy(s); w.last = 0.0   # own pacing, shared done-set and file
            subs.append(threading.Thread(target=page_items, args=(w, part, 1)))
        for t in subs: t.start()
        for t in subs: t.join()
        s.n_new = len(s.done)
        return
    for u in urls:
        if u in s.done: continue
        if "scmp.com/yp/" in u or "scmp.com/posties/" in u: continue  # student/children sections redirect off-site; not headlines
        t = s.get(u)
        if not t: continue
        m = meta(t)
        raw = m.get("article:published_time") or m.get("ld")
        v = ts(raw)
        if v and v < START: continue
        s.write(u, iso(v), raw, m.get("og:title"))

# ---------------- sources ----------------
def kitco():
    s = Site("kitco")
    x = s.get("https://www.kitco.com/static-sitemaps/off-the-wire.xml")
    for blk in re.findall(r"<url>(.*?)</url>", x or "", re.S):
        loc = re.search(r"<loc>(.*?)</loc>", blk); pd_ = re.search(r"<news:publication_date>(.*?)</news:publication_date>", blk)
        ti = re.search(r"<news:title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</news:title>", blk, re.S)
        v = ts(pd_.group(1)) if pd_ else None
        if loc and ti and v and v >= START:
            s.write(loc.group(1), iso(v), pd_.group(1), html.unescape(html.unescape(ti.group(1))))
    log(s.name, f"DONE {s.n_new} new, {len(s.done)} total")

def tradingeconomics():
    s = Site("tradingeconomics"); size, step = 100, 90
    start = max(0, len(s.done) - 300)  # resume near the oldest item on file; new items shift offsets
    while True:
        t = s.get(f"https://tradingeconomics.com/ws/stream.ashx?start={start}&size={size}")
        if not t: break
        try: arr = json.loads(t)
        except Exception: log(s.name, f"bad json at {start}"); break
        if not arr: break
        oldest = None
        for it in arr:
            v = ts(it.get("date"))  # no zone suffix: read as UTC (search's fetch comparison)
            if v and (oldest is None or v < oldest): oldest = v
            if v and v >= START:
                s.write("https://tradingeconomics.com" + (it.get("url") or "") + "#" + str(it.get("ID")),
                        iso(v), it.get("date"), it.get("title"), id_=it.get("ID"))
        if oldest and oldest < START: break
        start += step
    log(s.name, f"DONE {s.n_new} new, {len(s.done)} total")

def interfax():
    s = Site("interfax"); i = 112800; miss = 0
    while miss < 60:
        u = f"https://interfax.com/newsroom/top-stories/{i}/"; i += 1
        if u in s.done: miss = 0; continue
        t = s.get(u)
        if not t: miss += 1; continue
        ti = re.search(r"<title>(.*?)</title>", t, re.S)
        d = re.search(r"(\d{1,2} \w{3} 20\d\d),? (\d\d:\d\d)", t)
        if not (ti and d): miss += 1; continue
        miss = 0
        loc = dt.datetime.strptime(d.group(1) + " " + d.group(2), "%d %b %Y %H:%M")
        v = (loc - dt.timedelta(hours=3)).replace(tzinfo=dt.timezone.utc)  # site time read as Moscow (UTC+3), unconfirmed
        if v >= START: s.write(u, iso(v), d.group(0) + " site time", html.unescape(ti.group(1).strip()), id_=i - 1)
    log(s.name, f"DONE {s.n_new} new, {len(s.done)} total, stopped at id {i}")

def bno():
    s = Site("bno"); urls = []
    for y in (2025, 2026):
        x = s.get(f"https://bnonews.com/?feed=sitemap-posttype-post&m={y}") or ""
        for u, lm in urls_with_lastmod(x):
            m = re.search(r"/(20\d\d)/(\d\d)/", u)
            if m and (int(m.group(1)), int(m.group(2))) >= (2025, 7): urls.append(u)
    log(s.name, f"{len(urls)} article URLs from sitemaps"); page_items(s, urls)
    log(s.name, f"DONE {s.n_new} new, {len(s.done)} total")

def theblock():
    s = Site("theblock"); urls = []; n = 1
    while n < 400:
        x = s.get(f"https://www.theblock.co/sitemap_tbco_post_type_post_{n}.xml")
        if not x or "<url>" not in x: break
        for u, lm in urls_with_lastmod(x):
            m = re.search(r"/(20\d\d)-(\d\d)-(\d\d)-", u)
            if m:
                if (int(m.group(1)), int(m.group(2))) >= (2025, 7): urls.append(u)
            elif lm and ts(lm) and ts(lm) >= START: urls.append(u)
        n += 1
    log(s.name, f"{len(urls)} article URLs from {n-1} sitemaps"); page_items(s, urls)
    log(s.name, f"DONE {s.n_new} new, {len(s.done)} total")

def investinglive():
    s = Site("investinglive"); urls = []
    d = dt.date(2025, 7, 28)
    while d <= dt.date.today():
        y, w, _ = d.isocalendar()
        x = s.get(f"https://www.investinglive.com/sitemaps/news/articles/{y}-W{w:02d}.xml") or ""
        urls += [u for u, lm in urls_with_lastmod(x)]
        d += dt.timedelta(days=7)
    log(s.name, f"{len(urls)} article URLs from weekly sitemaps"); page_items(s, urls)
    log(s.name, f"DONE {s.n_new} new, {len(s.done)} total")

def scmp():
    s = Site("scmp"); urls = []; seen = set()
    mons = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
    y, m = 2025, 8
    while (y, m) <= (dt.date.today().year, dt.date.today().month):
        x = s.get(f"https://www.scmp.com/sitemap/archives/articles/{y}_{mons[m-1]}.xml") or ""
        for u, lm in urls_with_lastmod(x):
            if u not in seen: seen.add(u); urls.append(u)
        m += 1
        if m == 13: y, m = y + 1, 1
    x = s.get("https://www.scmp.com/sitemap/articles.xml") or ""
    for u, lm in urls_with_lastmod(x):
        if u not in seen: seen.add(u); urls.append(u)
    log(s.name, f"{len(urls)} article URLs from monthly sitemaps"); page_items(s, urls, workers=4)
    log(s.name, f"DONE {s.n_new} new, {len(s.done)} total")

def independent():
    s = Site("independent"); d = dt.date(2025, 7, 31)
    while d <= dt.date.today():
        x = s.get(f"https://www.independent.co.uk/sitemaps/sitemap-articles-{d:%Y-%m-%d}.xml") or ""
        page_items(s, [u for u, lm in urls_with_lastmod(x)])
        log(s.name, f"day {d} done, {s.n_new} new so far")
        d += dt.timedelta(days=1)
    log(s.name, f"DONE {s.n_new} new, {len(s.done)} total")

ALL = dict(kitco=kitco, tradingeconomics=tradingeconomics, interfax=interfax, bno=bno,
           theblock=theblock, investinglive=investinglive, scmp=scmp, independent=independent)

if __name__ == "__main__":
    names = sys.argv[1:] or list(ALL)
    def run(n):
        try: ALL[n]()
        except Exception as e: log(n, f"CRASH {e!r}")
    th = [threading.Thread(target=run, args=(n,)) for n in names]
    log("main", f"start {names}")
    for t in th: t.start()
    for t in th: t.join()
    log("main", "all threads finished")
