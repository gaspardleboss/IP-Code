# Ly-ion — Explication technique complète du fonctionnement

---

## Vue d'ensemble : c'est quoi le système ?

Ly-ion est une borne de location de batteries portables (power banks) pour étudiants.  
La borne contient **24 emplacements**, chacun avec une batterie dedans.  
Un étudiant peut **louer une batterie** de deux façons :
1. En **tapant sa carte RFID étudiante** sur le lecteur de la borne
2. En **scannant le QR code** de la borne avec son téléphone

Le système est composé de **4 grandes parties** qui communiquent entre elles :

```
[ Carte RFID / QR Code ]
         ↓
[ Raspberry Pi ]  ←→  [ Backend cloud ]  ←→  [ App mobile ]
         ↓
[ Base de données locale SQLite ]
```

---

## PARTIE 1 — Le Raspberry Pi (le cerveau physique de la borne)

### Rôle général
Le Raspberry Pi est l'ordinateur embarqué dans la borne. Il fait tourner un programme Python en permanence, 24h/24. Il contrôle tout le matériel physique.

### Les composants matériels qu'il gère

**Le lecteur RFID (RC522)**  
C'est le petit module à la surface de la borne où l'étudiant pose sa carte.  
Il communique avec le Pi via le protocole SPI (bus série rapide).  
Quand une carte est détectée, il renvoie un **UID** (identifiant unique) sous forme hexadécimale, par exemple `"04 89 7B CD 1D"`.  
Le code interroge ce lecteur **toutes les 200 millisecondes** (5 fois par seconde).

**Les LEDs embarquées sur chaque batterie (indication distribuée)**  
Le système ne contient **pas de bandeau LED centralisé** dans la borne. À la place, **chaque batterie est équipée de 5 LEDs embarquées** directement sur sa coque, câblées sur le circuit de gestion interne de la batterie (BMS + microcontrôleur).  
Ces LEDs ont **deux modes de fonctionnement** selon que la batterie est dans la borne ou sortie.

*Mode "Docked" (batterie insérée dans un slot)* — Les LEDs reflètent l'**état du slot** calculé par la Raspberry Pi. L'état est communiqué à la batterie via les **pogo pins magnétiques** qui servent simultanément de contact de charge, de détection de présence, et de canal d'échange d'informations. Les couleurs possibles :
- **Cyan pulsé** → batterie en charge (SoC < 100%)
- **Bleu fixe** → batterie chargée à 100%, disponible à la location
- **Vert fixe** → slot déverrouillé, la batterie est en train d'être retirée
- **Rouge clignotant** → défaut détecté (anomalie de charge ou défectueuse signalée par le serveur)

*Mode "Undocked" (batterie sortie, utilisée par l'étudiant)* — Dès que les pogo pins se déconnectent, le contrôleur interne de la batterie prend le relais de façon autonome. Les LEDs affichent alors :
- **Niveau de charge** (jauge linéaire sur les 5 LEDs) :
  - 5/5 vert → 80-100%
  - 4/5 vert → 60-80%
  - 3/5 jaune → 40-60%
  - 2/5 orange → 20-40%
  - 1/5 rouge clignotant → 0-20%
- **Indicateur de défaut** (écrase la jauge) : 5 LEDs rouges clignotantes si le contrôleur interne détecte une surchauffe, un déséquilibre de cellule ou un courant anormal.

Cette architecture distribue l'affichage à la source (la batterie elle-même), ce qui garantit un retour visuel cohérent **à la fois dans la borne et dans la main de l'étudiant**, sans nécessiter de bus d'éclairage dédié dans le locker.

**Les extenseurs GPIO (MCP23017 via I2C)**  
Le Raspberry Pi n'a pas assez de broches GPIO pour contrôler 24 serrures + 24 capteurs.  
On utilise donc 3 puces MCP23017 connectées en I2C (bus à 2 fils : SDA et SCL).  
Chaque puce ajoute 16 broches configurables :

- **Puce A (adresse 0x20)** : 16 broches en **sortie** → commande les relais des solénoïdes pour les slots 1 à 16
- **Puce B (adresse 0x21)** : 8 broches en **sortie** (solénoïdes 17-24) + 8 broches en **entrée** (détection batterie 17-24)
- **Puce C (adresse 0x22)** : 16 broches en **entrée** → détection de présence de batterie pour les slots 1-16

**Les relais et solénoïdes**  
Chaque emplacement a un relais électromécanique.  
Quand le Raspberry Pi met une broche à **HIGH**, le relais se ferme → le solénoïde reçoit du courant → la serrure s'ouvre.  
Par défaut, tous les solénoïdes sont **verrouillés**. À chaque démarrage du programme, le code appelle `lock_all()` pour s'assurer que tout est fermé.

**Les pogo pins — interface multi-fonction batterie/borne**  
Chaque emplacement est équipé de connecteurs pogo-pins magnétiques qui assurent **trois fonctions simultanément** :

1. **Détection de présence** — quand une batterie est insérée, elle complète un circuit électrique → un optocoupleur génère un signal **HIGH** sur la broche d'entrée du MCP23017 correspondant. Le code lit ces broches **toutes les 500 ms**.
2. **Transfert d'énergie pour la charge** — les mêmes pogo pins transportent le courant de charge depuis le bus 24 V de la borne (via relais dédié + convertisseur DC-DC) vers les cellules de la batterie.
3. **Canal de télémétrie et de commande LED** — les pogo pins véhiculent également les données numériques échangées entre la Raspberry Pi et le microcontrôleur interne de chaque batterie. Dans ce canal transitent :
   - *De la batterie vers le Pi* : niveau de charge (SoC en %), température des cellules, tension, flags de défaut (overcurrent, overtemp, imbalance), compteur de cycles.
   - *Du Pi vers la batterie* : l'état du slot à afficher sur les 5 LEDs (CHARGING / READY / UNLOCKED / FAULT).

Cette fusion de fonctions dans un seul connecteur magnétique simplifie énormément la mécanique du locker (pas de câblage LED dédié, pas de capteur de présence séparé) et garantit la cohérence entre ce qui est affiché sur la batterie et ce que pense le système central.

---

### L'organisation du code embarqué

Le programme démarre dans `main.py` et lance **4 threads en parallèle** :

#### Thread 1 — Boucle de lecture RFID
Interroge le lecteur RC522 toutes les 200 ms.  
Si une carte est détectée, elle appelle `handle_card_scan(uid)`.

**Logique de `handle_card_scan` :**
1. Cherche dans la base locale si cette carte a une **session active** (= batterie déjà louée)
   - Si **oui** → c'est un **retour** : on vérifie que la batterie est bien dans l'emplacement, on ferme la session, l'état du slot passe à CHARGING (les LEDs de la batterie pulsent en cyan)
   - Si **non** → c'est une **demande de location** :
     - On contacte le backend cloud : `POST /api/rent`
     - Si le backend répond : il donne le numéro du slot à ouvrir → le solénoïde s'ouvre, l'état du slot passe à UNLOCKED (LEDs de la batterie vertes)
     - Si le backend est **injoignable** (mode hors ligne) : on vérifie si la carte est dans la table locale `allowed_cards`. Si oui, on choisit le meilleur slot disponible localement, on ouvre, et on met l'événement en file d'attente pour synchroniser plus tard

#### Thread 2 — Boucle de surveillance des slots
Lit toutes les 500 ms les 24 entrées de détection (via les MCP23017).  
Compare l'état actuel avec l'état précédent pour détecter :
- **LOW → HIGH** (batterie insérée) :
  - Si un étudiant avait loué ce slot → c'est un retour, on ferme la session
  - Sinon → une batterie a été posée par la maintenance, on la surveille
- **HIGH → LOW** (batterie retirée) :
  - Si une session est active → retrait autorisé (l'étudiant est parti avec). Les pogo pins se déconnectent, la batterie bascule automatiquement en mode autonome (jauge de charge gérée par son propre microcontrôleur).
  - Sinon → **retrait non autorisé** : on log une alerte, on marque l'emplacement comme défectueux dans la base locale (les LEDs ne sont plus pilotables puisque la batterie est partie)

#### Thread 3 — Boucle de surveillance de la charge
Toutes les 60 secondes, le thread lit la **télémétrie de chaque batterie présente** via les pogo pins :
- Niveau de charge en %
- Température des cellules
- Flags de défaut remontés par le BMS interne

À partir de ces données, le Pi met à jour l'état du slot en base SQLite :
- Charge = 100% et pas de défaut → état **READY** → LEDs de la batterie en bleu fixe
- Charge < 100% et pas de défaut → état **CHARGING** → LEDs de la batterie en cyan pulsé
- Défaut remonté par la batterie ou par le serveur → état **FAULT** → LEDs de la batterie en rouge clignotant

La commande d'affichage correspondante est renvoyée à la batterie via les pogo pins. Cela remplace l'ancienne approche où le Pi pilotait lui-même une bande NeoPixel centralisée.

#### Thread 4 — Boucle de synchronisation cloud
Toutes les 30 secondes :
1. Envoie les événements en file d'attente vers le backend (accumulés pendant une coupure réseau), y compris la télémétrie batterie agrégée
2. Pousse les sessions créées hors ligne
3. Récupère les états à jour des slots (niveaux de charge de référence, flags de défaut côté serveur)
4. Récupère la liste des cartes autorisées (pour le mode hors ligne)
5. Envoie un heartbeat pour dire "la borne est en ligne"

---

## PARTIE 2 — La base de données locale (SQLite)

Le Pi a une base SQLite stockée localement (sur la carte SD).  
Elle sert de **mémoire locale** quand le réseau est coupé et de source de vérité pour l'état physique de la borne.

**5 tables principales :**

**`slots`** — état actuel de chaque emplacement  
Contient : slot_id (1-24), battery_uid (quelle batterie est dedans), is_locked, slot_state (CHARGING / READY / UNLOCKED / FAULT), charge_level, battery_temperature, is_defective  
→ Mise à jour à chaque événement physique, à chaque lecture de télémétrie batterie, et à chaque sync cloud

**`sessions`** — historique des locations  
Contient : session_id (UUID), card_uid (qui a loué), slot_id, start_time, end_time, is_synced  
→ `end_time = NULL` signifie que la location est en cours  
→ `is_synced = 0` signifie que le backend n'est pas encore au courant

**`allowed_cards`** — liste blanche des cartes pour le mode hors ligne  
Contient : card_uid, student_id, display_name, is_active  
→ Mise à jour à chaque synchronisation depuis le cloud

**`slot_logs`** — journal d'audit complet  
Chaque insertion, retrait, déverrouillage, anomalie, et lecture de télémétrie batterie est enregistré avec un timestamp

**`sync_queue`** — file d'attente pour la synchronisation différée  
Quand le réseau est coupé, les événements sont mis ici avec endpoint + payload JSON.  
Le thread 4 les rejoue dès que le réseau revient.

---

## PARTIE 3 — Le backend cloud (Flask + PostgreSQL)

### Rôle général
Le backend est un serveur web en **Python Flask** avec une base de données **PostgreSQL**.  
Il est déployé dans un conteneur Docker avec Nginx devant lui (pour le HTTPS).  
Il centralise toutes les données, valide les cartes, gère les sessions et sert l'application mobile.

### Sécurité
- Les bornes s'authentifient avec une **clé API secrète** dans le header HTTP `X-Station-Key`
- Les étudiants s'authentifient avec des **JWT** (tokens JSON signés, valables 1h avec refresh à 30 jours)
- Aucune donnée sensible n'est hardcodée dans le code : tout passe par des **variables d'environnement**

### Les modèles de données PostgreSQL

**`Student`** — compte étudiant  
student_number (adaptable à n'importe quelle université), name, email, password_hash, card_uid, deposit_balance, is_active

**`Battery`** — chaque batterie physique  
battery_uid (RFID UID de la batterie elle-même), charge_level, cycle_count, health_status (GOOD/DEGRADED/DEFECTIVE), last_temperature, last_telemetry_timestamp

**`Station`** — une borne physique  
id (ex: "station-001"), location_name, qr_code_token (UUID unique pour le QR code), is_online, last_heartbeat

**`Slot`** — emplacement dans une borne (1 à 24)  
Lié à une station et à une batterie, is_locked, slot_state (CHARGING / READY / UNLOCKED / FAULT), is_defective

**`Session`** — location en cours ou terminée  
Lié à un étudiant, un slot, une batterie. Status : ACTIVE / RETURNED / OVERDUE / LOST  
deposit_held (montant retenu), deposit_returned

**`SlotLog`** — audit trail avec champ JSONB pour les détails (y compris les échantillons de télémétrie batterie)

### Les endpoints principaux

**Authentification :**
- `POST /api/auth/card` → la borne envoie un UID, le backend vérifie si la carte est enregistrée et renvoie un JWT
- `POST /api/auth/login` → l'app mobile envoie numéro étudiant + mot de passe, reçoit un JWT
- `POST /api/auth/register-card` → l'étudiant lie sa carte RFID à son compte (une seule fois)

**Location :**
- `POST /api/rent` → la borne (ou l'app) demande une location. Le backend :
  1. Valide la carte / le JWT
  2. Vérifie qu'il n'y a pas de session déjà active
  3. Sélectionne le slot avec la batterie la plus chargée et en bon état (`MAX(charge_level) WHERE health='GOOD'`)
  4. Crée la session, retient le dépôt
  5. Répond avec le numéro du slot
- `POST /api/return` → ferme la session, libère le dépôt
- `GET /api/slots/<station_id>` → retourne l'état des 24 slots (utilisé par l'app et la sync)

**Synchronisation :**
- `POST /api/sync/push` → la borne envoie ses événements accumulés hors ligne + les échantillons de télémétrie batterie. Le backend répond avec la liste des cartes autorisées et les états à jour des slots
- `POST /api/sync/heartbeat` → ping toutes les 30s pour signaler que la borne est en ligne

**Administration :**
- `POST /api/admin/students/import` → upload d'un fichier CSV (student_number, name, email) pour importer les étudiants en masse
- `POST /api/admin/students/sync-external` → reçoit un tableau JSON d'un système externe (SIS universitaire) pour synchroniser automatiquement les comptes
- `PUT /api/admin/slots/<id>/flag-defective` → marquer un emplacement comme défectueux (le Pi enverra la commande FAULT à la batterie concernée via les pogo pins → LEDs rouges clignotantes)
- `GET /api/admin/reports/usage` → statistiques d'utilisation

### Adaptabilité à n'importe quelle université
Le backend n'a **aucune donnée étudiante hardcodée**.  
Les universités fournissent leur liste d'étudiants via :
- Un CSV uploadé par un admin
- Un push JSON automatique depuis leur système d'information
Le nom de l'école, le montant du dépôt, la durée max de location sont tous des **variables d'environnement**.

---

## PARTIE 4 — L'application mobile (React Native + Expo)

### Rôle général
L'app est développée avec **React Native et Expo**, ce qui permet de compiler pour iOS et Android depuis un seul code source.  
Elle permet aux étudiants de louer une batterie via QR code, sans avoir besoin de leur carte RFID.

### Flux principal (location par QR code)

1. **L'étudiant ouvre l'app** et voit l'onglet "Scanner"
2. Il **scanne le QR code** sur la borne avec la caméra
3. Le QR code contient l'URL `lyion://station/<token>` — c'est un deep link
4. Si l'étudiant n'est **pas connecté** : message "Connectez-vous à votre compte étudiant pour continuer" → redirigé vers LoginScreen
5. Si connecté → **StationScreen** : l'app appelle `GET /api/slots/<station_id>` et affiche une grille de 24 cases colorées (chaque case reprend le slot_state : CHARGING / READY / UNLOCKED / FAULT)
6. L'étudiant **tape sur un slot bleu** (READY = disponible) → **RentConfirmScreen**
7. Il confirme → l'app appelle `POST /api/rent` avec son JWT
8. Le backend répond avec le numéro du slot → la borne reçoit l'ordre de déverrouiller via la synchronisation
9. L'étudiant retire la batterie (les LEDs de la batterie passent en mode autonome : jauge de charge)

**Rafraîchissement automatique** : StationScreen interroge le backend toutes les **5 secondes** pour mettre à jour les couleurs des slots en temps réel.

### Structure des écrans

**LoginScreen** — Connexion  
Champs : numéro étudiant + mot de passe  
Appel : `POST /api/auth/login`  
Stockage du JWT dans `expo-secure-store` (chiffré, équivalent du Keychain iOS / Keystore Android)

**QRScanScreen** — Scan QR  
Utilise `expo-barcode-scanner`  
Valide le format du QR code, vérifie la connexion, redirige vers StationScreen

**StationScreen** — Grille des 24 slots  
Affiche chaque slot avec sa couleur (reprise du slot_state de la batterie) et son niveau de charge  
Slot bleu (READY) = tappable  
Rafraîchissement auto toutes les 5 secondes

**RentConfirmScreen** — Confirmation  
Affiche le numéro du slot, le niveau de charge, le montant du dépôt  
Bouton "Confirmer et déverrouiller"

**ActiveRentalScreen** — Location en cours  
Affiche les infos de l'étudiant et la batterie louée  
Bouton de retour (à compléter avec le scan QR de retour)

**ProfileScreen** — Profil  
Infos du compte, solde de dépôt, état de la carte RFID, déconnexion

### SlotGrid et SlotCard (composants)
La grille est un composant réutilisable.  
Chaque case (`SlotCard`) connaît son `slot_state` et affiche la couleur correspondante (cyan = CHARGING, bleu = READY, vert = UNLOCKED, rouge = FAULT).  
Si `slot_state = "READY"`, la case est cliquable. Sinon, elle affiche une alerte.

### Gestion des tokens JWT
- Le token d'accès dure **1 heure**
- Le token de refresh dure **30 jours**
- Tous deux sont stockés dans `expo-secure-store` (jamais en clair)
- Le module `auth.js` gère le renouvellement automatique

---

## Comment les 4 parties communiquent — récapitulatif des flux

### Flux 1 : Location par carte RFID (sans internet)
```
Étudiant tape sa carte
    → Thread RFID lit l'UID
    → Cherche l'UID dans allowed_cards (SQLite local)
    → Choisit le meilleur slot disponible
    → Solénoïde s'ouvre (GPIO → MCP23017 → relais)
    → Pi envoie l'état UNLOCKED à la batterie via pogo pins → LEDs vertes
    → Session enregistrée localement (SQLite)
    → Événement mis en sync_queue
    → Étudiant retire la batterie → pogo pins se déconnectent → LEDs passent en mode jauge autonome
    → Quand le réseau revient → sync_queue envoyée au backend
```

### Flux 2 : Location par carte RFID (avec internet)
```
Étudiant tape sa carte
    → Thread RFID lit l'UID
    → POST /api/rent {card_uid, station_id} → Backend
    → Backend valide la carte, choisit le meilleur slot, crée la session
    → Répond {slot: 5, session_id: "uuid", battery_charge: 92}
    → RPi ouvre le slot 5
    → Pi envoie l'état UNLOCKED à la batterie 5 via pogo pins → LEDs vertes
    → Étudiant retire → pogo pins se déconnectent → batterie bascule en mode jauge
    → Session sauvegardée en local
```

### Flux 3 : Retour de batterie
```
Étudiant replace la batterie dans un slot libre
    → Pogo pins se reconnectent → détection HIGH sur MCP23017
    → Thread de surveillance détecte une insertion
    → L'étudiant re-tape sa carte (ou le système croise automatiquement via le battery_uid lu en télémétrie)
    → Trouve une session active pour cet UID en SQLite
    → Session fermée (end_time = maintenant)
    → Pi envoie l'état CHARGING à la batterie via pogo pins → LEDs cyan pulsées
    → Télémétrie de charge reprise à l'intervalle de 60s (Thread 3)
    → POST /api/return envoyé au backend (ou mis en queue si hors ligne)
```

### Flux 4 : Location par QR code (application mobile)
```
Étudiant scanne QR code
    → App décode lyion://station/<token>
    → GET /api/slots/<station_id> → grille affichée
    → Étudiant tape un slot bleu (READY)
    → POST /api/rent {station_id} avec JWT
    → Backend crée la session, répond {slot: 3}
    → App affiche "L'emplacement 3 s'ouvre"
    → Au prochain heartbeat (30s max), le RPi récupère l'ordre et ouvre le slot 3
    → Pi envoie l'état UNLOCKED à la batterie 3 via pogo pins → LEDs vertes
    → Étudiant retire → batterie en mode jauge autonome
```

---

## Déploiement — comment ça s'installe

### Backend (serveur cloud)
```bash
# 1. Remplir les variables d'environnement
cp lyion_backend/.env.example lyion_backend/.env

# 2. Lancer avec Docker Compose (Flask + PostgreSQL + Nginx)
docker-compose up -d
```
Docker lance 3 conteneurs :
- **PostgreSQL** : stocke toutes les données (étudiants, sessions, batteries)
- **Flask/Gunicorn** : le serveur Python avec 4 workers parallèles
- **Nginx** : reverse proxy, termine le HTTPS, transmet à Flask

### Raspberry Pi
```bash
# Sur le Pi :
bash setup_rpi.sh     # Active SPI/I2C, installe les libs Python, crée le service systemd
nano .env             # Renseigner l'URL du backend et la clé API
sudo systemctl start lyion_embedded
```
Le service **systemd** redémarre automatiquement le programme si il plante.

### Application mobile
```bash
cd lyion_app
# Changer BACKEND_URL dans services/api.js
npx expo build:android    # ou :ios
```

---

## Points clés à retenir pour l'oral

1. **4 threads en parallèle sur le Pi** : RFID, détection physique, surveillance charge/télémétrie, synchronisation cloud — chacun indépendant, chacun résistant aux erreurs

2. **Mode hors ligne complet** : le Pi peut fonctionner sans internet grâce à la base SQLite locale et la table `allowed_cards`. Les événements sont synchronisés quand le réseau revient via la `sync_queue`

3. **Pogo pins magnétiques multi-fonction** : un seul connecteur assure simultanément la détection de présence, le transfert d'énergie pour la charge, et la communication bidirectionnelle (télémétrie batterie + commande LED). Cela réduit drastiquement la complexité mécanique et électrique du locker.

4. **Affichage LED distribué à la source** : chaque batterie porte ses propres 5 LEDs, pilotées en mode docké par le Pi via pogo pins, et en mode autonome (hors locker) par le microcontrôleur interne de la batterie. Le retour visuel est donc cohérent à la fois dans la borne (état du slot) et dans la main de l'étudiant (jauge de charge + défauts).

5. **Sécurité à plusieurs niveaux** : clé API pour les bornes, JWT pour les étudiants, tokens chiffrés sur le téléphone, aucune donnée sensible dans le code

6. **Adaptabilité universitaire** : import CSV ou push JSON pour importer les étudiants, variables d'environnement pour tout ce qui est institution-spécifique

7. **Solénoïde = verrou physique** : le relais est actif HIGH (sécurité fail-safe) — une coupure de courant laisse tout verrouillé
