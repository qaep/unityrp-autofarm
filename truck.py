from __future__ import annotations
import json
import os
import time
from typing import Optional, Dict, Tuple, Callable

from core import Lg, CFG, Sc
from movement import Gi
from vision import Vs


class Ti:
    uto  = 3.0
    lto  = 3.0
    pi   = 0.15
    ahc  = 0.40
    iod  = 1.0
    acd  = 0.4
    MO   = "OUVRIR"
    MI   = "INTERAGIR"
    MC   = "COPIER"

    def __init__(self, logger: Lg, game_interface: Gi,
                 vision_system: Vs, screen_capture: Sc):
        self.l = logger
        self.gi     = game_interface
        self.vs     = vision_system
        self.sc     = screen_capture
        self.pixels = self._load_pixels()

    def _load_pixels(self) -> Dict:
        import sys
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, CFG.get('tpf', 'pixels.json'))
        if not os.path.exists(path):
            self.l.w(f"pixels absent {path}")
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.l.e(f"pixels load err {e}")
            return {}

    def rpx(self):
        self.pixels = self._load_pixels()

    def gpx(self, key: str) -> Optional[Tuple[int, int]]:
        d = self.pixels.get(key)
        if not d:
            self.l.e(f"pixel '{key}' non calibre")
            return None
        x, y = int(d.get('x', 0)), int(d.get('y', 0))
        if x <= 0 or y <= 0:
            self.l.e(f"pixel '{key}' = (0,0)")
            return None
        return (x, y)

    def _poll_hud(self, timeout: float) -> Optional[str]:
        t_end = time.time() + timeout
        while time.time() < t_end:
            fr = self.sc.cap()
            if fr is not None and fr.size > 0:
                st = self.vs.dvh(fr)
                if st is not None:
                    return st
            time.sleep(self.pi)
        return None

    def unlock(self, max_retries: int = 1) -> bool:
        self.l.i("unlock U")
        self.gi.press('u', 0.12)
        time.sleep(0.7)
        return True

    def lock(self, max_retries: int = 1) -> bool:
        self.l.i("lock U")
        self.gi.press('u', 0.12)
        time.sleep(0.7)
        return True

    def _candidates(self, pb=None):
        if not pb:
            fr = self.sc.cap()
            if fr is None or fr.size == 0:
                return []
            pb = self.vs.d_pnk(fr)
        if not pb:
            return []
        big = max(pb, key=lambda b: b['area'])
        x, y, bw, bh = big['bbox']
        cx = x + bw // 2
        cy = y + bh // 2
        return [
            (cx, cy),
            (cx - bw // 4, cy),
            (cx + bw // 4, cy),
            (cx, cy - bh // 4),
            (cx, cy + bh // 4),
        ]

    def _ocr_find(self, text: str, px=None, py=None):
        fr = self.sc.cap()
        if fr is None or fr.size == 0:
            return None
        _, pos = self.vs.damip(fr, [text], target_cx=px, target_cy=py)
        return pos

    def _menu_state(self, px=None, py=None):
        fr = self.sc.cap()
        if fr is None or fr.size == 0:
            return (None, None)
        match, pos = self.vs.damip(
            fr, [self.MO, self.MI, self.MC], target_cx=px, target_cy=py)
        if match == self.MO: return ('ouvrir', pos)
        if match == self.MI: return ('interagir', pos)
        if match == self.MC: return ('copier', pos)
        return (None, None)

    def open_menu(self, pink_blobs=None) -> bool:
        cands = self._candidates(pink_blobs)
        if not cands:
            self.l.e("aucun blob rose")
            return False
        for idx, (px, py) in enumerate(cands, 1):
            self.l.i(f"alt #{idx}/{len(cands)} ({px},{py})")
            self.gi.kdn('alt')
            self.gi.mv_cur(px, py)
            time.sleep(1.0)
            kind, pos = self._menu_state(px=px, py=py)
            if kind is None:
                time.sleep(0.5)
                kind, pos = self._menu_state(px=px, py=py)
            if kind is None:
                time.sleep(0.5)
                kind, pos = self._menu_state(px=px, py=py)
            if kind == 'ouvrir':
                self.l.i("ouvrir direct")
                self.gi.click()
                time.sleep(0.2)
                self.gi.kup('alt')
                time.sleep(self.iod)
                self.l.i("coffre ouvert")
                return True
            if kind == 'interagir':
                fp = self._ocr_find(self.MI, px=px, py=py)
                if fp:
                    pos = fp
                self.l.i(f"interagir {pos} → clic")
                self.gi.mv_cur(pos[0], pos[1])
                time.sleep(0.15)
                self.gi.click()
                time.sleep(0.8)
                po = None
                for _ in range(6):
                    po = self._ocr_find(self.MO, px=px, py=py)
                    if po:
                        break
                    time.sleep(0.4)
                if po:
                    self.l.i(f"ouvrir sous-menu {po}")
                    fresh = self._ocr_find(self.MO)
                    if fresh:
                        po = fresh
                    self.gi.mv_cur(po[0], po[1])
                    time.sleep(0.15)
                    self.gi.click()
                    time.sleep(0.2)
                    self.gi.kup('alt')
                    time.sleep(self.iod)
                    self.l.i("coffre ouvert")
                    return True
                self.l.w("interagir clique ouvrir introuvable")
                self.gi.kup('alt')
                time.sleep(0.3)
                continue
            if kind == 'copier':
                self.l.w("menu copier → next")
                self.gi.kup('alt')
                time.sleep(0.3)
                continue
            self.l.d(f"aucun menu ({px},{py})")
            self.gi.kup('alt')
            time.sleep(0.3)
        self.l.e(f"coffre fail {len(cands)} cands")
        return False

    def _qty_popup(self, qty: int):
        qf = self.gpx('qty')
        cf = self.gpx('cfm')
        if qf and cf:
            self.gi.cat(qf[0], qf[1])
            time.sleep(0.05)
            self.gi.cat(qf[0], qf[1])
            time.sleep(0.05)
            self.gi.cat(qf[0], qf[1])
            time.sleep(0.15)
            self.gi.press('end', 0.03)
            for _ in range(10):
                self.gi.press('backspace', 0.02)
                time.sleep(0.02)
            time.sleep(0.1)
            self.gi.tnui(str(int(qty)), delay=0.06)
            time.sleep(0.2)
            self.gi.cat(cf[0], cf[1])
            time.sleep(0.6)
            self.l.i("qty confirmee")
        elif cf:
            self.gi.cat(cf[0], cf[1])
            time.sleep(0.6)
        else:
            self.gi.press('enter', 0.1)
            time.sleep(0.5)

    def _clear_search(self):
        pos = self.gpx('srch')
        if not pos:
            return
        self.gi.cat(pos[0], pos[1])
        time.sleep(0.15)
        self.gi.press('end', 0.05)
        time.sleep(0.05)
        for _ in range(20):
            self.gi.press('backspace', 0.02)
            time.sleep(0.02)
        time.sleep(0.15)

    def _search_inv(self, q: str):
        self._clear_search()
        pos = self.gpx('srch')
        self.gi.cat(pos[0], pos[1])
        time.sleep(0.2)
        self.gi.tnui(q, delay=0.05)
        time.sleep(0.4)

    def tro(self, q): return self.transfer("orang", q)

    def _slot_count(self, sx: int, sy: int) -> int:
        fr = self.sc.cap()
        if fr is None or fr.size == 0:
            return 0
        val = self.vs.dsc(fr, sx, sy)
        return int(val) if val and val > 0 else 0

    def transfer(self, search_str: str, qty_fallback: int, max_passes: int = 12) -> bool:
        src = self.gpx('org_itm')
        dst = self.gpx('drop')
        if not src or not dst:
            return False
        self._search_inv(search_str)
        time.sleep(0.6)
        done = False
        for i in range(1, max_passes + 1):
            cnt = self._slot_count(src[0], src[1])
            if cnt <= 0:
                if not done:
                    cnt = max(1, qty_fallback)
                    self.l.i(f"{search_str} pass {i} fallback={cnt}")
                else:
                    self.l.i(f"{search_str} pass {i} vide fin {i-1}")
                    break
            else:
                self.l.i(f"{search_str} pass {i} qty={cnt}")
            self.gi.drag(src[0], src[1], dst[0], dst[1], duration=0.55)
            time.sleep(0.6)
            self._qty_popup(cnt)
            done = True
            time.sleep(1.8)
        self._clear_search()
        return done

    def trt(self, q): return self.transfer("tabac", q, 6)

    def close_inv(self) -> bool:
        self.gi.press('tab', 0.1)
        time.sleep(1.0)
        self.l.i("inventaire ferme")
        return True

    def open_inv(self):
        self.gi.press('tab', 0.1)
        time.sleep(self.iod)

    def read_w(self) -> Optional[float]:
        fr = self.sc.cap()
        if fr is None or fr.size == 0:
            return None
        return self.vs.diw(fr)

    def eat(self, ncfg: dict, count: int, wait_per_bite: float = 8.0,
                      interrupt: Optional[Callable[[], bool]] = None) -> int:
        sl = self.gpx('org_itm')
        if not sl:
            self.l.w("pixel item absent")
            return 0
        eaten = 0
        nc = ncfg.get('nc', 1)
        if nc == 2:
            for lbl in [ncfg.get('nd', 'eau'), ncfg.get('ne', 'pain')]:
                self._search_inv(lbl)
                for i in range(1):
                    if interrupt and interrupt(): return eaten
                    self.gi.dbl_at(sl[0], sl[1])
                    self.l.i(f"consomme {lbl}")
                    eaten += 1
                    time.sleep(wait_per_bite)
        else:
            itm = ncfg.get('ni', 'orang')
            self._search_inv(itm)
            for i in range(count):
                if interrupt and interrupt():
                    self.l.i("repas stop")
                    break
                self.gi.dbl_at(sl[0], sl[1])
                self.l.i(f"mange {itm} {i+1}/{count}")
                eaten += 1
                time.sleep(wait_per_bite)
        self._clear_search()
        return eaten


TruckInteractor = Ti
