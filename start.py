import sys, time, threading, ctypes
if sys.platform != 'win32': sys.exit(1)
try:
    from core import Lg as L, CFG, Et
    from state import OrangeFarmAI as Of
except: sys.exit(1)

def _run(ai, l):
    r = {'o': True}
    def hw():
        p = {0x77: 0, 0x78: 0, 0x79: 0}
        while r['o']:
            for k in (0x77, 0x78, 0x79):
                s = ctypes.windll.user32.GetAsyncKeyState(k)
                pr = (s & 0x8000) and not p[k]
                p[k] = s & 0x8000
                if pr:
                    if k == 0x79:
                        print("stop")
                        ai.stop()
                        r['o'] = False
                    elif k == 0x78:
                        if ai.paused: ai.resume()
                        else: ai.pause()
                    elif k == 0x77:
                        s_ = ai.gst()
                        st = s_['stats']
                        print(f"s:{s_['state']} c:{st.get('sc',0)} a:{s_['context']['collection_attempts']} v:{s_['context']['cd']}")
            time.sleep(0.05)
    threading.Thread(target=hw, daemon=True).start()

    for i in range(3, 0, -1): time.sleep(1)
    ai.start()

    lp = 0
    while r['o'] and ai.run:
        n = time.time()
        if n - lp >= 10:
            s_ = ai.gst()
            st = s_['stats']
            print(f"t:{int(st.get('st',0))} s:{s_['state']} c:{st.get('sc',0)} b:{s_['context']['blobs_visible']} v:{s_['context']['cd']}")
            lp = n
        time.sleep(0.5)

def m():
    if not sys.argv[1:]:
        from cli import menu, CMAP
        cfg = menu()
        if cfg is None: sys.exit(0)
        res = cfg.get('res')
        if res: CFG['res'] = res
        tc = CMAP.get(cfg.get('tc', 'rose'), 'pink')
        fm = 'orange'
        nc = cfg.get('cm') == 'nocar'
        cm = cfg.get('cm') == 'car'
        l = L("bot")
        ai = Of(l, no_car=nc, truck_color=tc, farm_mode=fm, ccfg=cfg)
        if cm:
            ai.context.bif = True
            ai.cs = Et.GT
        _run(ai, l)
        return

    a = set()
    for x in sys.argv[1:]:
        if x.startswith('--'): a.add(x)
        elif x.startswith('-'): a.add('-' + x)
        else: a.add('--' + x)
    if '--h' in a or '--help' in a:
        print("usage: run_bot.py [options]")
        print("  (sans args)  menu interactif")
        print("  --car        demarre direct au truck")
        print("  --nocar      mode sans vehicule")
        print("  --beige      truck beige + tabac")
        print("  --tabacrose  tabac + truck rose")
        print("  --cartabac   --car + --tabacrose")
        sys.exit(0)

    cm = '--car' in a
    nc = '--nocar' in a
    bg = '--beige' in a
    tr = '--tabacrose' in a
    ct = '--cartabac' in a
    if ct: cm, tr = True, True
    if cm and nc: sys.exit(1)

    fm = "tabac" if bg or tr else "orange"
    tc = "beige" if bg else "pink"

    print(f"go {fm} {tc}")
    l = L("bot")
    ai = Of(l, no_car=nc, truck_color=tc, farm_mode=fm)

    if cm:
        ai.context.bif = True
        ai.cs = Et.GT
        l.i("cm=1")

    _run(ai, l)

if __name__ == "__main__": m()