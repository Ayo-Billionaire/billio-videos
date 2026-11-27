"""weigh.py <data dir>: store each picture's embedded size in pool/catalog.json ("bytes"), so check_job.py and the writer can refuse pictures over the 2 MB build limit without going online (the writer's sandbox can reach only GitHub)."""
import io, json, sys, zipfile, urllib.request, concurrent.futures as cf
P = sys.argv[1] + "/pool/catalog.json"; cat = json.load(open(P))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/126 Safari/537.36"}
def weight(x):
    try:
        z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(urllib.request.Request(cat[x]["lottie"], headers=UA), timeout=60).read()))
        js = [m for m in z.namelist() if m.endswith(".json") and m.lower() != "manifest.json"]; a = [m for m in js if "animations/" in m] or js
        return x, len(z.read(a[0])) + int(sum(z.getinfo(m).file_size for m in z.namelist() if not m.endswith(".json")) * 1.37)
    except Exception: return x, None
todo = [x for x in cat if not cat[x].get("bytes")]; done = 0
with cf.ThreadPoolExecutor(16) as ex:
    for x, w in ex.map(weight, todo):
        if w: cat[x]["bytes"] = w; done += 1
json.dump(cat, open(P, "w"), indent=0)
print(f"weighed {done} of {len(todo)}; over 1.9 MB: {sum(1 for v in cat.values() if v.get('bytes', 0) > 1_900_000)}; total {len(cat)}")
