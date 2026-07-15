import cv2
import numpy as np
import math
import time
from typing import List, Optional, Dict, Any
from collections import deque
from core import Oc, Lg, CFG
import os
import traceback

try:
    import pytesseract
    _tpaths = [
        CFG.get('tess', ''),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Tesseract-OCR', 'tesseract.exe'),
    ]
    for _tp in _tpaths:
        if _tp and os.path.exists(_tp):
            pytesseract.pytesseract.tesseract_cmd = _tp
            break
except ImportError:
    pytesseract = None

# MEILLEUR HSV ORANGE!!
HSV_LOWER = np.array([2, 200, 120])
HSV_UPPER = np.array([20, 255, 255])

# MEILLEUR HSV ROSE TRUCK! h_max = 165 exclut ciel et coucher du soleil, (h à 170+), s_min = 110 exclut rose pale du sol et arbres
HSV_PINK_LOWER = np.array([125, 70, 60])
HSV_PINK_UPPER = np.array([175, 255, 255])

# beige actuellement obsolète, je le fixerai plus tard, si besoin faites une "issue" sur github
HSV_BEIGE_LOWER1 = np.array([0,   80, 40])
HSV_BEIGE_UPPER1 = np.array([10, 255, 255])
HSV_BEIGE_LOWER2 = np.array([160, 80, 40])
HSV_BEIGE_UPPER2 = np.array([179, 255, 255])

bma  = 220
bpma = 800
bbma = 300
bam  = 1.15
bhm  = 15
mxt  = 60
myg  = 400
mpxt = 60
mpyt = 60
mbxt = 80
mbyt = 80
mmr  = (0, 0, 250, 250)
hbp  = 150


def _build_pink_mask(f):
    hsv  = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HSV_PINK_LOWER, HSV_PINK_UPPER)
    k    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    h, w = mask.shape
    mask[:int(h * 0.05), :] = 0
    mx, my, mw, mh = mmr
    mask[h - mh:h, mx:mx + mw] = 0
    mask[h - hbp:h, :] = 0
    return mask


def _merge_pink_blobs(blobs):
    if len(blobs) < 2:
        return blobs
    used = [False] * len(blobs)
    out  = []
    for i, bi in enumerate(blobs):
        if used[i]:
            continue
        group = [bi]
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j, bj in enumerate(blobs):
                if used[j]:
                    continue
                for g in group:
                    gx1, gy1, gw, gh = g['bbox']
                    gx2, gy2 = gx1 + gw, gy1 + gh
                    jx1, jy1, jw, jh = bj['bbox']
                    jx2, jy2 = jx1 + jw, jy1 + jh
                    dx = max(0, max(gx1, jx1) - min(gx2, jx2))
                    dy = max(0, max(gy1, jy1) - min(gy2, jy2))
                    if dx <= mpxt and dy <= mpyt:
                        group.append(bj)
                        used[j] = True
                        changed = True
                        break
        if len(group) == 1:
            out.append(bi)
            continue
        xs  = [g['bbox'][0] for g in group]
        ys  = [g['bbox'][1] for g in group]
        x2s = [g['bbox'][0] + g['bbox'][2] for g in group]
        y2s = [g['bbox'][1] + g['bbox'][3] for g in group]
        mx, my = min(xs), min(ys)
        mw, mh = max(x2s) - mx, max(y2s) - my
        out.append({
            'center': (mx + mw // 2, my + mh // 2),
            'area':   int(sum(g['area'] for g in group)),
            'bbox':   (mx, my, mw, mh),
            'radius': max(mw, mh) // 2,
            'merged_count': len(group),
        })
    return out


def _build_beige_mask(f):
    hsv   = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, HSV_BEIGE_LOWER1, HSV_BEIGE_UPPER1)
    mask2 = cv2.inRange(hsv, HSV_BEIGE_LOWER2, HSV_BEIGE_UPPER2)
    mask  = cv2.bitwise_or(mask1, mask2)
    k     = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask  = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask  = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    h, w  = mask.shape
    mx, my, mw, mh = mmr
    mask[h - mh:h, mx:mx + mw] = 0
    mask[h - hbp:h, :] = 0
    return mask


def _merge_beige_blobs(blobs):
    if len(blobs) < 2:
        return blobs
    used = [False] * len(blobs)
    out  = []
    for i, bi in enumerate(blobs):
        if used[i]:
            continue
        group = [bi]
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j, bj in enumerate(blobs):
                if used[j]:
                    continue
                for g in group:
                    gx1, gy1, gw, gh = g['bbox']
                    gx2, gy2 = gx1 + gw, gy1 + gh
                    jx1, jy1, jw, jh = bj['bbox']
                    jx2, jy2 = jx1 + jw, jy1 + jh
                    dx = max(0, max(gx1, jx1) - min(gx2, jx2))
                    dy = max(0, max(gy1, jy1) - min(gy2, jy2))
                    if dx <= mbxt and dy <= mbyt:
                        group.append(bj)
                        used[j] = True
                        changed = True
                        break
        xmn = min(b['bbox'][0] for b in group)
        ymn = min(b['bbox'][1] for b in group)
        xmx = max(b['bbox'][0] + b['bbox'][2] for b in group)
        ymx = max(b['bbox'][1] + b['bbox'][3] for b in group)
        w   = xmx - xmn
        h   = ymx - ymn
        out.append({
            'center': (xmn + w // 2, ymn + h // 2),
            'area':   sum(b['area'] for b in group),
            'bbox':   (xmn, ymn, w, h),
            'radius': max(w, h) // 2,
            'merged_count': len(group),
        })
    return out


def _build_orange_mask(f):
    hsv  = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
    k    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    h, w = mask.shape
    mx, my, mw, mh = mmr
    mask[h - mh:h, mx:mx + mw] = 0
    mask[h - hbp:h, :] = 0
    return mask


def _merge_vertical_fragments(blobs):
    if len(blobs) < 2:
        return blobs
    sb   = sorted(blobs, key=lambda b: b['bbox'][0] + b['bbox'][2] / 2)
    used = [False] * len(sb)
    out  = []
    for i, bi in enumerate(sb):
        if used[i]:
            continue
        group = [bi]
        used[i] = True
        xi = bi['bbox'][0] + bi['bbox'][2] / 2
        for j in range(i + 1, len(sb)):
            if used[j]:
                continue
            bj = sb[j]
            xj = bj['bbox'][0] + bj['bbox'][2] / 2
            if abs(xj - xi) > mxt:
                continue
            ok = False
            for g in group:
                gy1, gy2 = g['bbox'][1], g['bbox'][1] + g['bbox'][3]
                jy1, jy2 = bj['bbox'][1], bj['bbox'][1] + bj['bbox'][3]
                gap = max(0, max(gy1, jy1) - min(gy2, jy2))
                if gap <= myg:
                    ok = True
                    break
            if ok:
                group.append(bj)
                used[j] = True
        if len(group) == 1:
            out.append(bi)
            continue
        xs  = [g['bbox'][0] for g in group]
        ys  = [g['bbox'][1] for g in group]
        x2s = [g['bbox'][0] + g['bbox'][2] for g in group]
        y2s = [g['bbox'][1] + g['bbox'][3] for g in group]
        mx, my = min(xs), min(ys)
        mw, mh = max(x2s) - mx, max(y2s) - my
        area   = sum(g['area'] for g in group)
        aspect = mh / max(1, mw)
        out.append({
            'center': (mx + mw // 2, my + mh // 2),
            'area':   int(area),
            'bbox':   (mx, my, mw, mh),
            'radius': max(mw, mh) // 2,
            'aspect': aspect,
            'is_beam': aspect >= bam and mh >= bhm,
            'merged_count': len(group),
        })
    return out


class Vs:
    def __init__(self, logger: Lg):
        self.l = logger
        self.dtms = deque(maxlen=100)
        self.dcnt = 0

    def d_org(self, frame_bgr: np.ndarray) -> List[Dict[str, Any]]:
        t0 = time.time()
        try:
            mask = _build_orange_mask(frame_bgr)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            blobs = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < bma:
                    continue
                x, y, bw, bh = cv2.boundingRect(cnt)
                cx = x + bw // 2
                cy = y + bh // 2
                aspect  = bh / max(1, bw)
                is_beam = aspect >= bam and bh >= bhm
                blobs.append({
                    'center':  (cx, cy),
                    'area':    int(area),
                    'bbox':    (x, y, bw, bh),
                    'radius':  max(bw, bh) // 2,
                    'aspect':  aspect,
                    'is_beam': is_beam,
                })
            blobs = _merge_vertical_fragments(blobs)
            blobs.sort(key=lambda b: b['area'], reverse=True)
            dt = time.time() - t0
            self.dtms.append(dt)
            self.dcnt += 1
            self.l.d(f"orange {len(blobs)} blobs {dt*1000:.1f}ms")
            return blobs
        except Exception as e:
            self.l.e(f"orange detect err {e}")
            return []

    def dcp(self, frame_bgr: np.ndarray) -> bool:
        h, w = frame_bgr.shape[:2]
        y1, y2 = 5, min(90, h)
        x2 = min(650, w)
        roi = frame_bgr[y1:y2, 0:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        roi_mean = float(np.mean(gray))

        if roi_mean >= 195:
            return False

        if roi_mean < 60:
            tv = 140
        elif roi_mean < 120:
            tv = 165
        else:
            tv = 190

        _, thresh = cv2.threshold(gray, tv, 255, cv2.THRESH_BINARY)
        key_zone  = int(np.sum(thresh[:, 0:65] > 0))
        text_end  = min(350, thresh.shape[1])
        text_zone = int(np.sum(thresh[:, 70:text_end] > 0))

        if not hasattr(self, '_pcn'):
            self._pcn = 0
        self._pcn += 1
        if self._pcn % 60 == 0:
            self.l.d(f"prompt scan key={key_zone} txt={text_zone} mean={roi_mean:.0f}")

        pixel_pass = (key_zone >= 300) and (text_zone > 400)

        if not pixel_pass:
            self._prompt_was_detected = False
            self._pixel_pass_streak   = 0
            return False

        now    = time.time()
        last_ok = getattr(self, '_prompt_ocr_last_ok', 0.0)
        if now - last_ok < 1.0:
            self._prompt_was_detected = True
            return True

        pp_streak = getattr(self, '_pixel_pass_streak', 0) + 1
        self._pixel_pass_streak = pp_streak

        ocr_ok = self._ocr_prompt(roi)

        force = False
        if (not ocr_ok) and (pp_streak >= 3) and (350 <= key_zone <= 1800):
            force = True
            self.l.i(f"prompt force x{pp_streak} key={key_zone}")

        if (not ocr_ok) and (not force):
            if not getattr(self, '_prompt_ocr_rej', False):
                self.l.i(f"prompt rejete key={key_zone} streak={pp_streak}")
            self._prompt_ocr_rej = True
            self._prompt_was_detected = False
            return False
        self._prompt_ocr_rej = False

        self._prompt_ocr_last_ok = now
        if not getattr(self, '_prompt_was_detected', False):
            tag = "[FORCE]" if force else "[OCR]"
            self.l.i(f"prompt detecte key={key_zone} {tag}")
        self._prompt_was_detected = True
        return True

    def _ocr_prompt(self, roi_bgr) -> bool:
        if pytesseract is None:
            return True
        try:
            import unicodedata
            gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
            big  = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            preprocs = []
            for thr in (200, 170, 140):
                _, m = cv2.threshold(big, thr, 255, cv2.THRESH_BINARY)
                preprocs.append(cv2.bitwise_not(m))
            try:
                ad = cv2.adaptiveThreshold(big, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 21, -10)
                preprocs.append(cv2.bitwise_not(ad))
            except Exception:
                pass
            kw = ('ramasser', 'amasse', 'masse', 'feuille', 'euille', 'feuil',
                  'orange', 'rang', 'tabac', 'abac', 'pour', 'our ', 'des f')
            best = ''
            for img in preprocs:
                for psm in ('--psm 7', '--psm 6'):
                    try:
                        try:
                            txt = pytesseract.image_to_string(img, lang='fra', config=psm)
                        except Exception:
                            txt = pytesseract.image_to_string(img, config=psm)
                    except Exception:
                        continue
                    norm = unicodedata.normalize('NFD', txt.lower()).encode('ascii', 'ignore').decode('ascii')
                    if any(k in norm for k in kw):
                        return True
                    if len(norm.strip()) > len(best):
                        best = norm.strip()
            self.l.d(f"ocr prompt='{best[:80]}'")
            return False
        except Exception as e:
            self.l.d(f"ocr confirm err {e}")
            return True

    def d_pnk(self, frame_bgr: np.ndarray) -> List[Dict[str, Any]]:
        t0 = time.time()
        try:
            mask = _build_pink_mask(frame_bgr)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            blobs = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 5:
                    continue
                x, y, bw, bh = cv2.boundingRect(cnt)
                blobs.append({
                    'center': (x + bw // 2, y + bh // 2),
                    'area':   int(area),
                    'bbox':   (x, y, bw, bh),
                    'radius': max(bw, bh) // 2,
                })
            blobs    = _merge_pink_blobs(blobs)
            raw      = sorted(blobs, key=lambda b: b['area'], reverse=True)
            fh, fw   = frame_bgr.shape[:2]
            def _ok(b):
                if b['area'] < bpma:
                    return False
                bx, by, bw, bh = b['bbox']
                if bh <= 0 or bw <= 0:
                    return False
                asp = bw / float(bh)
                cy  = by + bh // 2
                if asp < 0.30:       return False
                if asp > 6.0:        return False
                if bw > fw * 0.60:   return False
                if cy < fh * 0.12 and bw > fw * 0.30: return False
                if b['area'] / float(bw * bh) < 0.30: return False
                return True
            blobs = [b for b in blobs if _ok(b)]
            blobs.sort(key=lambda b: b['area'], reverse=True)
            if not blobs and raw:
                now = time.time()
                if now - getattr(self, '_lpd', 0) > 8.0:
                    top = raw[0]
                    bx, by, bw, bh = top['bbox']
                    asp  = bw / float(bh) if bh > 0 else 0
                    fill = top['area'] / float(max(1, bw * bh))
                    cy   = by + bh // 2
                    self.l.i(
                        f"pink rejete area={top['area']} {bw}x{bh}@({bx},{by}) "
                        f"cy={cy}/{fh} asp={asp:.2f} fill={fill:.2f}"
                    )
                    self._lpd = now
            if blobs:
                self.l.d(f"pink {len(blobs)} blobs area={blobs[0]['area']} {(time.time()-t0)*1000:.1f}ms")
            return blobs
        except Exception as e:
            self.l.e(f"pink detect err {e}")
            return []

    def d_bge(self, frame_bgr: np.ndarray) -> List[Dict[str, Any]]:
        t0 = time.time()
        try:
            mask = _build_beige_mask(frame_bgr)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            blobs = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 5:
                    continue
                x, y, bw, bh = cv2.boundingRect(cnt)
                blobs.append({
                    'center': (x + bw // 2, y + bh // 2),
                    'area':   int(area),
                    'bbox':   (x, y, bw, bh),
                    'radius': max(bw, bh) // 2,
                })
            blobs = _merge_beige_blobs(blobs)
            blobs = [b for b in blobs if b['area'] >= bbma]
            blobs.sort(key=lambda b: b['area'], reverse=True)
            if blobs:
                self.l.d(f"beige {len(blobs)} blobs area={blobs[0]['area']} {(time.time()-t0)*1000:.1f}ms")
            return blobs
        except Exception as e:
            self.l.e(f"beige detect err {e}")
            return []

    def dbf(self, frame_bgr: np.ndarray, force_ocr: bool = False) -> bool:
        now = time.time()
        if not force_ocr:
            if now - getattr(self, 'lbft', 0) < 1.0:
                return False
        self.lbft = now
        h, w = frame_bgr.shape[:2]
        y1 = max(0, h - 280)
        y2 = max(0, h - 100)
        x1, x2 = 5, min(440, w)
        if y2 <= y1 or x2 <= x1:
            return False
        roi = frame_bgr[y1:y2, x1:x2]
        hsv  = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        red1 = cv2.inRange(hsv, np.array([0,   140, 100]), np.array([10,  255, 255]))
        red2 = cv2.inRange(hsv, np.array([170, 140, 100]), np.array([179, 255, 255]))
        rpx  = int(np.sum((red1 | red2) > 0))
        if rpx < 80:
            return False
        if pytesseract is None:
            self.l.w("pytesseract absent bag_full off")
            return False
        try:
            import unicodedata
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            big  = cv2.resize(gray, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
            mask = cv2.adaptiveThreshold(big, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY, 21, -8)
            disc = ('place', 'pas ')
            gen  = ('assez', 'avez', 'vous')
            for psm in ('--psm 6', '--psm 11'):
                try:
                    txt = pytesseract.image_to_string(mask, lang='fra', config=psm)
                except Exception:
                    txt = pytesseract.image_to_string(mask, config=psm)
                norm = unicodedata.normalize('NFD', txt).encode('ascii', 'ignore').decode('ascii').lower()
                dh = [k for k in disc if k in norm]
                gh = [k for k in gen  if k in norm]
                if len(dh) >= 1 and len(gh) >= 1:
                    self.l.i(f"bag full red={rpx} hits={dh+gh}")
                    return True
            if now - getattr(self, '_lbd', 0) > 5.0:
                self.l.i(f"bag full pre-filtre ok red={rpx} ocr fail")
                self._lbd = now
            return False
        except Exception as e:
            self.l.d(f"bag full ocr err {e}")
            return False

    def dvh(self, frame_bgr: np.ndarray) -> Optional[str]:
        h, w = frame_bgr.shape[:2]
        y1 = max(0, h - 340)
        y2 = max(0, h - 120)
        x1, x2 = 20, min(650, w)
        if y2 <= y1 or x2 <= x1:
            return None
        roi = frame_bgr[y1:y2, x1:x2]
        hsv   = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        gm    = cv2.inRange(hsv, np.array([40,  80,  80]), np.array([85,  255, 255]))
        rm1   = cv2.inRange(hsv, np.array([0,  120, 100]), np.array([10,  255, 255]))
        rm2   = cv2.inRange(hsv, np.array([170,120, 100]), np.array([179, 255, 255]))
        rm    = cv2.bitwise_or(rm1, rm2)
        gpx   = int(np.sum(gm > 0))
        rpx   = int(np.sum(rm > 0))
        if gpx < 80 and rpx < 80:
            return None
        if gpx > 200 and gpx > rpx * 1.5:
            self.l.i(f"hud deverrouille g={gpx}")
            return "unlocked"
        if rpx > 200 and rpx > gpx * 1.5:
            status = "locked"
            if pytesseract is not None:
                try:
                    import unicodedata
                    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    _, th = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                    try:
                        text = pytesseract.image_to_string(th, lang='fra', config='--psm 6')
                    except Exception:
                        text = pytesseract.image_to_string(th, config='--psm 6')
                    norm = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('ascii').lower()
                    if 'coffre' in norm:
                        status = "still_locked"
                except Exception as e:
                    self.l.d(f"ocr hud rouge err {e}")
            self.l.i(f"hud {status.upper()} r={rpx}")
            return status
        if pytesseract is None:
            return None
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        try:
            text = pytesseract.image_to_string(th, lang='fra', config='--psm 6')
        except Exception:
            try:
                text = pytesseract.image_to_string(th, config='--psm 6')
            except Exception as e:
                self.l.w(f"ocr hud err {e}")
                return None
        import unicodedata
        norm = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('ascii').lower()
        if 'coffre' in norm and 'verrouille' in norm:
            return "still_locked"
        if 'deverrouille' in norm:
            return "unlocked"
        if 'verrouille' in norm:
            return "locked"
        return None

    def dmi(self, frame_bgr: np.ndarray, text: str) -> Optional[tuple]:
        match, pos = self.damip(frame_bgr, [text])
        return pos if match == text else None

    def damip(self, frame_bgr: np.ndarray,
                                      texts: list, target_cx=None, target_cy=None):
        import unicodedata
        if pytesseract is None:
            self.l.w("pytesseract absent menu detect fail")
            return None, None
        from pytesseract import Output
        h, w   = frame_bgr.shape[:2]
        mx, my = 350, 350
        cxs    = target_cx if target_cx is not None else w // 2
        cys    = target_cy if target_cy is not None else h // 2
        x1 = max(0, int(cxs) - mx)
        x2 = min(w, int(cxs) + mx)
        y1 = max(0, int(cys) - my)
        y2 = min(h, int(cys) + my)
        roi = frame_bgr[y1:y2, x1:x2]
        gray     = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        big_gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        mask     = cv2.adaptiveThreshold(big_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY, 21, -15)
        img_ocr  = cv2.bitwise_not(mask)
        targets_map = {}
        for t in texts:
            tn = unicodedata.normalize('NFD', t.upper()).encode('ascii', 'ignore').decode('ascii')
            wds = [ww for ww in tn.split() if len(ww) >= 4]
            if wds:
                targets_map[t] = wds
        if not targets_map:
            return None, None
        candidates  = []
        all_ocr_wds = []
        MIN_CONF    = 35
        for config in ['--psm 6', '--psm 11']:
            if candidates:
                break
            try:
                try:
                    data = pytesseract.image_to_data(img_ocr, lang='fra', config=config,
                                                     output_type=Output.DICT)
                except Exception:
                    data = pytesseract.image_to_data(img_ocr, config=config,
                                                     output_type=Output.DICT)
                n = len(data['text'])
                for i in range(n):
                    word = data['text'][i].strip()
                    if not word or len(word) < 3:
                        continue
                    conf = int(data['conf'][i]) if str(data['conf'][i]).lstrip('-').isdigit() else 0
                    wn   = unicodedata.normalize('NFD', word.upper()).encode('ascii', 'ignore').decode('ascii')
                    all_ocr_wds.append((word, wn, conf))
                    if conf < MIN_CONF:
                        continue
                    mw = None
                    mb = None
                    for bt, tw_list in targets_map.items():
                        for tw in tw_list:
                            if wn == tw or (len(tw) >= 5 and tw in wn) or (len(wn) >= 5 and wn in tw):
                                mw = tw
                                mb = bt
                                break
                        if mw:
                            break
                    if mw is None:
                        continue
                    bx = (int(data['left'][i]) // 2) + x1
                    by = (int(data['top'][i])  // 2) + y1
                    bw = int(data['width'][i])  // 2
                    bh = int(data['height'][i]) // 2
                    candidates.append((bx + bw // 2, by + bh // 2, mw, conf, word, mb))
            except Exception:
                continue
        if not candidates:
            if all_ocr_wds:
                top = sorted(all_ocr_wds, key=lambda x: -x[2])[:12]
                self.l.w(
                    f"ocr no match {texts} roi ({x1},{y1})-({x2},{y2}) "
                    + " | ".join(f"'{ww}'({wn},{c})" for ww, wn, c in top)
                )
            else:
                self.l.w(f"ocr aucun mot roi ({x1},{y1})-({x2},{y2})")
            try:
                import time as _t
                dbg = os.path.join(os.path.dirname(__file__), 'debug_ocr')
                os.makedirs(dbg, exist_ok=True)
                ts = int(_t.time() * 1000) % 100000
                cv2.imwrite(os.path.join(dbg, f'roi_{ts}.png'), roi)
                cv2.imwrite(os.path.join(dbg, f'mask_{ts}.png'), img_ocr)
                self.l.i(f"roi dump debug_ocr/roi_{ts}.png")
            except Exception as e:
                self.l.d(f"roi dump err {e}")
            return None, None
        for bt in texts:
            if bt not in targets_map:
                continue
            tgt_wds = targets_map[bt]
            tc = [c for c in candidates if c[5] == bt]
            if not tc:
                continue
            if len(tgt_wds) == 1:
                best = max(tc, key=lambda c: c[3])
                self.l.i(f"menu '{bt}' ({best[0]},{best[1]}) conf={best[3]}")
                return bt, (best[0], best[1])
            CDIST = 250
            for i, ci in enumerate(tc):
                cluster   = [ci]
                seen      = {ci[2]}
                for j, cj in enumerate(tc):
                    if i == j:
                        continue
                    ddx = cj[0] - ci[0]
                    ddy = cj[1] - ci[1]
                    if (ddx*ddx + ddy*ddy) <= CDIST*CDIST:
                        cluster.append(cj)
                        seen.add(cj[2])
                if seen >= set(tgt_wds):
                    ccx = sum(c[0] for c in cluster) // len(cluster)
                    ccy = sum(c[1] for c in cluster) // len(cluster)
                    self.l.i(f"menu multi '{bt}' ({ccx},{ccy})")
                    return bt, (ccx, ccy)
        return None, None

    def dsc(self, frame_bgr: np.ndarray, slot_x: int,
                          slot_y: int, slot_size: int = 80) -> Optional[int]:
        if pytesseract is None:
            return None
        import re
        h, w = frame_bgr.shape[:2]
        bx1 = max(0, slot_x)
        bx2 = min(w, slot_x + slot_size // 2 + 10)
        by1 = max(0, slot_y - slot_size // 2 - 5)
        by2 = min(h, slot_y - 5)
        if bx2 <= bx1 or by2 <= by1:
            return None
        roi  = frame_bgr[by1:by2, bx1:bx2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        big  = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        _, th = cv2.threshold(big, 180, 255, cv2.THRESH_BINARY)
        try:
            text = pytesseract.image_to_string(th, config='--psm 8 -c tessedit_char_whitelist=0123456789')
        except Exception as e:
            self.l.d(f"slot count err {e}")
            return None
        m = re.search(r'(\d{1,3})', text.strip())
        if not m:
            try:
                t2 = pytesseract.image_to_string(th, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                m  = re.search(r'(\d{1,3})', t2.strip())
            except Exception:
                pass
        if not m:
            return None
        try:
            val = int(m.group(1))
            if 1 <= val <= 999:
                self.l.i(f"slot count ({slot_x},{slot_y}) = {val}")
                return val
        except ValueError:
            pass
        return None

    def diw(self, frame_bgr: np.ndarray) -> Optional[float]:
        import re
        if pytesseract is None:
            return None
        h, w = frame_bgr.shape[:2]
        x1 = int(w * 0.15)
        x2 = int(w * 0.45)
        y1 = int(h * 0.10)
        y2 = int(h * 0.20)
        roi  = frame_bgr[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        try:
            text = pytesseract.image_to_string(th, config='--psm 6 -c tessedit_char_whitelist=0123456789./kg ')
        except Exception as e:
            self.l.w(f"ocr poids err {e}")
            return None
        m = re.search(r'(\d+(?:\.\d+)?)\s*/\s*24', text)
        if m:
            try:
                val = float(m.group(1))
                self.l.i(f"poids {val:.2f}/24")
                return val
            except ValueError:
                pass
        self.l.d(f"ocr poids fail text={text!r}")
        return None

    def d_org_circles(self, frame_bgr: np.ndarray) -> List[Oc]:
        blobs = self.d_org(frame_bgr)
        out   = []
        for b in blobs:
            cx, cy = b['center']
            out.append(Oc(x=cx, y=cy, r=b['radius'], c=1.0, t=time.time(), d=0))
        return out

    def gbt(self, blobs: List[Dict], screen_w: int = None,
                        previous: Optional[Dict] = None) -> Optional[Dict]:
        if not blobs:
            return None
        if screen_w is None:
            screen_w = CFG['res'][0]
        beams = [b for b in blobs if b.get('is_beam')]
        if beams:
            pool = beams
        else:
            pool = [b for b in blobs if b.get('aspect', 0) > 0.3 and b['area'] > 100]
            if not pool:
                return None
        pool_sorted = sorted(pool, key=lambda b: b['area'], reverse=True)
        best = pool_sorted[0]
        if previous is not None:
            px, py    = previous['center']
            prev_area = previous.get('area', 0)
            def dist2(b):
                return (b['center'][0] - px) ** 2 + (b['center'][1] - py) ** 2
            same   = min(pool, key=dist2)
            same_d = dist2(same) ** 0.5
            if same_d < 200 and best['area'] < same['area'] * 2.0:
                return same
            if prev_area >= 2000:
                bx, by   = best['center']
                best_d   = ((bx - px) ** 2 + (by - py) ** 2) ** 0.5
                if best['area'] < 800 and best_d > 400:
                    self.l.i(f"overshoot prev={prev_area} new={best['area']} d={best_d:.0f}")
                    return None
        return best

    def dperf(self) -> Dict[str, float]:
        if not self.dtms:
            return {}
        return {
            'average_detection_time': float(np.mean(self.dtms)),
            'max_detection_time':     float(np.max(self.dtms)),
            'min_detection_time':     float(np.min(self.dtms)),
            'total_detections':       self.dcnt,
        }

    def dbg(self, frame_bgr: np.ndarray, blobs: List[Dict]) -> np.ndarray:
        out = frame_bgr.copy()
        sw  = frame_bgr.shape[1]
        sh  = frame_bgr.shape[0]
        cv2.line(out, (sw//2-20, sh//2), (sw//2+20, sh//2), (255,255,255), 1)
        cv2.line(out, (sw//2, sh//2-20), (sw//2, sh//2+20), (255,255,255), 1)
        for i, blob in enumerate(blobs[:5]):
            cx, cy = blob['center']
            x, y, bw, bh = blob['bbox']
            col = (0,255,0) if i == 0 else (0,200,200)
            cv2.rectangle(out, (x, y), (x+bw, y+bh), col, 2)
            cv2.circle(out, (cx, cy), 4, col, -1)
            cv2.putText(out, f"#{i+1} area={blob['area']}",
                        (x, y-6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1)
        return out


Vs = Vs
