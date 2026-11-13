import ast
f = r"D:\planet\mika\mika_daily.py"
s = open(f, encoding="utf-8").read()
add = r'''

def ensure_ollama(log):
    """her reflection runs on the local models; start Ollama quietly if it is not up"""
    import urllib.request
    def up():
        try: urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3); return True
        except Exception: return False
    if up(): return
    exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    if not os.path.exists(exe): log.write("ollama not found; she plays without reflection\n"); return
    e = dict(os.environ)
    try:                                   # the models live where the user variable says (the colony's L4 zone)
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k: e["OLLAMA_MODELS"] = winreg.QueryValueEx(k, "OLLAMA_MODELS")[0]
    except Exception: pass
    subprocess.Popen([exe, "serve"], env=e, creationflags=0x08000000 | 0x00000008, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(2)
        if up(): log.write("started ollama for her reflection\n"); return
    log.write("ollama did not come up; she plays without reflection\n")
'''
old1 = "    except Exception: return {}\n"
old2 = 'with open(log_path, "a", encoding="utf-8") as log:\n'
assert s.count(old1) == 1 and s.count(old2) == 1
s = s.replace(old1, old1 + add, 1).replace(old2, old2 + "    ensure_ollama(log)\n", 1)
ast.parse(s)
open(f, "w", encoding="utf-8").write(s)
print("ok")
