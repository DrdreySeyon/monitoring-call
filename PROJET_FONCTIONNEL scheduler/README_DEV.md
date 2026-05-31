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

## Scheduler

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
