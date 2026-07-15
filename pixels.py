"""
Outil de calibration pour le systeme truck / coffre / inventaire.

Usage :
    python capture_truck_pixels.py

Le script guide pas a pas pour placer la souris sur chaque element et
enregistre les coordonnees dans truck_pixels.json.

NOTE : "menu_ouvrir_coffre" n'est PAS dans cette liste — le menu Alt
contextuel change de position selon l'angle camera. Il est detecte
dynamiquement par OCR (detect_menu_item_position dans vision_system.py).

Seuls les elements dont la position est FIXE (UI inventaire, popup
quantite centree) sont calibres ici.
"""

import json
import os
import sys
import time

try:
    import pyautogui
except ImportError:
    print("[FATAL] pyautogui non installe. pip install pyautogui")
    sys.exit(1)

PXF = os.path.join(os.path.dirname(__file__), "pixels.json")

STEPS = [
    ("srch",
     "tab -> barre de recherche (haut gauche) -> entree",
     False),

    ("org_itm",
     "tape n'importe quel item dans la barre de recherche -> survole le 1er item (slot 1)-> entree",
     False),

    ("drop",
     "alt -> ouvre coffre pickup -> survole 1er slot libre (zone droite) -> entree",
     False),

    ("qty",
     "popup quantite apres drag : survole le champ de texte -> entree",
     True),

    ("cfm",
     "boutton 'confirmer' drag un objet dans l'inv de proximité, sélectionne un nombre d'items puis survole le boutton confirmer -> entree",
     True),

    ("eat_itm",
     "recherche un item à manger dans ton inventaire puis survole le slot 1 -> entree",
     False),
]


def load_ex() -> dict:
    if os.path.exists(PXF):
        try:
            with open(PXF, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save(coords: dict):
    with open(PXF, "w", encoding="utf-8") as f:
        json.dump(coords, f, indent=2, ensure_ascii=False)


def cap_all():
    coords = load_ex()
    print(f"=== Calibration truck_pixels.json ===")
    print(f"Fichier : {PXF}")
    print()
    print("NOTE : le menu 'OUVRIR LE COFFRE' (Alt) est detecte par OCR automatiquement")
    print("       — pas besoin de calibrer sa position.")
    print()

    pyautogui.FAILSAFE = False
    try:
        for key, desc, optional in STEPS:
            current = coords.get(key)
            calibrated = current and (current.get('x', 0) > 0 or current.get('y', 0) > 0)
            cur_txt = f"(actuel : {current})" if calibrated else "(non calibre)"
            opt_txt = " [OPTIONNEL]" if optional else ""
            print(f"--- {key}{opt_txt} {cur_txt} ---")
            print(desc)
            prompt = "[ENTREE]=capturer"
            if calibrated:
                prompt += ", r=recalibrer"
            if optional:
                prompt += ", s=skip"
            prompt += ", q=quitter  "
            choice = input(prompt).strip().lower()
            if choice == "q":
                break
            if choice == "s":
                print("  skip.\n")
                continue
            if choice != "r" and calibrated:
                print("  Conserve l'ancienne valeur.\n")
                continue
            print("  Positionne ta souris sur l'element...")
            print("  Tu as 3s pour bien positionner...")
            for i in (3, 2, 1):
                print(f"  {i}...")
                time.sleep(1)
            pos = pyautogui.position()
            coords[key] = {"x": int(pos.x), "y": int(pos.y)}
            save(coords)
            print(f"  OK → ({pos.x}, {pos.y})\n")
    finally:
        pyautogui.FAILSAFE = True

    print("=== Calibration terminee ===")
    print()
    for k, v in coords.items():
        calibrated = v.get('x', 0) > 0 or v.get('y', 0) > 0
        status = "OK" if calibrated else "NON CALIBRE"
        print(f"  {k:20} {v}  [{status}]")


def tst1(key: str):
    coords = load_ex()
    if key not in coords:
        print(f"[ERR] '{key}' absent de {PXF}")
        return
    c = coords[key]
    if c.get('x', 0) <= 0:
        print(f"[WARN] '{key}' non calibre (x=0)")
        return
    print(f"Dans 3s deplace la souris sur {key} ({c['x']},{c['y']})")
    time.sleep(3)
    pyautogui.moveTo(c["x"], c["y"], duration=0.3)
    print("OK. Verifie visuellement.")


if __name__ == "__main__":
    print("1. Calibrer les coordonnees (sequentiel)")
    print("2. Tester une coordonnee (deplace la souris dessus)")
    choice = input("Choix (1/2) : ").strip()
    if choice == "2":
        key = input("Nom de cle : ").strip()
        tst1(key)
    else:
        cap_all()
