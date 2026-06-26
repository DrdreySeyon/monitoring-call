# PROJET_TTS_VOSK_PIPER_20260624

Projet UX TCU avec integration de la variable `tts` pour pilotage Piper TTS cote Asterisk, et lecture des resultats Vosk depuis la base.

```text
PROJET_TTS_VOSK_PIPER_20260624
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
D:\bpce\PROJET_TTS_VOSK_PIPER_20260624\start_backend.bat
```

Puis ouvrir :

```text
http://127.0.0.1:8090/
```

Documentation de l'integration Asterisk/Piper/Vosk :

```text
D:\bpce\PROJET_TTS_VOSK_PIPER_20260624\docs\ASTERISK_PIPER_VOSK.md
```
