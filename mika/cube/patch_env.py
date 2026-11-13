"""Let the cube scripts run on another company set: CUBE_HOME = folder, CUBE_TICKERS = file of tickers."""
fixes = {
    r"D:\planet\mika\cube\cube_fetch.py": [
        ('HOME = r"D:\\planet\\mika\\cube"\n', 'HOME = os.environ.get("CUBE_HOME", r"D:\\planet\\mika\\cube")\n'),
        ('tickers = sorted(pd.read_csv(r"D:\\planet\\mika\\trading_backtest_rows.csv")["ticker"].unique())\n',
         'tickers = (sorted(open(os.environ["CUBE_TICKERS"]).read().split()) if os.environ.get("CUBE_TICKERS")\n'
         '           else sorted(pd.read_csv(r"D:\\planet\\mika\\trading_backtest_rows.csv")["ticker"].unique()))\n')],
    r"D:\planet\mika\cube\cube_leak_blur.py": [
        ('HOME = r"D:\\planet\\mika\\cube"\n', 'HOME = os.environ.get("CUBE_HOME", r"D:\\planet\\mika\\cube")\n')],
    r"D:\planet\mika\cube\cube_leak_size.py": [
        ('import math\n', 'import math, os\n'),
        ('X = pd.read_csv(r"D:\\planet\\mika\\cube\\leak_blur_events.csv")\n',
         'X = pd.read_csv(os.path.join(os.environ.get("CUBE_HOME", r"D:\\planet\\mika\\cube"), "leak_blur_events.csv"))\n')],
}
for f, reps in fixes.items():
    s = open(f, encoding="utf-8").read()
    for old, new in reps:
        assert s.count(old) == 1, (f, old[:50])
        s = s.replace(old, new)
    open(f, "w", encoding="utf-8").write(s)
print("ok")
