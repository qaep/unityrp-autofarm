# debug truck : ça permet de visualiser le blob orange et le véhicule utilisé en rose,
# la couleur rose est à demander au méchano (ls customs  ou celui au nord) : https://i.imgur.com/qqvxWNs.png https://i.imgur.com/HOQ2GzE.png
# c'est un rose écarlate.

import cv2
import numpy as np
import mss
import time
import os

hmin, hmax = 135, 168
smin, smax = 40, 255
vmin, vmax = 40, 255

ohmin, ohmax = 2, 20
osmin, ovmin = 200, 120  # s de 200 car le sol, terre et arbres étaient parfois détectés

pma = 200
oma = 40

dw, dh = 960, 540

mmr = (0, 0, 250, 250)
hbp = 150


def excl(mask, h, w, cut_sky=False):
    mx, my, mw, mh = mmr
    mask[h - mh:h, mx:mx + mw] = 0
    mask[h - hbp:h, :] = 0
    if cut_sky:
        sky_cutoff = int(h * 0.35)
        mask[:sky_cutoff, :] = 0
    return mask


def _mpnk(blobs):
    if len(blobs) < 2:
        return blobs
    used = [False] * len(blobs)
    out = []

    for i, bi in enumerate(blobs):
        if used[i]: continue
        group = [bi]
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j, bj in enumerate(blobs):
                if used[j]: continue
                for g in group:
                    gx1, gy1, gw, gh = g['bbox']
                    gx2, gy2 = gx1 + gw, gy1 + gh
                    jx1, jy1, jw, jh = bj['bbox']
                    jx2, jy2 = jx1 + jw, jy1 + jh

                    dx = max(0, max(gx1, jx1) - min(gx2, jx2))
                    dy = max(0, max(gy1, jy1) - min(gy2, jy2))
                    if dx <= 60 and dy <= 60:
                        group.append(bj)
                        used[j] = True
                        changed = True
                        break

        # pour fusionner les bbox en une seule
        x_min = min([b['bbox'][0] for b in group])
        y_min = min([b['bbox'][1] for b in group])
        x_max = max([b['bbox'][0] + b['bbox'][2] for b in group])
        y_max = max([b['bbox'][1] + b['bbox'][3] for b in group])
        w = x_max - x_min
        h = y_max - y_min
        out.append({
            'cx': x_min + w // 2,
            'cy': y_min + h // 2,
            'area': sum([b['area'] for b in group]),
            'bbox': (x_min, y_min, w, h),
            'aspect': h / max(1, w)
        })
    return out

def dblobs(mask, min_area, is_pink=False):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if is_pink and area < 5:
            continue
        elif not is_pink and area < min_area:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        cx, cy = x + w // 2, y + h // 2
        aspect = h / max(1, w)
        blobs.append({
            'cx': cx, 'cy': cy, 'area': int(area),
            'bbox': (x, y, w, h), 'aspect': aspect
        })

    if is_pink:
        blobs = _mpnk(blobs)
        blobs = [b for b in blobs if b['area'] >= min_area]

    blobs.sort(key=lambda b: b['area'], reverse=True)
    return blobs


def main():
    global hmin, hmax, smin, vmin

    os.makedirs("images", exist_ok=True)
    mode = 0
    mode_names = ["Overlay", "Masque seul", "Cote a cote"]

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        print(f"screen: {monitor['width']}x{monitor['height']}")
        print("cmd: q : quit  s: save  +/- : hmax  [/] : hmin  1/2 : smin  3/4 : vmin  m : change mode")

        while True:
            t0 = time.time()

            raw = np.array(sct.grab(monitor))
            frame = raw[:, :, :3]
            fh, fw = frame.shape[:2]
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            pink_lower = np.array([hmin, smin, vmin])
            pink_upper = np.array([hmax, smax, vmax])
            pink_mask = cv2.inRange(hsv, pink_lower, pink_upper)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            pink_mask = cv2.morphologyEx(pink_mask, cv2.MORPH_OPEN, kernel)
            pink_mask = cv2.morphologyEx(pink_mask, cv2.MORPH_CLOSE, kernel)
            pink_mask = excl(pink_mask, fh, fw, cut_sky=True)
            orange_lower = np.array([ohmin, osmin, ovmin])
            orange_upper = np.array([ohmax, 255, 255])
            orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
            kernel_o = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            orange_mask = cv2.morphologyEx(orange_mask, cv2.MORPH_OPEN, kernel_o)
            orange_mask = cv2.morphologyEx(orange_mask, cv2.MORPH_CLOSE, kernel_o)
            orange_mask = excl(orange_mask, fh, fw)
            pink_blobs = dblobs(pink_mask, pma, is_pink=True)
            orange_blobs = dblobs(orange_mask, oma, is_pink=False)
            overlay = frame.copy()
            overlay[pink_mask > 0] = [255, 0, 255]
            overlay[orange_mask > 0] = [0, 140, 255]


            for i, b in enumerate(pink_blobs[:5]):
                bx, by, bw, bh = b['bbox']
                color = (255, 0, 255) if i == 0 else (200, 100, 200)
                cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), color, 3)
                cv2.circle(overlay, (b['cx'], b['cy']), 6, color, -1)
                label = f"PINK #{i+1} area={b['area']} asp={b['aspect']:.1f}"
                cv2.putText(overlay, label, (bx, by - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


            for i, b in enumerate(orange_blobs[:5]):
                bx, by, bw, bh = b['bbox']
                color = (0, 255, 0) if i == 0 else (0, 200, 200)
                cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), color, 2)
                cv2.circle(overlay, (b['cx'], b['cy']), 4, color, -1)
                label = f"ORG #{i+1} a={b['area']} asp={b['aspect']:.1f}"
                cv2.putText(overlay, label, (bx, by - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
            cv2.line(overlay, (fw // 2 - 20, fh // 2), (fw // 2 + 20, fh // 2), (255, 255, 255), 1)
            cv2.line(overlay, (fw // 2, fh // 2 - 20), (fw // 2, fh // 2 + 20), (255, 255, 255), 1)

            fps = 1.0 / max(time.time() - t0, 0.001)
            tot_px = int(np.sum(pink_mask > 0))
            info1 = (f"PINK HSV [{hmin},{smin},{vmin}]-[{hmax},{smax},{vmax}] "
                     f"| blobs={len(pink_blobs)} px={tot_px} | FPS={fps:.0f}")
            info2 = (f"ORANGE blobs={len(orange_blobs)} "
                     f"| Mode: {mode_names[mode]} (m=changer)")
            cv2.putText(overlay, info1, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 255), 2)
            cv2.putText(overlay, info2, (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
            cv2.putText(overlay, "+/-:hmax  [/]:hmin  1/2:smin  3/4:vmin  q:quit  s:save",
                        (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            if mode == 0:
                display = cv2.resize(overlay, (dw, dh))
            elif mode == 1:
                pink_vis = cv2.cvtColor(pink_mask, cv2.COLOR_GRAY2BGR)
                display = cv2.resize(pink_vis, (dw, dh))
            else:
                left = cv2.resize(overlay, (dw // 2, dh))
                pink_vis = cv2.cvtColor(pink_mask, cv2.COLOR_GRAY2BGR)
                right = cv2.resize(pink_vis, (dw // 2, dh))
                display = np.hstack([left, right])

            cv2.imshow("Truck (le véhicule) + le blob orange debug", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                ts = int(time.time())
                cv2.imwrite(f"images/frametruck_{ts}.png", frame)
                cv2.imwrite(f"images/pinkmask_{ts}.png", pink_mask)
                cv2.imwrite(f"images/orangemask_{ts}.png", orange_mask)
                cv2.imwrite(f"images/overlay_{ts}.png", overlay)
                print(f"4 fichiers dans \images\ (ts={ts})")
            elif key == ord('m'):
                mode = (mode + 1) % 3
                print(f"mode {mode_names[mode]}")
            elif key == ord('+') or key == ord('='):
                hmax = min(hmax + 1, 179)
                print(f"tune hmax = {hmax}")
            elif key == ord('-'):
                hmax = max(hmax - 1, hmin + 5)
                print(f"tune hmax = {hmax}")
            elif key == ord(']'):
                hmin = min(hmin + 1, hmax - 5)
                print(f"tune hmin = {hmin}")
            elif key == ord('['):
                hmin = max(hmin - 1, 100)
                print(f"tune hmin = {hmin}")
            elif key == ord('1'):
                smin = min(smin + 5, 200)
                print(f"smin = {smin}")
            elif key == ord('2'):
                smin = max(smin - 5, 20)
                print(f"smin = {smin}")
            elif key == ord('3'):
                vmin = min(vmin + 5, 200)
                print(f"vmin = {vmin}")
            elif key == ord('4'):
                vmin = max(vmin - 5, 20)
                print(f"vmin = {vmin}")

    cv2.destroyAllWindows()
    print(f"\nfin: valeurs hsv :")
    print(f"  lower = np.array([{hmin}, {smin}, {vmin}])")
    print(f"  upper = np.array([{hmax}, {smax}, {vmax}])")


if __name__ == "__main__":
    main()


# credits pour ce fichier: merci à l'autocomplete m'ayant aidé grandement dans l'écriture et c'est super aidant
