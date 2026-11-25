"""Quiet copy for the PUBLIC repo: prints line numbers, seeds and scores, never the words. Signature voice generator (runs in GitHub Actions). Pinned stack: see requirements.lock and spec.json.
One key per job. Each line: Chatterbox with the locked settings, then a whisper word check, retried on other seeds."""
import json, os, re, sys, difflib
import torch, torchaudio
from huggingface_hub import snapshot_download
from chatterbox.tts import ChatterboxTTS
from faster_whisper import WhisperModel
spec = json.load(open("spec.json"))["voice"]
key = sys.argv[1]; lines = json.load(open("lines.json"))[key]; os.makedirs("out", exist_ok=True)
path = snapshot_download("ResembleAI/chatterbox", revision=spec["hf_revision"], allow_patterns=["ve.safetensors", "t3_cfg.safetensors", "s3gen.safetensors", "tokenizer.json", "conds.pt"])
tts = ChatterboxTTS.from_local(path, "cpu")
asr = WhisperModel("small.en", device="cpu", compute_type="int8")
norm = lambda s: re.findall(r"[a-z0-9']+", s.lower().replace("’", "'"))
forced = json.load(open("seeds.json")).get(key, {}) if os.path.exists("seeds.json") else {}
report = {}
for n, text in enumerate(lines, 1):
    best = None; seeds = [forced[str(n)]] if str(n) in forced else spec["seeds"]
    for seed in seeds:
        torch.manual_seed(seed)
        wav = tts.generate(text, audio_prompt_path="michael-ref.wav", exaggeration=spec["exaggeration"], cfg_weight=spec["cfg_weight"], temperature=spec["temperature"])
        p = f"out/raw{n}_{seed}.wav"; torchaudio.save(p, wav, tts.sr)
        segs, _ = asr.transcribe(p, language="en"); heard = " ".join(s.text for s in segs)
        score = difflib.SequenceMatcher(None, norm(text), norm(heard)).ratio()
        print(f"L{n} seed {seed} score {score:.2f}", flush=True)
        if best is None or score > best[0]: best = (score, p, seed)
        if score >= 0.97: break
    os.replace(best[1], f"out/L{n}.wav"); report[n] = {"score": round(best[0], 2), "seed": best[2], "text": text}
    for f in os.listdir("out"):
        if f.startswith(f"raw{n}_"): os.remove(os.path.join("out", f))
json.dump(report, open(f"out/report_{key}.json", "w"), indent=1); print("DONE", key)
