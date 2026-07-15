import sys, os, subprocess, time, json, urllib.request, tempfile, ctypes

DIR = os.path.dirname(os.path.abspath(__file__))
CFJ = os.path.join(DIR, 'config.json')

_IMP = {
    "opencv-python": "cv2", "numpy": "numpy", "pillow": "PIL",
    "psutil": "psutil", "pywin32": "win32gui", "pyautogui": "pyautogui",
    "mss": "mss", "pytesseract": "pytesseract", "keyboard": "keyboard",
    "mouse": "mouse",
}

def _rreq():
    rf = os.path.join(DIR, 'requirements.txt')
    pkgs = []
    if not os.path.exists(rf):
        return list(_IMP.items())
    with open(rf, 'r', encoding='utf-8') as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith('#'):
                continue
            name = ln.split('>=')[0].split('<=')[0].split('==')[0].split('!=')[0].strip()
            imp  = _IMP.get(name.lower(), name.lower().replace('-','_'))
            pkgs.append((name, imp))
    return pkgs

TURL = ("https://github.com/UB-Mannheim/tesseract/releases/download/"
        "v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe")
TDIR = os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\'), 'Tesseract-OCR')
TPS  = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.join(TDIR, 'tesseract.exe'),
]


def _adm():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False


def _uac():
    sc = os.path.abspath(__file__)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sc}"', None, 1)
    sys.exit(0)


def _chk(imp):
    try:
        __import__(imp)
        return True
    except ImportError:
        return False


def _pkgs():
    PKGS = _rreq()
    miss = [pip for pip, imp in PKGS if not _chk(imp)]
    if not miss:
        print("deps ok")
        time.sleep(0.4)
        return
    print(f"install : {', '.join(miss)}")
    subprocess.check_call(
        [sys.executable, '-m', 'pip', 'install', '-q', '--upgrade'] + miss,
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
    if 'pywin32' in miss: _pw32()
    print("deps ok")


def _pw32():
    try:
        sc = os.path.join(os.path.dirname(sys.executable), 'Scripts', 'pywin32_postinstall.py')
        if os.path.exists(sc):
            subprocess.call([sys.executable, sc, '-install'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass


def _tfd():
    for p in TPS:
        if os.path.exists(p): return p
    return None


def _tin():
    print("dl tesseract...")
    tmp = os.path.join(tempfile.gettempdir(), 'tess.exe')
    try:
        urllib.request.urlretrieve(TURL, tmp)
    except Exception as e:
        print(f"tesseract dl fail ({e})")
        print("ocr off")
        return None
    if not _adm():
        print("admin requis pour tesseract")
        time.sleep(1)
        _uac()
    print("install tesseract...")
    subprocess.call(f'"{tmp}" /S /D={TDIR}', shell=True)
    try: os.remove(tmp)
    except: pass
    return _tfd()


def _tcfg(p):
    try:
        d = {}
        if os.path.exists(CFJ):
            with open(CFJ, 'r', encoding='utf-8') as f: d = json.load(f)
        d['tess'] = p
        with open(CFJ, 'w', encoding='utf-8') as f: json.dump(d, f, indent=4)
    except: pass


def _tess():
    p = _tfd()
    if p:
        print("tesseract ok")
        _tcfg(p)
        return
    print("tesseract absent")
    p = _tin()
    if p:
        print("tesseract ok")
        _tcfg(p)
    else:
        print("tesseract fail, ocr off")


def main():
    os.chdir(DIR)
    print()
    print("check deps...")
    _pkgs()
    print()
    _tess()
    print()
    print("ok")
    time.sleep(0.6)
    subprocess.Popen([sys.executable, os.path.join(DIR, 'start.py')])


if __name__ == '__main__':
    main()
