import shutil, sys
f = r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet\living_library.py"
shutil.copy2(f, f + ".bak_20261014_before_lazy")
s = open(f, encoding="utf-8").read()
reps = [
    ("    log(f\"brain: {made} digested, {kept} unchanged, {gone} removed (raw file gone) -> {BRAIN}\")\n    return made\n",
     "    log(f\"brain: {made} digested, {kept} unchanged, {gone} removed (raw file gone) -> {BRAIN}\")\n    return made + gone\n"),
    ("    sparse.save_npz(SIGS(), M)\n",
     "    tmp_sig = SIGS()[:-4] + \".tmp.npz\"                     # write then swap, so a search mid-build never reads half a file\n"
     "    sparse.save_npz(tmp_sig, M); os.replace(tmp_sig, SIGS())\n"),
    ("    ap.add_argument(\"--top\", type=int, default=20); ap.add_argument(\"--model\", default=\"qwen2.5:3b\")\n",
     "    ap.add_argument(\"--top\", type=int, default=20); ap.add_argument(\"--model\", default=\"qwen2.5:3b\")\n"
     "    ap.add_argument(\"--lazy\", action=\"store_true\", help=\"rebuild the spiral only if something changed or it is 24h old\")\n"),
    ("        if a.cmd == \"ingest\": ingest()\n        digest_all(); build_spiral(); print(f\"done in {time.time() - t0:.0f}s\")\n",
     "        if a.cmd == \"ingest\": ingest()\n"
     "        changed = digest_all()\n"
     "        age_h = (time.time() - os.path.getmtime(INDEX())) / 3600 if os.path.exists(INDEX()) else 1e9\n"
     "        if a.lazy and not changed and age_h < 24:\n"
     "            print(f\"spiral: nothing changed, index {age_h:.1f}h old - kept as is\")\n"
     "        else: build_spiral()\n"
     "        print(f\"done in {time.time() - t0:.0f}s\")\n"),
]
for old, new in reps:
    if s.count(old) != 1: sys.exit("patch target not found once: " + old[:60])
    s = s.replace(old, new)
open(f, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
