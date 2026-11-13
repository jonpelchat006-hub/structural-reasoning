"""Oct 16 evening: play.py hooks for Mika's weighing. sense() each press (energy left), mind.press() may ask for a
reset ("RESET"), weigh_reset() may hold her path against a budget reset, after_press() sees what each press changed.
With mind=None nothing changes."""
import ast, shutil
F = r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet\play.py"
shutil.copy2(F, F + ".bak_20261016_before_weigh")
s = open(F, encoding="utf-8").read()
reps = [
    ("            forced_ = None\n            if mind is not None and hasattr(mind, \"press\"):\n"
     "                try: forced_ = mind.press(lvl, since)\n"
     "                except Exception as e_: log(f\"  {n:3d}. mind: route failed ({str(e_)[:80]})\"); forced_ = None\n"
     "            if forced_ is not None: do_reset = None\n",
     "            forced_ = None; mind_reset_ = False\n"
     "            if mind is not None and hasattr(mind, \"sense\"):\n"
     "                try: mind.sense(lvl, rem, margin, since)\n"
     "                except Exception as e_: log(f\"  {n:3d}. mind: sense failed ({str(e_)[:80]})\")\n"
     "            if mind is not None and hasattr(mind, \"press\"):\n"
     "                try: forced_ = mind.press(lvl, since)\n"
     "                except Exception as e_: log(f\"  {n:3d}. mind: route failed ({str(e_)[:80]})\"); forced_ = None\n"
     "            if isinstance(forced_, str):                     # she asks to put the level back (a trimmed route failed, a study is over)\n"
     "                do_reset = f\"mind: {forced_.lower()} requested\"; mind_reset_ = True; forced_ = None\n"
     "            if forced_ is not None: do_reset = None\n"),
    ("            if do_reset:\n                segments.append(",
     "            if do_reset and not mind_reset_ and mind is not None and hasattr(mind, \"weigh_reset\") and str(do_reset).startswith((\"target\", \"budget\")):\n"
     "                try:\n"
     "                    hold_ = mind.weigh_reset(lvl, {\"reason\": do_reset, \"rem\": rem, \"margin\": margin, \"target\": planned[1] if planned else None,\n"
     "                                                   \"kind\": planned[2] if planned else None, \"exp\": exp[\"id\"] if exp else None, \"since\": since})\n"
     "                except Exception as e_:\n"
     "                    hold_ = None; log(f\"  {n:3d}. mind: weighing failed ({str(e_)[:80]})\")\n"
     "                if hold_:\n"
     "                    log(f\"  {n:3d}. mind holds her path instead of resetting ({do_reset}; {hold_})\"); do_reset = None\n"
     "            if do_reset:\n                segments.append("),
    ("                        \"dist\": (None if near is None else -near), \"goals\": len(state[\"goals\"]), \"mover\": state[\"agent\"]})\n",
     "                        \"dist\": (None if near is None else -near), \"goals\": len(state[\"goals\"]), \"mover\": state[\"agent\"]})\n"
     "            if mind is not None and hasattr(mind, \"after_press\"):\n"
     "                try: mind.after_press(lvl, since, a, int(d.sum()), round(sp, 3), nl, why)\n"
     "                except Exception: pass\n"),
]
for old, new in reps:
    assert s.count(old) == 1, old[:90]
    s = s.replace(old, new)
ast.parse(s); open(F, "w", encoding="utf-8").write(s)
print("play.py patched; backup .bak_20261016_before_weigh")
