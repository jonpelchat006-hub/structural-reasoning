# ARC daily: scheduled live play.py fails on missing torch (interpreter mismatch)

**Found:** 2026-09-28 scheduled run (also hit the first runs of 9/25 and 9/27; manual re-runs those days succeeded).

## Symptom
`arc_daily.py` practice leg completes normally (verdict `same`, 54 wins vs baseline 54), and the ls20 oracle (`ls20_chain.py`) passes 5/5 levels — but the live `play.py` leg records all-`None`/empty completions with tail:

```
File "...\planet\play.py", line 62, in __init__
    import torch, eye
ModuleNotFoundError: No module named 'torch'
```

## Cause
In the scheduled (Desktop Commander / PowerShell) environment, `python` on PATH resolves to `C:\Users\GamerTech\anaconda3\python.exe`, which does **not** have torch installed. The successful interactive re-runs used the other install, `C:\Users\GamerTech\AppData\Local\Python\pythoncore-3.14-64` (its numpy shows up in the successful runs' warnings). Practice (`induce.py`) and the oracle don't import torch, so only the live play leg dies — which is why the daily verdict still comes out clean while live play data silently goes missing on scheduled days.

## Fix options
- Have `arc_daily.py` launch `play.py` with the full path to the 3.14 interpreter (or set the desired python explicitly at the top of arc_daily.py) instead of relying on `sys.executable`/PATH; or
- `pip install torch` into the anaconda3 environment.

Until fixed, expect scheduled-run history lines with `levels: null` for `play.py` while manual runs look healthy.
