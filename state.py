import time
import threading
import traceback
import signal
import sys
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from collections import deque

from core import Et, Lg, CFG, Oc, Cs, Sc
from vision import Vs
from movement import Mc, Gi
from truck import TruckInteractor


@dataclass
class Cx:
    cir:  List[Oc] = field(default_factory=list)
    tc:   Optional[Oc] = None
    cbl:  List[Dict] = field(default_factory=list)
    tbl:  Optional[Dict] = None
    cpb:  List[Dict] = field(default_factory=list)
    ttb:  Optional[Dict] = None
    ltst: float = 0.0
    cpv:  bool = False
    bfhv: bool = False
    lit:  float = 0.0
    ca:   int = 0
    sr:   int = 0
    sif:  int = 0
    cf:   int = 0
    sst:  float = field(default_factory=time.time)
    lsc:  float = 0.0
    mtr:  Dict[str, Any] = field(default_factory=dict)
    ec:   int = 0
    ra:   int = 0
    bif:  bool = False
    lpc:  float = field(default_factory=time.time)
    oib:  int = 0
    rsac: Optional[Et] = None


class Ct:
    def __init__(self, l: Lg):
        self.l  = l
        self.cd = CFG['cd']
        self.lt = 0.0
        self.iw = False

    def start(self):
        self.lt = time.time()
        self.iw = True

    def ready(self) -> bool:
        if not self.iw:
            return True
        if time.time() - self.lt >= self.cd:
            self.iw = False
            return True
        return False

    def rem(self) -> float:
        if not self.iw:
            return 0.0
        return max(0.0, self.cd - (time.time() - self.lt))


class Stm:
    def __init__(self, l: Lg):
        self.l       = l
        self._nc = False

    def next(self, st: Et, cx: Cx) -> Et:
        if st == Et.I:
            return Et.MV if cx.tbl else Et.SC
        if st == Et.SC:
            return Et.MV if cx.tbl else Et.SE
        if st == Et.MV:
            return Et.MV if cx.tbl else Et.SE
        if st == Et.CO:
            return Et.W
        if st == Et.W:
            return Et.SC if time.time() - cx.lit >= CFG['cd'] else Et.W
        if st == Et.SE:
            if cx.tbl:
                return Et.SE
            if cx.sif >= CFG['sit']:
                if self._nc:
                    cx.sif = 0; cx.sr = 0
                    return Et.SE
                if not cx.bif:
                    cx.sif = 0; cx.sr = 0
                    return Et.SE
                return Et.GT
            if cx.sr >= CFG['msr']:
                cx.sr = 0
                return Et.I
            return Et.SE
        if st in (Et.GT, Et.TR, Et.PC):
            return st
        if st == Et.ER:
            return Et.I if cx.ra < 3 else Et.PA
        if st == Et.PA:
            return Et.PA
        return st


class Bot:
    def __init__(self, l: Lg, no_car: bool = False,
                 truck_color: str = 'pink', farm_mode: str = 'orange',
                 ccfg: dict = None):
        self.l          = l
        self.nc     = no_car
        self.tc = truck_color
        self.fm  = farm_mode
        self._ccfg      = ccfg or {}
        self.ds         = self._ccfg.get('ds', 'orang' if farm_mode == 'orange' else 'tabac')
        self.ncfg       = self._bld_ncfg()
        self.bk         = float(self._ccfg.get('bk', CFG['bwt']))
        self.cs = Et.I
        self.context    = Cx()

        self.gi    = Gi(l)
        self.mc    = Mc(l, self.gi)
        self.vs    = Vs(l)
        self.ct    = Ct(l)
        self.sm    = Stm(l)
        self.sm._nc = self.nc
        self.sc    = Sc(l)
        self.truck = TruckInteractor(l, self.gi, self.vs, self.sc)
        self._pcr  = False

        self.run  = False
        self.paused   = False
        self.stp = False

        self.thr   = None
        self.thv = None
        self.ths  = None

        self.pm    = Pm(l)
        self.stats = Cs()
        self.stats.st = time.time()
        self.eh    = Eh(l)

        signal.signal(signal.SIGINT,  self._sig)
        signal.signal(signal.SIGTERM, self._sig)

    def _bld_ncfg(self):
        c  = self._ccfg
        nc = c.get('nc', 1 if self.fm == 'orange' else 2)
        if nc == 2:
            return {'nc': 2, 'nd': c.get('nd', 'eau'), 'ne': c.get('ne', 'pain')}
        return {'nc': 1, 'ni': c.get('ni', 'orang')}

    def start(self):
        if self.run:
            return
        self.l.i("bot start")
        self.run  = True
        self.stp = False
        self.thr   = threading.Thread(target=self._loop,  daemon=True)
        self.thv = threading.Thread(target=self._vloop, daemon=True)
        self.ths  = threading.Thread(target=self._sloop, daemon=True)
        self.thr.start()
        self.thv.start()
        self.ths.start()

    def stop(self):
        self.l.i("bot stop")
        self.stp = True
        self.run  = False
        self.mc.stop()

    def pause(self):
        self.paused = True
        self.cs = Et.PA
        self.mc.stop()
        self.l.i("pause")

    def resume(self):
        self.paused = False
        self.cs = Et.I
        self.l.i("resume")

    def _loop(self):
        self.l.i("loop start")
        while not self.stp:
            try:
                if self.paused:
                    time.sleep(0.5)
                    continue
                self._upd_ctx()
                now = time.time()
                can_int = self.cs not in (Et.TR, Et.PC, Et.PA, Et.ER)
                if now - self.context.lpc >= CFG['pci'] and can_int and not self._pcr:
                    self.l.i("timer → pcheck")
                    self.context.rsac = self.cs
                    self._pcr = True
                    self.mc.stop()
                    self.cs = Et.PC
                if not self._pcr:
                    ns = self.sm.next(self.cs, self.context)
                    if ns != self.cs:
                        self.cs = ns
                self._exec()
                self.pm.update()
                time.sleep(0.1)
            except Exception as e:
                self.eh.handle(e, self.context)
                self.cs = Et.ER
                time.sleep(1.0)

    def _vloop(self):
        self.l.i("vloop start")
        while not self.stp:
            try:
                if self.paused:
                    time.sleep(0.5)
                    continue
                img = self.sc.cap()
                if img is not None and img.size > 0:
                    blobs = self.vs.d_org(img)
                    self.context.cbl = blobs
                    self.stats.cd  += len(blobs)
                    tb = (self.vs.d_bge(img)
                          if self.tc == 'beige'
                          else self.vs.d_pnk(img))
                    self.context.cpb = tb
                    now = time.time()
                    if tb:
                        self.context.ttb  = tb[0]
                        self.context.ltst = now
                    elif now - self.context.ltst > 2.5:
                        self.context.ttb = None
                    self.context.cpv = self.vs.dcp(img)
                    if not self.context.bif and not self.nc:
                        if self.vs.dbf(img):
                            self.context.bif  = True
                            self.context.bfhv = True
                            self.l.i("bag full")
                time.sleep(CFG['si'])
            except Exception as e:
                self.l.e(f"vloop err {e}")
                time.sleep(1.0)

    def _sloop(self):
        while not self.stp:
            try:
                time.sleep(1.0)
            except Exception:
                time.sleep(5.0)

    def _upd_ctx(self):
        if not hasattr(self, '_ntc'):
            self._ntc = 0
        nt  = None
        had = bool(self.context.cbl)
        if had:
            nt = self.vs.gbt(
                self.context.cbl,
                screen_w=self.gi._win_w,
                previous=self.context.tbl,
            )
        if nt is not None:
            self.context.tbl = nt
            self._ntc = 0
        else:
            self._ntc += 1
            if had and self.context.tbl is not None:
                self.l.i("overshoot release")
                self.context.tbl = None
                self._ntc = 0
            elif self._ntc >= 10:
                self.context.tbl = None

    def _exec(self):
        s = self.cs
        if   s == Et.MV: self._h_move()
        elif s == Et.CO: self._on_col()
        elif s == Et.W:  self._h_wait()
        elif s == Et.SE: self._h_search()
        elif s == Et.GT: self._h_truck()
        elif s == Et.TR: self._h_transfer()
        elif s == Et.PC: self._h_pcheck()
        elif s == Et.ER: self._h_err()
        elif s == Et.PA: time.sleep(0.5)

    def _h_move(self):
        if self.context.bif and not self.nc:
            self.l.i("bag full → truck")
            self.mc.stop()
            self.cs = Et.GT
            return
        if self.context.cpv:
            self.context.cpv = False
            self.l.i("prompt → e")
            self.mc.stop()
            time.sleep(0.08)
            self.gi.press('e', 0.3)
            time.sleep(1.5)
            chk = self.sc.cap()
            if chk is not None and chk.size > 0:
                if self.vs.dbf(chk, force_ocr=True):
                    self.context.bif  = True
                    self.context.bfhv = True
                    if not self.nc:
                        self.l.i("pas de place → truck")
                        self.cs = Et.GT
                        return
            self._on_col()
            return
        blob = self.context.tbl
        if not blob:
            self.mc.stop()
            self.cs = Et.SE
            return
        r = self.mc.nav_blob(blob)
        if r == 'collected':
            self._on_col()
        elif r in ('navigating', 'turning'):
            self.context.ca += 1
            if self.context.ca > 500:
                self.mc.stop()
                self.l.w("trop tentatives")
                self.context.tbl = None
                self.context.ca  = 0
                self.cs = Et.SE

    def _on_col(self):
        self.mc.stop()
        self.stats.tc += 1
        self.stats.sc += 1
        self.context.tbl = None
        self.context.tc  = None
        self.context.ca  = 0
        self.context.cf  = 0
        self.context.sif = 0
        self.context.oib += 1
        self.context.lit = time.time()
        self.context.lsc = time.time()
        self.l.i(f"recolte sc={self.stats.sc}")
        self.ct.start()
        self.cs = Et.W

    def _h_wait(self):
        if self.context.bif and not self.nc:
            self.l.i("wait bag full")
            self.cs = Et.GT

    def _h_search(self):
        if self.context.bif and not self.nc:
            self.l.i("search bag full")
            self.mc.stop()
            self.cs = Et.GT
            return
        if self.context.tbl:
            self.context.sr  = 0
            self.context.sif = 0
            self.mc.rss()
            self.l.i("blob → move")
            self.cs = Et.MV
            return
        if self.context.sif >= CFG['sit']:
            self.l.i(f"search fail {self.context.sif} → truck")
            self.mc.stop()
            self.cs = Et.GT
            return
        self.mc.sscan(should_stop=lambda: self.vs.gbt(self.context.cbl) is not None)
        self.context.sr += 1
        if self.context.tbl is None:
            self.context.sif += 1

    def _h_truck(self):
        truck  = self.context.ttb
        sw, sh = CFG['res']
        if truck is None:
            try:
                fr = self.sc.cap()
                if fr is not None and fr.size > 0:
                    fresh = (self.vs.d_bge(fr)
                             if self.tc == 'beige'
                             else self.vs.d_pnk(fr))
                    if fresh:
                        truck = fresh[0]
                        self.context.ttb  = truck
                        self.context.cpb  = fresh
                        self.context.ltst = time.time()
                        self.l.i(f"truck detect area={truck.get('area',0)}")
            except Exception as e:
                self.l.d(f"truck detect {e}")
        if truck is None:
            self.mc.tscan(should_stop=lambda: len(self.context.cpb) > 0)
            return
        if hasattr(self.mc, 'rst'):
            self.mc.rst()
        bbox = truck.get('bbox', (0, 0, 0, 0))
        bx, by, bw, bh = (bbox[0], bbox[1], bbox[2], bbox[3]) if len(bbox) >= 4 else (0,0,0,0)
        tcx = bx + bw // 2
        dx  = abs(tcx - sw // 2)
        vc  = bh >= int(sh * 0.42)
        al  = dx <= int(sw * 0.22)
        ca  = bh >= int(sh * 0.35) and al
        if vc or ca:
            self.l.i(f"truck arrive bh={bh} dx={dx}")
            self.mc.stop()
            time.sleep(0.15)
            wd = 1.8 if bh < int(sh * 0.38) else (1.2 if bh < int(sh * 0.45) else 0.7)
            self.gi.kdn('z')
            time.sleep(wd)
            self.gi.kup('z')
            self.mc.stop()
            self.context.sif = 0
            self.cs = Et.TR if self.context.bif else Et.SE
            return
        now = time.time()
        if now - getattr(self, '_tlog', 0) > 1.5:
            self.l.i(f"truck nav bh={bh} dx={dx}")
            self._tlog = now
        self.mc.nav_blob(truck, crawl_thresh=100000)

    def _h_transfer(self):
        self.l.i("transfert debut")
        self.mc.stop()
        time.sleep(0.3)
        qty = max(1, int(self.stats.sc))
        try:
            if CFG['vlk']:
                if not self.truck.unlock():
                    self.l.w("unlock fail")
            pb = self.context.cpb
            if not self.truck.open_menu(pink_blobs=pb):
                self.l.e("coffre fail")
                self._fin_transfer(False)
                return
            ok = self.truck.transfer(self.ds, qty)
            if not ok:
                self.l.e("transfer fail")
            self.truck.close_inv()
            if CFG['vlk']:
                if not self.truck.lock():
                    self.l.c("verrou fail")
            self._fin_transfer(ok)
        except Exception as e:
            self.l.e(f"transfer err {e}")
            try:
                self.gi.rel_keys()
                self.gi.press('tab', 0.1)
                if CFG['vlk']:
                    self.truck.lock()
            except Exception:
                pass
            self._fin_transfer(False)

    def _fin_transfer(self, ok: bool):
        self.context.sif = 0
        self.mc.rss()
        if ok:
            self.context.bif  = False
            self.context.bfhv = False
            self.stats.sc     = 0
            self.context.oib  = 0
            self.l.i("transfer ok → search")
            self.cs = Et.SE
        else:
            self.l.w("transfer fail → retente")
            self.gi.press('s', duration=1.0)
            self.cs = Et.GT

    def _h_pcheck(self):
        self.l.i("pcheck start")
        self.mc.stop()
        time.sleep(0.3)
        full_now = False
        try:
            self.truck.open_inv()
            w = self.truck.read_w()
            if w is not None:
                self.l.i(f"poids {w:.1f}/24")
                if w >= self.bk:
                    full_now = True
            else:
                self.l.w("ocr poids fail")
            self.truck.eat(
                self.ncfg, count=CFG['eoc'], wait_per_bite=CFG['eow'],
                interrupt=lambda: self.stp or self.paused,
            )
            self.truck.close_inv()
        except Exception as e:
            self.l.e(f"pcheck err {e}")
            try:
                self.gi.press('tab', 0.1)
            except Exception:
                pass
        self.context.lpc = time.time()
        self._pcr = False
        if full_now:
            self.context.bif = True
            if not self.nc:
                self.l.i("pcheck plein → truck")
                self.cs = Et.GT
            else:
                rs = self.context.rsac or Et.SE
                if rs in (Et.TR, Et.PC, Et.PA, Et.ER): rs = Et.SE
                self.cs = rs
        else:
            rs = self.context.rsac or Et.SE
            if rs in (Et.TR, Et.PC, Et.PA, Et.ER): rs = Et.SE
            self.l.i(f"pcheck → {rs.value}")
            self.cs = rs
        self.context.rsac = None

    def _h_err(self):
        self.l.w("recovery")
        self.mc.stop()
        self.context.tc = None
        self.context.ca = 0
        self.context.ra += 1
        time.sleep(2.0)

    def _sig(self, signum, frame):
        self.stop()
        sys.exit(0)

    def gst(self) -> Dict[str, Any]:
        el = time.time() - (self.stats.st or time.time())
        return {
            'state':      self.cs.value,
            'is_running': self.run,
            'is_paused':  self.paused,
            'stats': {
                'sc':           self.stats.sc,
                'st':           el,
                'session_time': el,
                'tc':           self.stats.tc,
            },
            'context': {
                'cd':                  self.stats.cd,
                'blobs_visible':       len(self.context.cbl),
                'has_target':          self.context.tbl is not None,
                'collection_attempts': self.context.ca,
                'search_rotations':    self.context.sr,
                'consecutive_failures': self.context.cf,
            },
        }


class Pm:
    def __init__(self, l: Lg):
        self.l  = l
        self.lu = time.time()

    def update(self):
        self.lu = time.time()


class Eh:
    def __init__(self, l: Lg):
        self.l = l

    def handle(self, e: Exception, cx: Cx):
        self.l.e(f"err {type(e).__name__} {e}")
        cx.tc = None
        cx.ca = 0
        cx.ec += 1


OrangeFarmAI  = Bot
AIContext     = Cx
CollectionTimer = Ct
