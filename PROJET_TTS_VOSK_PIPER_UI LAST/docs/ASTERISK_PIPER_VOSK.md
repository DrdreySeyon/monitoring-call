# Integration Asterisk, Piper TTS et Vosk

## Principe retenu

L'application ne lance pas Piper ni Vosk localement sur la VM API.

Le role de l'application est de piloter l'appel via ARI et de transmettre les variables necessaires au dialplan Asterisk.

Le serveur Asterisk reste responsable de :

- generer le message audio avec Piper,
- convertir le fichier audio avec SoX,
- lire le fichier audio dans l'appel,
- enregistrer l'appel,
- faire la detection Vosk,
- ecrire le resultat dans la base.

## Variable ajoutee par l'application

La variable `tts` est ajoutee au scenario et envoyee dans le body ARI :

```json
{
  "variables": {
    "call_time_s": "30",
    "ring_timeout_s": "60",
    "keyword": "bonjour, aide",
    "dtmf": "#12",
    "time_s_before_dtmf": "4",
    "time_ms_between_dtmf": "3000",
    "tts": "Bonjour, merci de confirmer votre identite"
  }
}
```

Si `tts` est vide, la variable n'est pas envoyee.

## Mode retenu dans cette version

La version reste volontairement simple :

- un seul message `tts` complet,
- une seule sequence `dtmf`,
- un delai `time_s_before_dtmf`,
- un intervalle `time_ms_between_dtmf` entre les DTMF.

Exemple :

```text
tts = Bonjour, je souhaite joindre le service support
dtmf = 123
time_s_before_dtmf = 4
time_ms_between_dtmf = 3000
```

L'API ne decoupe pas le TTS en plusieurs morceaux. Elle envoie le texte complet a Asterisk dans la variable `tts`.

## Prerequis cote serveur Asterisk

Installer et verifier :

- `piper`
- `sox`
- modele Piper francais, par exemple `fr_FR-tom-medium`
- modele Vosk francais
- droits d'ecriture dans les repertoires audio Asterisk

Repertoires attendus d'apres les informations fournies :

```text
/srv/asterisk/piper-tts/
/srv/asterisk/var/lib/asterisk/sounds/piper-tts/
```

Fichiers modele Piper a placer dans `/srv/asterisk/piper-tts/` :

```text
fr_FR-tom-medium.onnx
fr_FR-tom-medium.onnx.json
MODEL_CARD
```

## Integration dialplan

Le dialplan Asterisk doit exploiter la variable `tts`.

Logique attendue :

1. verifier que `${tts}` n'est pas vide,
2. generer un fichier WAV avec Piper,
3. convertir le WAV en ALAW 8 kHz avec SoX,
4. lire le fichier avec `Playback`,
5. continuer l'appel,
6. laisser Vosk traiter l'enregistrement,
7. enregistrer `vosk_status`, `transcription` et les champs metier dans la table `calls`.

Dans cette version, le dialplan exploite uniquement la variable `tts` globale.

## Colonnes ajoutees cote application

La version ajoute automatiquement la colonne `tts` si elle manque :

- `scenarios.tts`
- `calls.tts`

## Points de controle

Dans les logs API, verifier que le scenario est lance avec succes.

Dans les logs Asterisk, verifier la presence de :

```text
Set(TEXT=${tts})
System(... piper ...)
System(... sox ...)
Playback(...)
Vosk status : OK|KO
```

Dans la base, verifier :

```sql
SELECT id, scenario_name, tts, vosk_status, transcription
FROM calls
ORDER BY created_at DESC
LIMIT 10;
```

## Conclusion

Oui, l'integration est possible meme si Vosk et Piper doivent rester sur le serveur Asterisk/ARI/AMI.

La bonne frontiere technique est :

- API : orchestration, scenarios, planification, payload ARI, affichage.
- Asterisk : appel, TTS, enregistrement, Vosk.
- Base : point de synchronisation entre Asterisk et l'application.
