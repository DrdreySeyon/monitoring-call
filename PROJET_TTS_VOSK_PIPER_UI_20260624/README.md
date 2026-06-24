# PROJET_TTS_VOSK_PIPER_UI_20260624

Projet UX TCU avec integration de la variable `tts` pour pilotage Piper TTS cote Asterisk, lecture des resultats Vosk depuis la base, et affichage d'exploitation TTS dans les onglets.

Ajouts visuels :
- Dashboard : indicateurs appels TTS et TTS detectes.
- Scenarios : badge mode appel `Standard`, `DTMF`, `TTS`, `TTS + DTMF`.
- Historique : filtre par mode, colonnes mode et statut TTS, export CSV enrichi.
- Supervision : synthese `TTS / Piper` basee sur les scenarios et appels charges.
- Planificateur : mode appel et rappel du TTS attendu.
- Resultats Vosk : filtre par mode, TTS attendu et detection via transcription.

Preview globale du projet avec les ajouts TTS / DTMF / Vosk / supervision :

```text
D:\bpce\PROJET_TTS_VOSK_PIPER_UI_20260624\FRONT\preview.html
```

Preview detaillee des 4 modes uniquement :

```text
D:\bpce\PROJET_TTS_VOSK_PIPER_UI_20260624\FRONT\preview-modes-tts.html
```

```text
PROJET_TTS_VOSK_PIPER_UI_20260624
|-- API
|   |-- main.py
|   |-- config.py
|   |-- database.py
|   |-- models.py
|   |-- ari.py
|   |-- ami_listener.py
|   |-- scheduler.py
|   |-- requirements.txt
|   `-- test_backend.py
|-- FRONT
|   |-- index.html
|   `-- assets
|       |-- css
|       `-- js
|-- docs
|   `-- ASTERISK_PIPER_VOSK.md
|-- start_backend.bat
`-- start_front.bat
```

Lancement backend + front :

```powershell
D:\bpce\PROJET_TTS_VOSK_PIPER_UI_20260624\start_backend.bat
```

Puis ouvrir :

```text
http://127.0.0.1:8090/
```

Documentation de l'integration Asterisk/Piper/Vosk :

```text
D:\bpce\PROJET_TTS_VOSK_PIPER_UI_20260624\docs\ASTERISK_PIPER_VOSK.md
```
