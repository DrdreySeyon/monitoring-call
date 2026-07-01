# MOS / ToS - Qualite d'appel

Cette version calcule un MOS estime a partir des metriques RTP deja presentes dans la table `cdr`.

## Source des donnees

Le backend lit les champs suivants dans `cdr`, via `cdr.uniqueid` rattache au `channel_id` de l'appel :

- `rxjitter`
- `txjitter`
- `rlp`
- `rtt`
- `rxcount`
- `txcount`
- `rxmes`
- `txmes`

## Mapping applicatif

| Champ CDR | Usage applicatif |
|---|---|
| `rxjitter` | jitter recu |
| `txjitter` | jitter envoye |
| `rlp` | paquets perdus |
| `rtt` | latence aller-retour |
| `rxcount` | paquets recus |
| `txcount` | paquets envoyes |
| `rxmes` | mesure RTP recue, conservee pour diagnostic |
| `txmes` | mesure RTP envoyee, conservee pour diagnostic |

## Calcul MOS

L'application calcule :

- `rtp_jitter_ms` : moyenne de `rxjitter` et `txjitter`
- `rtp_packet_loss_pct` : estimation en pourcentage depuis `rlp` et `rxcount`
- `rtp_rtt_ms` : valeur `rtt`
- `mos_score` : MOS estime
- `mos_label` : libelle lisible
- `qos_status` : `ok`, `warning` ou `ko`

Si aucune metrique RTP n'est disponible dans `cdr`, l'application affiche `MOS N/A`.

## Interpretation

- MOS >= 4.3 : Excellent
- MOS >= 4.0 : Bon
- MOS >= 3.6 : Acceptable
- MOS >= 3.1 : Mauvais
- MOS < 3.1 : Tres mauvais

## ToS / DSCP

Le ToS/DSCP n'est pas calcule dans cette version car les champs visibles dans la table `cdr` fournie ne contiennent pas de colonne ToS, DSCP ou classe de service IP exploitable.

Pour l'ajouter proprement plus tard, il faudra une source fiable, par exemple :

- colonne CDR dediee au DSCP/ToS ;
- mesure issue du SBC ;
- export RTP/QoS reseau ;
- enrichissement AMI/ARI si disponible dans votre contexte.

## Ecrans impactes

- Dashboard : MOS moyen et appels avec QoS degradee.
- Historique : colonne Qualite.
- Detail appel : section Qualite voix.
- Timeline : etape Qualite voix.
- Export CSV local : colonnes MOS et RTP.

## Limite actuelle

Le MOS reste une estimation applicative. Pour valider finement la formule, il faut comparer quelques appels reels avec les valeurs exactes de `rxjitter`, `txjitter`, `rlp`, `rtt`, `rxcount` et `txcount` en base.
