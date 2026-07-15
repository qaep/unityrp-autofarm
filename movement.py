import ctypes
import ctypes.wintypes
import time
import math
import random
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from collections import deque
import win32gui
from core import Lg, CFG, GCFG, Oc, Pp

INPUT_MOUSE          = 0
MOUSEEVENTF_MOVE     = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004

class _MI(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]

class _IU(ctypes.Union):
    _fields_ = [("mi", _MI)]

class _IN(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("_input", _IU)]

def _smm(dx: int, dy: int = 0):
    inp = _IN()
    inp.type = INPUT_MOUSE
    inp._input.mi.dx = dx
    inp._input.mi.dy = dy
    inp._input.mi.dwFlags = MOUSEEVENTF_MOVE
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

def _sma(xp: int, yp: int):
    u  = ctypes.windll.user32
    sw = u.GetSystemMetrics(0) or 1920
    sh = u.GetSystemMetrics(1) or 1080
    inp = _IN()
    inp.type = INPUT_MOUSE
    inp._input.mi.dx    = int(xp * 65535 / max(1, sw - 1))
    inp._input.mi.dy    = int(yp * 65535 / max(1, sh - 1))
    inp._input.mi.dwFlags = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
    u.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

def _smc(xp: int, yp: int, hold: float = 0.05):
    _sma(xp, yp)
    time.sleep(0.03)
    u = ctypes.windll.user32
    dn = _IN(); dn.type = INPUT_MOUSE; dn._input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
    u.SendInput(1, ctypes.byref(dn), ctypes.sizeof(dn))
    time.sleep(max(0.01, hold))
    up = _IN(); up.type = INPUT_MOUSE; up._input.mi.dwFlags = MOUSEEVENTF_LEFTUP
    u.SendInput(1, ctypes.byref(up), ctypes.sizeof(up))

def _scip(hold: float = 0.05):
    u = ctypes.windll.user32
    dn = _IN(); dn.type = INPUT_MOUSE; dn._input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
    u.SendInput(1, ctypes.byref(dn), ctypes.sizeof(dn))
    time.sleep(max(0.01, hold))
    up = _IN(); up.type = INPUT_MOUSE; up._input.mi.dwFlags = MOUSEEVENTF_LEFTUP
    u.SendInput(1, ctypes.byref(up), ctypes.sizeof(up))

def _smdc(xp: int, yp: int):
    _smc(xp, yp, hold=0.04)
    time.sleep(0.06)
    _smc(xp, yp, hold=0.04)

def _smd(x1: int, y1: int, x2: int, y2: int, duration: float = 0.45, steps: int = 30):
    u = ctypes.windll.user32
    _sma(x1, y1)
    time.sleep(0.05)
    dn = _IN(); dn.type = INPUT_MOUSE; dn._input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
    u.SendInput(1, ctypes.byref(dn), ctypes.sizeof(dn))
    time.sleep(0.05)
    dl = duration / max(1, steps)
    for i in range(1, steps + 1):
        t = i / steps
        e = (1.0 - math.cos(t * math.pi)) / 2.0
        _sma(int(x1 + (x2 - x1) * e), int(y1 + (y2 - y1) * e))
        time.sleep(dl)
    up = _IN(); up.type = INPUT_MOUSE; up._input.mi.dwFlags = MOUSEEVENTF_LEFTUP
    u.SendInput(1, ctypes.byref(up), ctypes.sizeof(up))

def _smms(dx: int, dy: int = 0, duration: float = 0.12, steps: int = 20):
    if dx == 0 and dy == 0:
        return
    dl = duration / steps
    xs = ys = 0
    for i in range(1, steps + 1):
        e  = (1.0 - math.cos(i / steps * math.pi)) / 2.0
        xt = int(dx * e)
        yt = int(dy * e)
        ix, iy = xt - xs, yt - ys
        if ix != 0 or iy != 0:
            _smm(ix, iy)
            xs, ys = xt, yt
        time.sleep(dl)


# h : 0 à 179 c'est opencv
VK = {
    'z': 0x5A, 'q': 0x51, 'a': 0x41, 's': 0x53, 'd': 0x44,
    'e': 0x45, 'f': 0x46, 'r': 0x52,
    'shift': 0x10, 'ctrl': 0x11, 'space': 0x20,
    'enter': 0x0D, 'escape': 0x1B, 'tab': 0x09, 'alt': 0x12,
    'u': 0x55, 'backspace': 0x08, 'end': 0x23, 'home': 0x24,
    '0': 0x60, '1': 0x61, '2': 0x62, '3': 0x63, '4': 0x64,
    '5': 0x65, '6': 0x66, '7': 0x67, '8': 0x68, '9': 0x69,
}

KF = 'z'
KL = 'q'
KR = 'd'
KB = 's'
KS = 'shift'
KI = 'e'

WM_KEYDOWN = 0x0100
WM_KEYUP   = 0x0101
WM_CHAR    = 0x0102

CA  = 45000
CT  = 80


class Ms(Enum):                            # si analyse, majuscule pour suivre le style PEP 8 de python et c'était aussi dû à l'autocomplétion de vscode 
    IDLE       = "idle"
    FORWARD    = "moving_forward"
    TURNING    = "turning"
    RUNNING    = "running"
    APPROACH   = "approaching_target"
    INTERACT   = "interacting"


@dataclass
class Mcd:
    action:    str
    direction: Optional[str] = None
    duration:  float = 0.0
    key:       Optional[str] = None
    timestamp: float = 0.0


class Gi:
    def __init__(self, logger: Lg):
        self.l = logger
        self._hwnd  = None
        self._held  = set()
        self._win_x = 0
        self._win_y = 0
        self._win_w = CFG['res'][0]
        self._win_h = CFG['res'][1]
        self.estop    = False
        self.ms = GCFG['ms']
        self._fwin()

    def _fwin(self) -> bool:
        found = []
        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                if GCFG['wt'].lower() in win32gui.GetWindowText(hwnd).lower():
                    found.append(hwnd)
            return True
        try:
            win32gui.EnumWindows(cb, None)
            if found:
                self._hwnd = found[0]
                r = win32gui.GetWindowRect(self._hwnd)
                self._win_x = r[0]; self._win_y = r[1]
                self._win_w = r[2] - r[0]; self._win_h = r[3] - r[1]
                self.l.i(f"win {self._win_w}x{self._win_h}")
                return True
            self.l.w("win introuvable")
            return False
        except Exception as e:
            self.l.e(f"win err {e}")
            return False

    def ghwnd(self) -> Optional[int]:
        if self._hwnd and win32gui.IsWindow(self._hwnd):
            return self._hwnd
        self._fwin()
        return self._hwnd

    def _vk(self, key: str) -> int:
        k = key.lower()
        if k in VK: return VK[k]
        if len(k) == 1: return ctypes.windll.user32.VkKeyScanW(ord(k)) & 0xFF
        self.l.w(f"vk inconnu {key}")
        return 0

    def _lpd(self, vk: int, repeat: bool = False) -> int:
        sc = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        lp = 1 | (sc << 16)
        if repeat: lp |= (1 << 30)
        return lp

    def _lpu(self, vk: int) -> int:
        sc = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        return 1 | (sc << 16) | (1 << 30) | (1 << 31)

    def kdn(self, key: str):
        if self.estop: return
        hwnd = self.ghwnd()
        if not hwnd: return
        vk = self._vk(key)
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, vk, self._lpd(vk, vk in self._held))
        self._held.add(vk)

    def kup(self, key: str):
        hwnd = self.ghwnd()
        if not hwnd: return
        vk = self._vk(key)
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP, vk, self._lpu(vk))
        self._held.discard(vk)

    def press(self, key: str, duration: float = 0.08):
        if self.estop: return
        hwnd = self.ghwnd()
        if not hwnd: return
        vk = self._vk(key)
        sc = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1 | (sc << 16))
        if duration > 0: time.sleep(duration)
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP,   vk, 1 | (sc << 16) | (1 << 30) | (1 << 31))
        self._held.discard(vk)
        self.l.d(f"key {key} {duration:.3f}s")

    def hold(self, key_char: str, duration: float):
        if self.estop: return
        if not (isinstance(key_char, str) and len(key_char) == 1): return
        vk   = self._vk(key_char)
        hwnd = ctypes.windll.user32.GetForegroundWindow() or self.ghwnd()
        if not hwnd: return
        sc = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1 | (sc << 16))
        time.sleep(duration)
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP,   vk, 1 | (sc << 16) | (1 << 30) | (1 << 31))
        self._held.discard(vk)

    def relk(self, key: str):
        self.kup(key)

    def ttext(self, text: str, delay: float = 0.05):
        if self.estop: return
        for ch in text:
            try: self.press('space' if ch == ' ' else ch, 0.05)
            except Exception: pass
            time.sleep(delay)

    def tnui(self, text: str, delay: float = 0.04):
        if self.estop: return
        hwnd = self.ghwnd()
        if not hwnd: return
        for ch in text:
            ctypes.windll.user32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0)
            time.sleep(delay)

    def rel_keys(self):
        hwnd = self.ghwnd()
        if not hwnd: return
        for vk in list(self._held):
            ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP, vk, self._lpu(vk))
        self._held.clear()
        self.l.d("touches relachees")

    def mm(self, dx: int, dy: int = 0, duration: float = 0.05, steps: int = 6):
        if self.estop: return
        _smms(int(dx * self.ms), 0, duration=duration, steps=steps)

    def cat(self, x: int, y: int, hold: float = 0.05):
        if self.estop: return
        _smc(int(x), int(y), hold=hold)
        self.l.d(f"click_at ({x},{y})")

    def click(self, hold: float = 0.05):
        if self.estop: return
        _scip(hold=hold)

    def dbl_at(self, x: int, y: int):
        if self.estop: return
        _smdc(int(x), int(y))

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.45):
        if self.estop: return
        _smd(int(x1), int(y1), int(x2), int(y2), duration=duration)
        self.l.d(f"drag ({x1},{y1})→({x2},{y2})")

    def mv_cur(self, x: int, y: int):
        _sma(int(x), int(y))

    def focus(self) -> bool:
        hwnd = self.ghwnd()
        if not hwnd: return False
        if win32gui.GetForegroundWindow() != hwnd:
            try: win32gui.SetForegroundWindow(hwnd); time.sleep(0.05)
            except Exception: pass
        return win32gui.GetForegroundWindow() == hwnd

    def emstop(self):
        self.estop = True
        self.rel_keys()
        self.l.w("arret urgence")

    def rstop(self):
        self.estop = False


class Mc:
    def __init__(self, logger: Lg, game_interface: Gi):
        self.l          = logger
        self.gi  = game_interface
        self.cs   = Ms.IDLE
        self.tp = None
        self.cp = Pp(0, 0, 0, 0, time.time())
        self.cmds = deque(maxlen=1000)
        self.nsr = 0.0
        self.sd   = Sd()
        self.msm = Msm()

    def nav_blob(self, blob: dict, crawl_thresh: int = 22000) -> str:
        gi = self.gi
        scx      = gi._win_w // 2
        cx, cy   = blob['center']
        area     = blob['area']
        off      = cx - scx

        mode_now = 'SPRINT' if area < CA // 3 else 'WALK'
        now_t    = time.time()
        if (now_t - getattr(self, '_nlt', 0.0) > 2.0) or (mode_now != getattr(self, '_nlm', None)):
            self.l.i(f"nav c=({cx},{cy}) area={area} off={off:+d} {mode_now}")
            self._nlt = now_t
            self._nlm = mode_now

        STOL = CT
        BTOL = 320
        SFR  = 8000
        SNR  = 12000
        TC   = 0.40
        aoff = abs(off)

        if aoff > STOL:
            wk  = KR if off > 0 else KL
            hk  = getattr(self, '_htk', None)
            cmt = getattr(self, '_tsa', 0.0)
            if hk is not None and hk != wk:
                if (now_t - cmt) < TC:
                    pass
                else:
                    gi.kup(hk); self._htk = None; hk = None
            if hk != wk:
                if hk is not None: gi.kup(hk)
                gi.kdn(wk)
                self._htk = wk
                self._tsa = now_t
                self.l.d(f"turn {wk} off={off:+d}")
        else:
            if getattr(self, '_htk', None) is not None:
                self.l.d(f"turn release off={off:+d}")
                gi.kup(self._htk)
                self._htk = None

        if aoff > BTOL:
            if getattr(self, '_hfw', False): gi.kup(KF); self._hfw = False
            if getattr(self, '_hsp', False): gi.kup(KS); self._hsp = False
            self.cs = Ms.TURNING
            return 'turning'

        if area > crawl_thresh:
            if getattr(self, '_hsp', False): gi.kup(KS); self._hsp = False
            if getattr(self, '_hfw', False): gi.kup(KF); self._hfw = False
            gi.kdn(KF); time.sleep(0.15); gi.kup(KF)
            self.l.d(f"crawl area={area}")
            self.cs = Ms.APPROACH
            return 'navigating'

        if not getattr(self, '_hfw', False):
            gi.kdn(KF); self._hfw = True
            self.l.d("forward on")

        spn = getattr(self, '_hsp', False)
        if spn:
            if area > SNR:
                gi.kup(KS); self._hsp = False
                self.l.i(f"sprint off area={area}")
                self.cs = Ms.FORWARD
            else:
                self.cs = Ms.RUNNING
        else:
            if area < SFR:
                gi.kdn(KS); self._hsp = True
                self.l.i(f"sprint on area={area}")
                self.cs = Ms.RUNNING
            else:
                self.cs = Ms.FORWARD

        return 'navigating'

    def _move_forward(self, duration: float):
        self.cs = Ms.FORWARD
        if duration > 1.0: self._run_forward(duration)
        else: self.gi.press('z', duration)
        self.cs = Ms.IDLE

    def _move_backward(self, duration: float):
        self.gi.press('s', duration)

    def _strafe_left(self, duration: float):
        self.gi.press('a', duration)

    def _strafe_right(self, duration: float):
        self.gi.press('d', duration)

    def _run_forward(self, duration: float):
        self.cs = Ms.RUNNING
        gi = self.gi
        gi.kdn('shift'); gi.kdn('z')
        time.sleep(max(0, duration))
        gi.kup('z'); gi.kup('shift')
        self.cs = Ms.IDLE

    def _rotate_player(self, angle: float):
        if abs(angle) < 1: return
        self.gi.press('d' if angle > 0 else 'a',
                                      max(0.08, min(1.5, abs(angle) / 120.0)))

    def interact(self) -> bool:
        try:
            self.cs = Ms.INTERACT
            self.gi.press('e', 0.15)
            time.sleep(0.3)
            self.cs = Ms.IDLE
            return True
        except Exception as e:
            self.l.e(f"interact err {e}")
            self.cs = Ms.IDLE
            return False

    def find_tgt(self, search_angle: float = None) -> bool:
        try: self.sscan(); return True
        except Exception as e: self.l.e(f"search err {e}"); return False

    def _scan_key(self):
        self.sscan()

    SAD = 0.70
    SPA = 0.45
    SAB = 8
    SED = 2.2
    SPI = 0.05

    def sscan(self, should_stop=None):
        if not hasattr(self, '_sac'): self._sac = 0
        if self._sac >= self.SAB:
            self._sac = 0
            self.l.i(f"search explore {self.SED}s")
            self._hold([KS, KF], self.SED, should_stop)
            return
        self._sac += 1
        self.l.i(f"search arc {self._sac}/{self.SAB}")
        if self._hold([KS, KB, KR], self.SAD, should_stop):
            self.l.i("blob arc stop")
            self._sac = 0
            return
        self.l.d("arc pause")
        self._wait(self.SPA, should_stop)

    TAD = 0.55
    TPA = 0.30
    TAB = 6
    TED = 1.0

    def tscan(self, should_stop=None):
        if not hasattr(self, '_tac'): self._tac = 0
        gi = self.gi
        for k in (KF, KL, KR, KB, KS): gi.kup(k)
        self._htk = None; self._hfw = False; self._hsp = False
        if self._tac >= self.TAB:
            self._tac = 0
            self.l.i(f"truck explore {self.TED}s")
            self._hold([KS, KF], self.TED, should_stop)
            return
        self._tac += 1
        self.l.i(f"truck arc {self._tac}/{self.TAB}")
        if self._hold([KS, KB, KR], self.TAD, should_stop):
            self.l.i("truck arc stop")
            self._tac = 0
            return
        self._wait(self.TPA, should_stop)

    def rst(self):
        self._tac = 0

    def _hold(self, keys, duration: float, should_stop=None) -> bool:
        gi = self.gi
        for k in keys: gi.kdn(k)
        t0 = lr = time.time()
        hit = False
        try:
            while True:
                if time.time() - t0 >= duration: break
                if should_stop is not None and should_stop(): hit = True; break
                if time.time() - lr >= 0.5:
                    for k in keys: gi.kdn(k)
                    lr = time.time()
                time.sleep(self.SPI)
        finally:
            for k in reversed(keys): gi.kup(k)
        return hit

    def _wait(self, duration: float, should_stop=None):
        te = time.time() + duration
        while time.time() < te:
            if should_stop is not None and should_stop(): return
            time.sleep(self.SPI)

    def rss(self):
        self._sac = 0

    def cam_h(self):
        self.l.i("cam horizon")
        _smms(dx=0, dy=-12, duration=0.6, steps=16)
        time.sleep(0.1)

    def nav_circ(self, tc: Oc) -> bool:
        blob = {
            'center': (tc.x, tc.y),
            'area':   int(math.pi * tc.r ** 2),
            'bbox':   (tc.x - tc.r, tc.y - tc.r, tc.r * 2, tc.r * 2),
        }
        return self.nav_blob(blob) == 'collected'

    def stop(self):
        gi = self.gi
        for k in (KF, KL, KR, KB, KS): gi.kup(k)
        gi.rel_keys()
        self._htk = None; self._hfw = False; self._hsp = False
        self.cs   = Ms.IDLE
        self.tp = None

    def mv_done(self) -> bool:
        return self.cs == Ms.IDLE

    def stuck(self) -> bool:
        return self.sd.stuck()

    def fix_stuck(self):
        self.l.w("joueur bloque")
        random.choice([
            lambda: self._move_backward(1.0),
            lambda: self._rotate_player(45),
            lambda: self._strafe_left(0.5),
            lambda: self._strafe_right(0.5),
            lambda: self._rotate_player(-90),
        ])()
        self.sd.reset()

    def mv_stats(self) -> Dict[str, Any]:
        return {
            'state':     self.cs.value,
            'cmds':      len(self.cmds),
            'nav_sr':    self.nsr,
            'stuck':     self.sd.cnt,
            'target':    self.tp,
        }


class Sd:
    def __init__(self):
        self.ph  = deque(maxlen=20)
        self.st  = 5.0
        self.stt = 3.0
        self.sc  = 0
        self.lsm = time.time()
    def upd(self, x: int, y: int):
        t = time.time()
        self.ph.append((x, y, t))
        if len(self.ph) >= 2:
            px, py, _ = self.ph[-2]
            if math.sqrt((x-px)**2 + (y-py)**2) > self.st:
                self.lsm = t
    def stuck(self) -> bool:
        if len(self.ph) < 10: return False
        if time.time() - self.lsm > self.stt:
            self.sc += 1; return True
        return False
    def reset(self):
        self.ph.clear(); self.lsm = time.time()
    @property
    def cnt(self): return self.sc


class Msm:
    def __init__(self):
        self.q  = deque(maxlen=10)
        self.sf = 0.3
    def sm(self, dx: int, dy: int) -> Tuple[int, int]:
        self.q.append((dx, dy))
        if len(self.q) < 3: return dx, dy
        tw = wdx = wdy = 0
        for i, (cdx, cdy) in enumerate(self.q):
            w = (i + 1) * self.sf
            wdx += cdx * w; wdy += cdy * w; tw += w
        return (int(wdx/tw), int(wdy/tw)) if tw else (dx, dy)


Gi      = Gi
Mc = Mc
MovementState      = Ms
StuckDetection     = Sd
MovementSmoother   = Msm

# je remercie encore l'autocomplétion