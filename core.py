import cv2
import numpy as np
import pyautogui
import time
import threading
import math
import random
import json
import os
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import win32gui
import win32con
import win32api
import win32process
import psutil
from PIL import Image, ImageDraw, ImageFont
import keyboard
import mouse
from collections import deque
import pickle
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import asyncio
from queue import Queue, Empty
import signal
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

CFG = {
    'res': (1720, 1080),
    'ocr': {
        'lower': np.array([0, 50, 50]),   # meilleur hsv, je recommande de ne pas y toucher
        'upper': np.array([35, 255, 255])  # pareil, je recommande de pas y toucher c'est le meilleur pour peu de faux positifs
    },
    'cmr': 5,
    'cMr': 155,
    'dc': 0.5,
    'ms': 0.5,
    'cd': 7.5,
    'sra': 15,
    'msr': 24,
    'si': 0.1,
    'll': logging.INFO,
    'ss': True,
    'sd': 'screenshots',
    'dd': 'data',
    'cf': 'config.json',
    'sf': 'stats.json',
    'bwt':    22.0,
    'pci': 5 * 60,
    'eoc':       8,
    'eow':         8.0,
    'tca':        25000,
    'tct': 0.18,
    'sit': 6,
    'tpf':       'pixels.json',
    'vlk':             False,
}

try:
    _cf = os.path.join(BASE, 'config.json')
    if os.path.exists(_cf):
        with open(_cf, 'r', encoding='utf-8') as _f:
            for _k, _v in json.load(_f).items():
                if isinstance(_v, (str, int, float, bool)):
                    CFG[_k] = _v
except Exception:
    pass

GCFG = {
    'wt': 'FiveM',
    'ik': 'e',
    'mk': {
        'f': 'z',
        'b': 's',
        'l': 'a',
        'r': 'd',
        'rn': 'shift'
    },
    'ms': 1.0,
    'md': 0.1,
    'kpd': 0.05
}

class Et(Enum):
    I = "idle"
    SC = "scanning"
    MV = "moving"
    CO = "collecting"
    W = "waiting"
    SE = "searching"
    GT = "going_truck"
    TR = "transferring"
    PC = "periodic"
    ER = "error"
    PA = "paused"
    ST = "stopped"

@dataclass
class Oc:
    x: int
    y: int
    r: int
    c: float
    t: float
    d: float
    def __post_init__(self):
        sx = CFG['res'][0] // 2
        sy = CFG['res'][1] // 2
        self.d = math.sqrt((self.x - sx) ** 2 + (self.y - sy) ** 2)

@dataclass
class Pp:
    x: float
    y: float
    z: float
    r: float
    t: float

@dataclass
class Cs:
    tc: int = 0
    sc: int = 0
    ta: int = 0
    sr: float = 0.0
    st: float = 0.0
    tr: float = 0.0
    at: float = 0.0
    cd: int = 0
    fp: int = 0

class Lg:
    def __init__(self, n: str = "farm"):
        self.l = logging.getLogger(n)
        self.l.setLevel(CFG['ll'])
        ld = os.path.join(BASE, 'logs')
        os.makedirs(ld, exist_ok=True)
        fh = logging.FileHandler(os.path.join(ld, f'log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'), encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(CFG['ll'])
        fm = logging.Formatter('%(asctime)s - %(message)s')
        fh.setFormatter(fm)
        ch.setFormatter(fm)
        self.l.addHandler(fh)
        self.l.addHandler(ch)
    def d(self, m: str): self.l.debug(m)
    def i(self, m: str): self.l.info(m)
    def w(self, m: str): self.l.warning(m)
    def e(self, m: str): self.l.error(m)
    def c(self, m: str): self.l.critical(m)

class Cm:
    def __init__(self, f: str = CFG['cf']):
        self.f = f
        self.c = CFG.copy()
        self.ld()
    def ld(self):
        try:
            if os.path.exists(self.f):
                with open(self.f, 'r') as f:
                    self.c.update(json.load(f))
        except: pass
    def sv(self):
        try:
            s = self.c.copy()
            if 'ocr' in s:
                s['ocr']['lower'] = s['ocr']['lower'].tolist()
                s['ocr']['upper'] = s['ocr']['upper'].tolist()
            with open(self.f, 'w') as f:
                json.dump(s, f, indent=4)
        except: pass
    def g(self, k: str, d=None): return self.c.get(k, d)
    def s(self, k: str, v):
        self.c[k] = v
        self.sv()

class Sm:
    def __init__(self, f: str = CFG['sf']):
        self.f = f
        self.s = Cs()
        self.ss = time.time()
        self.ld()
    def ld(self):
        try:
            if os.path.exists(self.f):
                with open(self.f, 'r') as f:
                    d = json.load(f)
                    self.s.tc = d.get('tc', 0)
                    self.s.ta = d.get('total_attempts', 0)
                    self.s.tr = d.get('total_runtime', 0.0)
                    self.s.cd = d.get('cd', 0)
                    self.s.fp = d.get('fp', 0)
        except: pass
    def sv(self):
        try:
            d = {
                'tc': self.s.tc,
                'total_attempts': self.s.ta,
                'total_runtime': self.s.tr,
                'cd': self.s.cd,
                'fp': self.s.fp,
                'last_session': datetime.now().isoformat()
            }
            with open(self.f, 'w') as f:
                json.dump(d, f, indent=4)
        except: pass
    def inc_c(self):
        self.s.tc += 1
        self.s.sc += 1
        self.upd_sr()
        self.sv()
    def inc_a(self):
        self.s.ta += 1
        self.upd_sr()
    def upd_sr(self):
        if self.s.ta > 0:
            self.s.sr = self.s.tc / self.s.ta
    def g_sess(self) -> Dict[str, Any]:
        t = time.time() - self.ss
        return {
            'sc': self.s.sc,
            'st': t,
            'cr': self.s.sc / (t / 3600) if t > 0 else 0,
            'tc': self.s.tc,
            'sr': self.s.sr,
            'cd': self.s.cd
        }

class Sc:
    _tl = threading.local()
    def __init__(self, l: Lg):
        self.l = l
        self.c = 0
        self.h = None
        self.r = None
        self.lc = 0.0
        self.ci = 30.0
        if CFG['ss']:
            os.makedirs(os.path.join(BASE, CFG['sd']), exist_ok=True)
        self.fw()
    def gm(self):
        if not hasattr(self._tl, 'mss'):
            import mss as m
            self._tl.mss = m.mss()
        return self._tl.mss
    def fw(self) -> bool:
        try:
            import win32gui
            f = []
            def cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    if GCFG['wt'].lower() in win32gui.GetWindowText(hwnd).lower():
                        f.append(hwnd)
                return True
            win32gui.EnumWindows(cb, None)
            if f:
                self.h = f[0]
                x, y, x1, y1 = win32gui.GetWindowRect(self.h)
                self.r = {'left': x, 'top': y, 'width': x1 - x, 'height': y1 - y}
                self.l.d(f"win ok {x1-x}x{y1-y}")
                return True
            self.l.w("win no")
            return False
        except: return False
    def cap(self, r=None) -> np.ndarray:
        try:
            n = time.time()
            if n - self.lc > self.ci:
                self.fw()
                self.lc = n
            s = self.gm()
            gr = self.r if self.r else s.monitors[1]
            f = np.array(s.grab(gr))[:, :, :3]
            self.c += 1
            return f
        except Exception as e:
            self.l.e(f"cap err {e}")
            return np.array([])
    def prep(self, i: np.ndarray) -> np.ndarray:
        return i

AIState = Et
OrangeCircle = Oc
PlayerPosition = Pp
CollectionStats = Cs
Logger = Lg
ConfigManager = Cm
StatsManager = Sm
ScreenCapture = Sc
CONFIG = CFG
GAME_CONFIG = GCFG