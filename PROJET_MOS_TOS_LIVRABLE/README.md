# PROJET_MOS_TOS_LIVRABLE

Livrable propre de l'application Monitoring d'Appels TCU avec les dernieres modifications qualite voix.

## Contenu

- `API/` : backend FastAPI.
- `FRONT/` : frontend applicatif principal.
- `docs/MOS_TOS_QUALITE_APPEL.md` : documentation du calcul MOS et du statut ToS/DSCP.
- `start_backend.bat` : demarrage local backend + frontend servi par l'API.

Les previews, caches, bases locales, logs et anciens fichiers de documentation non necessaires ne sont pas inclus.

## Qualite d'appel

Le backend lit les metriques RTP disponibles dans la table `cdr` :

- `rxjitter`
- `txjitter`
- `rlp`
- `rtt`
- `rxcount`
- `txcount`
- `rxmes`
- `txmes`

L'application expose ensuite :

- `mos_score`
- `mos_label`
- `qos_status`
- `rtp_jitter_ms`
- `rtp_packet_loss_pct`
- `rtp_rtt_ms`
- details RTP RX/TX

Le ToS/DSCP n'est pas calcule dans cette version car aucun champ ToS/DSCP exploitable n'est visible dans la table `cdr` fournie. Le livrable reste donc strictement base sur les donnees reelles disponibles.

## Lancement local

Depuis ce dossier :

```powershell
.\start_backend.bat
```

Puis ouvrir :

```text
http://127.0.0.1:8090/
```

## Configuration

Les fichiers d'exemple sont dans `API/` :

- `.env.example`
- `.env.uat.example`

Les secrets doivent rester remplaces par des variables ou placeholders avant deploiement.
