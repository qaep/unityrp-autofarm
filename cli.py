import msvcrt, os, json, sys, time, subprocess

CF  = 'bot_configs.json'
_D  = os.path.dirname(os.path.abspath(__file__))
PXF = os.path.join(_D, 'pixels.json')
PRF = os.path.join(_D, 'pixels_presets.json')

RESS = [
    (1920, 1080),
    (1760, 990),
    (1720, 1080),
    (1680, 1050),
    (1600, 900),
    (1440, 900),
]

KGS = [12.0, 18.0, 24.0, 36.0]

PRESETS = {
    "orange":    {"tc": "rose",  "ds": "orang", "nc": 1, "ni": "orang",              "cm": None},
    "tabacrose": {"tc": "rose",  "ds": "tabac", "nc": 2, "nd": "eau", "ne": "pain",  "cm": None},
    "beige":     {"tc": "beige", "ds": "tabac", "nc": 2, "nd": "eau", "ne": "pain",  "cm": None},
    "cartabac":  {"tc": "rose",  "ds": "tabac", "nc": 2, "nd": "eau", "ne": "pain",  "cm": "car"},
}

CMAP = {"rose": "pink", "beige": "beige"}
RES  = list(PRESETS.keys()) + ["car", "nocar"]


def _gc():
    ch = msvcrt.getwch()
    if ch in ('\x00', '\xe0'):
        c2 = msvcrt.getwch()
        if c2 == 'H': return 'UP'
        if c2 == 'P': return 'DOWN'
        return None
    if ch == '\r': return 'ENTER'
    if ch == '\x1b': return 'ESC'
    return ch


def _bye():
    os.system('cls')
    print("\n\n\n\n                  au revoir")
    time.sleep(0.5)
    sys.exit(0)


def _mn(titre, opts):
    idx = 0
    while True:
        os.system('cls')
        print("esc pour quitter\n")
        print(titre + '\n')
        for i, o in enumerate(opts):
            print(('> ' if i == idx else '  ') + o)
        print()
        k = _gc()
        if k == 'UP':    idx = (idx - 1) % len(opts)
        elif k == 'DOWN': idx = (idx + 1) % len(opts)
        elif k == 'ENTER': return idx
        elif k == 'ESC':   _bye()


def _ld():
    if not os.path.exists(CF): return {}
    try:
        with open(CF) as f: return json.load(f)
    except: return {}


def _sv(d):
    with open(CF, 'w') as f: json.dump(d, f, indent=2)


def _res():
    labs = [f"{w}x{h} (recommande)" if i == 0 else f"{w}x{h}"
            for i, (w, h) in enumerate(RESS)] + ["autre"]
    c = _mn("resolution ecran", labs)
    if c < len(RESS):
        return RESS[c]
    while True:
        os.system('cls')
        print("esc pour quitter\n")
        print("resolution\n")
        v = input("  ____x____ > ").strip()
        if not v:
            continue
        if 'x' in v.lower():
            try:
                parts = v.lower().split('x')
                w, h = int(parts[0].strip()), int(parts[1].strip())
                if 640 <= w <= 7680 and 480 <= h <= 4320:
                    return (w, h)
                print("  resolution invalide")
                time.sleep(1)
            except (ValueError, IndexError):
                print("  format: 1920x1080")
                time.sleep(1)
        else:
            print("  format: 1920x1080")
            time.sleep(1)


def _bwt():
    labs = [f"{int(k)}kg" for k in KGS] + ["autre"]
    c = _mn("kg du sac (seuil depot)", labs)
    if c < len(KGS):
        return KGS[c]
    while True:
        os.system('cls')
        print("esc pour quitter\n")
        print("kg du sac\n")
        v = input("  > ").strip()
        try:
            k = float(v)
            if 1.0 <= k <= 200.0:
                return k
            print("  valeur invalide")
            time.sleep(1)
        except ValueError:
            print("  chiffres uniquement")
            time.sleep(1)


def _presets(bk: float):
    saved = _ld()
    noms  = list(PRESETS.keys())
    labs  = [f"{n} (defaut)" if n == "orange" else n for n in noms]
    for sn in saved: labs.append(f"[s] {sn}")
    labs.append("<- retour")
    c = _mn("presets", labs)
    if c == len(labs) - 1: return None
    if c < len(noms):
        p = PRESETS[noms[c]].copy()
    else:
        sn = list(saved.keys())[c - len(noms)]
        p  = saved[sn].copy()
    p['bk'] = bk
    return p


def _custom(bk: float):
    saved = _ld()
    skeys = list(saved.keys())
    opts  = ["nouvelle config"] + [f"[s] {sn}" for sn in skeys] + ["<- retour"]
    c = _mn("custom", opts)
    if c == len(opts) - 1: return None
    if c == 0: return _build(bk)
    p = saved[skeys[c - 1]].copy()
    p['bk'] = bk
    return p


def _build(bk: float):
    ci = _mn("couleur vehicule", ["rose", "beige"])
    tc = ["rose", "beige"][ci]

    ni = _mn("items nutrition", ["1 (un seul)", "2 (boire + manger)"])
    nc = ni + 1

    os.system('cls')
    print('"échap" pour quitter\n--\n')
    cfg = {"tc": tc, "nc": nc, "bk": bk}

    if nc == 1:
        print("item nutrition (ex: orang)")
        v = input("> ").strip()
        cfg["ni"] = v or "orang"
    else:
        print("item a boire (ex: eau)")
        v = input("> ").strip()
        cfg["nd"] = v or "eau"
        print("item a manger (ex: pain)")
        v = input("> ").strip()
        cfg["ne"] = v or "pain"

    print("objet a drag dans le coffre (ex: orang)")
    v = input("> ").strip()
    cfg["ds"] = v or "orang"

    print("option car/nocar (entree pour skip)")
    v = input("> ").strip().lower()
    cfg["cm"] = v if v in ("car", "nocar") else None

    si = _mn("sauvegarder?", ["oui", "non"])
    if si == 0:
        while True:
            os.system('cls')
            print("esc pour quitter\n")
            print("nom de la config")
            nm = input("> ").strip().lower()
            if not nm:
                print("nom vide"); _gc(); continue
            if nm in RES:
                print(f"'{nm}' est reserve"); _gc(); continue
            saved = _ld()
            if nm in saved:
                print(f"'{nm}' existe deja"); _gc(); continue
            saved[nm] = cfg
            _sv(saved)
            print(f"config '{nm}' sauvegardee")
            _gc()
            break

    return cfg


def _aide():
    os.system('cls')
    print("esc pour quitter\n")
    print("""presets   configs pretes a lancer
custom    faire sa config
car       commence directement au coffre (sac considere plein)
nocar     farm uniquement ignore le vehicule
rose      truck rose
beige     truck beige
seuil kg  poids inventaire qui declenche le depot
drag      texte tape dans la recherche inventaire avant drag
nutrition nb items consommes toutes les 5 mins

appuie sur une touche pour revenir""")
    _gc()


def _pxok():
    try:
        with open(PXF, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return all(d.get(k) for k in ('srch', 'org_itm', 'drop', 'qty', 'cfm', 'eat_itm'))
    except:
        return False


def _chkpx(res):
    if _pxok():
        return
    key = f"{res[0]}x{res[1]}"
    preset = None
    try:
        with open(PRF, 'r', encoding='utf-8') as f:
            preset = json.load(f).get(key)
    except:
        pass

    os.system('cls')
    print("esc pour quitter\n")
    print("pixels non calibres\n")

    if preset:
        print(f"preset disponible pour {key}\n")
        c = _mn(f"pixels ({key})", ["utiliser le preset", "calibrer manuellement"])
        if c == 0:
            try:
                with open(PXF, 'w', encoding='utf-8') as f:
                    json.dump(preset, f, indent=4)
                os.system('cls')
                print("pixels ok\n")
                time.sleep(0.8)
            except:
                pass
            return

    os.system('cls')
    print("esc pour quitter\n")
    print("calibration des pixels\n")
    print("le jeu doit etre ouvert\n")
    print("appuie sur une touche pour lancer la calibration...")
    _gc()
    subprocess.run([sys.executable, os.path.join(_D, 'pixels.py')])
    os.system('cls')


def menu():
    res = _res()
    _chkpx(res)
    bk  = _bwt()
    while True:
        c = _mn("farm bot", ["presets", "custom", "aide"])
        if c == 0:
            r = _presets(bk)
            if r is not None:
                r['res'] = res
                return r
        elif c == 1:
            r = _custom(bk)
            if r is not None:
                r['res'] = res
                return r
        elif c == 2:
            _aide()
