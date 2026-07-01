# PROJET_TTS_VOSK_PIPER_UI_20260624

Projet UX TCU avec integration de la variable `tts` pour pilotage Piper TTS cote Asterisk, lecture des resultats Vosk depuis la base, et affichage d'exploitation TTS dans les onglets.

Ajouts visuels :
- Dashboard : indicateurs appels TTS et TTS detectes.
- Scenarios : badge mode appel `Standard`, `DTMF`, `TTS`, `TTS + DTMF`.
- Historique : filtre par mode, colonnes mode et statut TTS, export CSV enrichi.
- Supervision : synthese `TTS / Piper` basee sur les scenarios et appels charges.
- Planificateur : mode appel et rappel du TTS attendu.
- Resultats Vosk : filtre par mode, TTS attendu et detection via transcription.
- Rafraichissement : bouton manuel, badge de derniere mise a jour, auto-refresh 30s / 1 min / 5 min.
- Import scenarios : creation en masse par CSV ou JSON depuis l'onglet Scenarios.

Colonnes CSV supportees pour l'import :

```text
name;keyword;category;caller;callee;trunk;call_time_s;ring_timeout_s;dtmf;time_s_before_dtmf;time_ms_between_dtmf;tts;frequency;schedule_date;active
```

Exemple :

```text
Controle TTS DTMF;dossier;SAV;+33123456789;+33752049226;TRUNK_SBC_SFR;30;60;123;4;3000;Bonjour, je souhaite joindre le service support;interval_30m;2026-06-27T09:30;true
```

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
