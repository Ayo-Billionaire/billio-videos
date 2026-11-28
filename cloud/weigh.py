"""weigh.py <data dir>: store each picture's embedded size in pool/catalog.json ("bytes"), so check_job.py and the writer can refuse pictures over the 2 MB build limit without going online (the writer's sandbox can reach only GitHub)."""
import base64, io, json, sys, zipfile, urllib.request, concurrent.futures as cf
P = sys.argv[1] + "/pool/catalog.json"; cat = json.load(open(P))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/126 Safari/537.36"}
def weight(x):   # exactly what extract.py writes: the animation json with every image embedded as base64
    try:
        z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(urllib.request.Request(cat[x]["lottie"], headers=UA), timeout=60).read())); names = z.namelist()
        js = [m for m in names if m.endswith(".json") and m.lower() != "manifest.json"]; a = [m for m in js if "animations/" in m] or js
        d = json.loads(z.read(a[0]))
        for y in d.get("assets", []):
            if "p" in y and not str(y["p"]).startswith("data:"):
                f = [m for m in names if m.endswith("/" + y["p"])]
                if f: ext = y["p"].rsplit(".", 1)[-1]; y["p"] = "data:image/%s;base64," % ("jpeg" if ext == "jpg" else ext) + base64.b64encode(z.read(f[0])).decode(); y["u"] = ""; y["e"] = 1
        return x, len(json.dumps(d))
    except Exception: return x, None
todo = [x for x in cat if not cat[x].get("exact")]; done = 0
with cf.ThreadPoolExecutor(16) as ex:
    for x, w in ex.map(weight, todo):
        if w: cat[x]["bytes"] = w; cat[x]["exact"] = 1; done += 1
json.dump(cat, open(P, "w"), indent=0)
print(f"weighed {done} of {len(todo)}; over 1.9 MB: {sum(1 for v in cat.values() if v.get('bytes', 0) > 1_900_000)}; total {len(cat)}")
