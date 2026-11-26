"""harvest.py <data> [max new=400]: add free LottieFiles animations to the picture pool (the same source and method as the Mac pools).
Reads pool/tags.json and pool/harvest-state.json (next page per tag). New ids are H:<n>. Thumbnail = frame at 45 percent, 170 px, like find_art."""
import concurrent.futures as cf, json, os, re, subprocess, sys, tempfile, urllib.request
D = sys.argv[1]; MAX = int(sys.argv[2]) if len(sys.argv) > 2 else 400
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
BAN = re.compile(r"flag|bitcoin|crypto|india|fathers-day|mothers-day|birthday|christmas|halloween|ramadan|diwali|corona|covid|olympic|blind|church|mosque|cross|bible|quran|pray|gun|weapon|blood|alcohol|beer|wine|cigarette|smok|logo|brand|text|word|letter|loading|spinner|preloader|404|error|ui-|app-|button|icon-set", re.I)
def get(u, b=False):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read()
    return r if b else r.decode("utf8", "ignore").replace("\\u002F", "/").replace("\\/", "/")
cat = json.load(open(D + "/pool/catalog.json")); tags = json.load(open(D + "/pool/tags.json"))
st = json.load(open(D + "/pool/harvest-state.json")) if os.path.exists(D + "/pool/harvest-state.json") else {}
have = {c["slug"] for c in cat.values()}; new = {}
order = sorted(tags, key=lambda t: st.get(t, 1))
for t in order:
    if len(new) >= MAX * 1.3: break
    pg = st.get(t, 1)
    try: s = list(dict.fromkeys(re.findall(r"/free-animation/([a-zA-Z0-9\-]+)", get(f"https://lottiefiles.com/free-animations/{t}" + (f"?page={pg}" if pg > 1 else "")))))
    except Exception: continue
    st[t] = pg + 1 if s else 99
    for x in s:
        if x not in have and x not in new and not BAN.search(x): new[x] = t
print("candidates", len(new))
tmp = tempfile.mkdtemp(); os.makedirs(D + "/pool/thumbs", exist_ok=True)
def one(kv):
    s, t = kv
    try:
        h = get("https://lottiefiles.com/free-animation/" + s)
        m = re.findall(r"https://assets-v2\.lottiefiles\.com/a/[A-Za-z0-9\-]+/[A-Za-z0-9]+\.mp4", h); l = re.findall(r"https://assets-v2\.lottiefiles\.com/a/[A-Za-z0-9\-]+/[A-Za-z0-9]+\.lottie", h)
        if not m or not l: return None
        f = f"{tmp}/{s}.mp4"; open(f, "wb").write(get(m[0], True))
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True).stdout.strip()
        d = float(d) if d else 2.0
        o = f"{tmp}/{s}.jpg"; subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{d * 0.45:.2f}", "-i", f, "-frames:v", "1", "-q:v", "6", "-vf", "scale=170:170:force_original_aspect_ratio=decrease,pad=170:170:(ow-iw)/2:(oh-ih)/2:white", o], capture_output=True)
        os.remove(f)
        return (s, {"slug": s, "tag": t, "lottie": l[0], "page": "https://lottiefiles.com/free-animation/" + s, "used": []}, o) if os.path.exists(o) else None
    except Exception: return None
n = 1 + max([int(k[2:]) for k in cat if k.startswith("H:")] or [0]); added = 0
with cf.ThreadPoolExecutor(8) as ex:
    for r in ex.map(one, list(new.items())[:int(MAX * 1.3)]):
        if not r or added >= MAX: continue
        s, rec, o = r; k = f"H:{n}"; n += 1; added += 1; cat[k] = rec; os.replace(o, f"{D}/pool/thumbs/H_{k[2:]}.jpg")
json.dump(cat, open(D + "/pool/catalog.json", "w"), indent=0); json.dump(st, open(D + "/pool/harvest-state.json", "w"))
print("added", added, "pool now", len(cat), "unused", sum(1 for c in cat.values() if not c["used"]))
