# Orange Farm AI pour GTA V (FiveM)

Orange Farm AI est un bot autonome de récolte et de logistique conçu pour les serveurs GTA V Roleplay sur FiveM (spécifiquement optimisé pour UNITY RP V2). Le bot utilise la vision par ordinateur et une machine à états pour naviguer de manière autonome, interagir avec l'environnement et gérer l'inventaire.

## 🚀 Fonctionnalités Principales

- **Détection Visuelle Avancée** : Utilise OpenCV pour isoler les faisceaux lumineux des ressources (oranges/tabac) et la carrosserie des véhicules (camion rose) via des masques HSV dynamiques.
- **Adaptation Jour/Nuit** : Le système de vision ajuste automatiquement la sensibilité de détection (saturation et luminosité) en fonction de l'éclairage ambiant du jeu pour ne jamais perdre sa cible de nuit.
- **Reconnaissance de Texte (OCR)** : Intégration de Tesseract OCR pour lire en temps réel les notifications de l'interface (HUD), comme les indications d'interaction ou les messages "Inventaire Plein".
- **Navigation Intelligente** : Contrôleur de mouvement autonome avec gestion des rotations (Shift+S+D / Shift+D), gestion de la vitesse (sprint vs marche d'approche) et évitement des pertes de cibles (anti-overshoot).
- **Machine à États Robuste** : Gestion fluide des cycles de récolte via des états définis (`SCANNING`, `MOVING_TO_TARGET`, `WAITING`, `SEARCHING`, `GOING_TO_TRUCK`, `TRANSFERRING`).
- **Gestion de l'Inventaire (NUI)** : Routine complète pour vider automatiquement le sac dans le coffre d'un véhicule désigné lorsque l'inventaire est plein, permettant un farming AFK de longue durée.

## 📁 Architecture du Projet

Le projet est divisé en plusieurs modules clés pour faciliter la maintenance :

- `run_bot.py` : Point d'entrée principal. Gère l'initialisation, les arguments de ligne de commande et la boucle principale.
- `ai_state_machine.py` : Le cerveau du bot. Gère les transitions entre la recherche, la navigation, l'attente, et le transfert d'inventaire.
- `vision_system.py` : Le système visuel. Capture l'écran, applique les filtres HSV, gère la détection de blobs, l'analyse OCR et la détection Jour/Nuit.
- `movement_controller.py` : S'occupe d'envoyer les inputs clavier virtuels au jeu via l'API Windows (`ctypes`, `SendInput`, `PostMessageW`), garantissant des mouvements précis sans conflit avec la souris.
- `orange_farm_ai.py` / Configurations : Fichiers de configuration, logs, et structures de données partagées.

## ⚙️ Prérequis

- **Python 3.8+**
- **Bibliothèques Python** : `opencv-python`, `numpy`, `pytesseract`, `pywin32`
- **Tesseract OCR** : Doit être installé sur la machine (chemin par défaut configuré vers `C:\Program Files\Tesseract-OCR\tesseract.exe`).
- **Jeu** : GTA V avec le client FiveM fonctionnant en mode fenêtré ou plein écran fenêtré.

## 🛠️ Utilisation

Lancez le bot depuis l'invite de commande. Différents modes sont disponibles via des arguments.

**Mode Collecte + Transfert au Camion (Tabac / Truck Pink) :**
```cmd
python run_bot.py --tabacrose
```

### Contrôles (Hotkeys)
- **F8** : Afficher les statistiques (taux de récolte, temps écoulé, succès).
- **F9** : Mettre le bot en Pause / Reprendre.
- **F10** : Arrêter complètement le script.

## 📝 Notes Techniques et Comportement
- **Arrivée au Camion** : Le bot évalue dynamiquement sa proximité avec le camion en mesurant la taille de la boîte englobante (bbox_h). Il ralentit (micro-steps) avant de s'arrêter net pour éviter de dépasser le véhicule.
- **Inputs Clavier** : L'utilisation de `PostMessageW` permet d'envoyer les frappes au processus FiveM de manière fiable sans "voler" le focus absolu de Windows, bien que le jeu doive rester visible à l'écran pour la vision par ordinateur.
