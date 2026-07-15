import sys, os, subprocess, zipfile, urllib.request, tempfile, time

APP  = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'farm-bot')
SRC  = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), 'src.zip')

import platform as _pl
_arch = _pl.machine().lower()
if _arch == 'arm64':
    PY_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-arm64.exe"
elif _arch in ('i386', 'i686', 'x86'):
    PY_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10.exe"
else:
    PY_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
PY_PATH = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python312', 'python.exe')


def _fpy():
    if os.path.exists(PY_PATH): return PY_PATH
    for cmd in ['python', 'py']:
        try:
            r = subprocess.run([cmd, '-c', 'import sys; print(sys.executable)'],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except: pass
    return None


def _ipy():
    print("python absent, dl...")
    tmp = os.path.join(tempfile.gettempdir(), 'py_setup.exe')
    try:
        urllib.request.urlretrieve(PY_URL, tmp)
    except Exception as e:
        print(f"dl fail ({e})")
        return None
    print("install python...")
    subprocess.call([tmp, '/quiet', 'InstallAllUsers=0', 'PrependPath=1', 'Include_test=0'])
    try: os.remove(tmp)
    except: pass
    return PY_PATH if os.path.exists(PY_PATH) else None


def main():
    print()
    print(" farm bot")
    print()

    os.makedirs(APP, exist_ok=True)
    print("extraction...")
    with zipfile.ZipFile(SRC) as zf:
        zf.extractall(APP)

    py = _fpy()
    if not py:
        py = _ipy()
    if not py or not os.path.exists(py):
        print("python introuvable")
        print("va sur python.org/downloads et installe python 3.12")
        input("\nappuie sur entree pour quitter")
        return

    print("ok")
    time.sleep(0.4)
    subprocess.Popen([py, os.path.join(APP, 'installer.py')])


if __name__ == '__main__':
    main()
