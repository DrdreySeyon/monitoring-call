# Espace de dev - Monitoring d'Appels TCU

Ce dossier est l'espace de dev de reference :

`D:\bpce\PROJET_FONCTIONNEL`

## Structure frontend

Le front utilise la structure compatible prod :

- `FRONT/index.html`
- `FRONT/assets/css/styles.css`
- `FRONT/assets/js/*.js`

## Demarrage rapide

API :

```powershell
.\start_api.bat
```

Front :

```powershell
.\start_front.bat
```

Puis ouvrir :

`http://127.0.0.1:8080`

## Configuration

La configuration API est lue depuis `API\.env`.

Au premier lancement, `start_api.bat` cree automatiquement `API\.env` depuis `API\.env.example` si le fichier n'existe pas.

## URLs utiles

- Front : `http://127.0.0.1:8080`
- Health API : `http://127.0.0.1:8000/api/health`
- Health detaille : `http://127.0.0.1:8000/api/health/detailed`
- Swagger : `http://127.0.0.1:8000/api/docs`

## Logs

Les logs API sont ecrits dans :

`API\logs\app.log`

Le fichier tourne automatiquement selon les parametres :

- `LOG_MAX_BYTES`
- `LOG_BACKUP_COUNT`

## Planificateur

Chaque scenario peut maintenant porter sa propre planification :

- `once`
- `daily`
- `weekly`
- `monthly`

Endpoints utiles :

- `GET /api/scheduler/status`
- `GET /api/scheduler/jobs`
- `POST /api/scheduler/sync`
- `POST /api/scenarios/{id}/run-now`
- `POST /api/scenarios/{id}/schedule/sync`

La base existante est enrichie automatiquement au demarrage avec les colonnes de planification si elles n'existent pas encore.

## Resultats Vosk

Vosk est traite en amont par Asterisk/MixMonitor ou par un traitement externe.
L'application ne recupere plus les fichiers audio et ne lance plus de transcription.
Elle lit uniquement les resultats presents directement dans la table `calls`.

Colonnes attendues dans `calls` :

- `channel_id`
- `vosk_status`
- `transcription`
- `created_at`

Les valeurs UAT attendues pour `calls.vosk_status` sont :

- `OK`
- `KO`

L'historique d'appels affiche directement le champ `calls.vosk_status`.
Les anciennes valeurs de lab `valid` et `invalid` restent seulement supportees pour les tests locaux.

## Hangup cause

La table UAT `calls` contient `hangup_cause`.
L'application l'utilise comme source de verite pour afficher le resultat reel :

- `16` : appel decroche / fin normale, affiche comme reussi.
- autre code : appel echoue, avec la cause lisible dans la colonne Erreur de l'historique.

La table `cdr` sert a completer la duree via `uniqueid`, mais elle ne porte pas le `hangup_cause` dans le schema UAT fourni.

Endpoints utiles :

- `GET /api/vosk/results`
- `GET /api/calls/history`

## Configuration UAT

Un template est disponible dans :

`API\.env.uat.example`

Il reprend les connecteurs fournis :

- `DATABASE_URL=mysql+pymysql://{{BDD_USER}}:{{BDD_PASSWORD}}@{{BDD_DNS}}:15100/asterisk`
- `ARI_URL=http://{{IP_ASTERISK}}:8088/ari`
- `ARI_USER={{ARI_USER}}`
- `ARI_PASSWORD={{ARI_PASSWORD}}`
