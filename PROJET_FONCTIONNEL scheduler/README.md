#


# monitoring-call
monitoring-call
Pour rajouter le mot cle à l'appel aller dans main.py perfomcall
@app.post(f"{settings.api_prefix}/scenarios/{{scenario_id}}/call")
async def call_from_scenario(scenario_id: int, db: Session = Depends(get_db)):
    db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")

    if not db_scenario.active:
        raise HTTPException(status_code=400, detail="Le scénario est inactif")

    try:
        call_row, ari_response = perform_call(
            db=db,
            caller=db_scenario.caller,
            callee=db_scenario.callee,
            trunk=db_scenario.trunk,
            call_time_s=db_scenario.call_time_s,
            dtmf=db_scenario.dtmf,
            time_s_before_dtmf=db_scenario.time_s_before_dtmf,
            time_ms_between_dtmf=db_scenario.time_ms_between_dtmf,
            scenario_id=db_scenario.id,
            scenario_name=db_scenario.name,
            scenario_keyword=db_scenario.keyword,
            scenario_category=db_scenario.category
        )

        return {
            "scenario": {
                "id": db_scenario.id,
                "name": db_scenario.name,
                "keyword": db_scenario.keyword,
                "category": db_scenario.category
            },
            "call": {
                "id": call_row.id,
                "channel_id": call_row.channel_id,
                "status": call_row.status,
                "caller": call_row.caller,


logger.info(f"ARI URL = {settings.ari_url}/channels")
logger.info(f"ARI endpoint = {endpoint}")
logger.info(f"ARI params = {params}")
logger.info(f"ARI payload = {payload}")



e problème vient sûrement de l’endpoint/trunk.

Dans ton ari.py, tu construis :

endpoint = f"PJSIP/{callee}@{trunk}"

Mais avec PJSIP, Asterisk attend souvent plutôt :

endpoint = f"PJSIP/{trunk}/sip:{callee}@IP_DU_TRUNK"

ou parfois :

endpoint = f"PJSIP/{trunk}/{callee}"

À tester directement dans le terminal Asterisk :

curl -u ari_user:sA7LuZ_t34 -X POST "http://sldcfrbiatk1076:8088/ari/channels?endpoint=PJSIP/TON_NUMERO@TRUNK_SBC_SFR_VEGA&extension=TON_NUMERO&context=recording&priority=1&callerId=TON_CALLER"

Si ça fait 404, teste :

curl -u ari_user:sA7LuZ_t34 -X POST "http://sldcfrbiatk1076:8088/ari/channels?endpoint=PJSIP/TRUNK_SBC_SFR_VEGA/sip:TON_NUMERO@100.76.143.56:5060&extension=TON_NUMERO&context=recording&priority=1&callerId=TON_CALLER"

D’après ton écran, pour TRUNK_SBC_SFR_VEGA, l’adresse est :

100.76.143.56:5060

Si le 2e test marche, alors dans ari.py, il faut remplacer :

endpoint = f"PJSIP/{callee}@{trunk}"

par :

trunk_hosts = {
    "TRUNK_SBC_SFR_VEGA": "100.76.143.56:5060",
    "TRUNK_SBC_SFR_SIRIUS": "100.76.143.48:5060",
    "TRUNK_SBC_OBS_VEGA": "100.76.143.57:5060",
    "TRUNK_SBC_OBS_SIRIUS": "100.76.143.49:5060",
    "TRUNK_SBC_ODIGO_VEGA": "100.76.143.58:5060",
    "TRUNK_SBC_ODIGO_SIRIUS": "100.76.143.50:5060",
}

endpoint = f"PJSIP/{trunk}/sip:{callee}@{trunk_hosts[trunk]}"



logger.info(f"ARI URL = {settings.ari_url}/channels")
logger.info(f"ARI endpoint = {endpoint}")
logger.info(f"ARI params = {params}")
logger.info(f"ARI payload = {payload}")



grep -R "asterisk/ari" -n /srv/api/asterisk
grep -R "ari_url" -n /srv/api/asterisk
grep -R "ARI_URL" -n /srv/api/asterisk
cat /srv/api/asterisk/.env




mysql -h asterisk-bdd-biatk.mycloud.intrabpce.fr \
-u biatkadmin \
-P 15100 \
-p

database_url = "mysql+pymysql://biatkadmin:MOTDEPASSE@asterisk-bdd-biatk.mycloud.intrabpce.fr:15000/NOM_BDD"



journalctl --user -u fastapi_app.service -n 100 --no-pager

from config import Settings
s = Settings()
print(s.database_url)




Alors le problème vient probablement d’autre chose dans l’URL SQLAlchemy.

Sur ta capture, je vois :

mysql+pymysql://biatkadmin:uhHLBa5LMJv2YLf0Bp_9@asterisk-bdd-biatk.mycloud.intrabpce.fr:15000/asterisk

Cette syntaxe semble correcte.

MAIS l’erreur :

Can't connect to MySQL server
[Errno 111] Connection refused

signifie maintenant que :

* l’URL est parsée correctement ✅
* SQLAlchemy fonctionne ✅
* pymysql fonctionne ✅
* mais FastAPI n’arrive toujours pas à joindre MySQL.

⸻

Pourtant ton test mysql CLI marche

Tu as montré que :

mysql -h ... -P 15000

fonctionne.

Donc le problème est probablement :

* utilisateur différent
* mot de passe différent
* environnement différent
* ou résolution DNS différente dans Python.

⸻

Vérification IMMÉDIATE

Teste exactement depuis le venv Python utilisé par FastAPI.

Fais :

source /srv/api/asterisk/env/bin/activate

Puis :

python3

Puis :

import pymysql
conn = pymysql.connect(
    host="asterisk-bdd-biatk.mycloud.intrabpce.fr",
    port=15000,
    user="biatkadmin",
    password="TON_MDP",
    database="asterisk"
)
print("OK")

⸻

Résultats possibles

Si ça affiche :

OK

Alors :

* MySQL fonctionne
* problème dans FastAPI/config/env

⸻

Si ça échoue encore

Alors :

* mauvais mot de passe
* mauvaise DB
* firewall
* host différent

⸻

Autre point important

Tu utilises :

/asterisk

comme nom de DB.

Tu dois vérifier qu’elle existe réellement :

Dans MySQL :

SHOW DATABASES;

et confirme que :

* asterisk existe exactement
* sans majuscule différente

⸻

Vérifie aussi la résolution DNS Python

Dans Python :

import socket
socket.gethostbyname("asterisk-bdd-biatk.mycloud.intrabpce.fr")

Si ça échoue → problème DNS côté Python/service.

⸻

Très probable maintenant

Je pense que :

* le nom de DB est faux
    OU
* le service FastAPI n’utilise pas la même config que celle modifiée.

Car l’erreur SQLAlchemy actuelle n’est plus une erreur de parsing, mais une vraie erreur réseau/connexion.











Ton journalctl confirme encore exactement la même erreur :

Can't connect to MySQL server
[Errno 111] Connection refused

Donc maintenant il faut arrêter de regarder FastAPI :
le problème est purement la connexion SQLAlchemy/MySQL utilisée PAR LE SERVICE.

Et vu que :

* le client mysql -h ... -P 15000 fonctionne ✅
* mais FastAPI échoue ❌

alors il y a 3 causes très probables restantes.

⸻

1. Tu n’utilises pas le même mot de passe

Le plus probable.

Le client MySQL fonctionne car tu tapes peut-être le bon mot de passe manuellement.

Mais dans config.py, il peut y avoir :

* une faute
* un caractère oublié
* un caractère spécial non échappé
* un espace caché

⸻

Test définitif

Fais EXACTEMENT ça dans le même venv que FastAPI :

source /srv/api/asterisk/env/bin/activate
python3

Puis colle :

import pymysql
conn = pymysql.connect(
    host="asterisk-bdd-biatk.mycloud.intrabpce.fr",
    port=15000,
    user="biatkadmin",
    password="LE_MÊME_MDP_QUE_CONFIGPY",
    database="asterisk"
)
print("MYSQL OK")

⸻

Résultat attendu

Si ça marche :

MYSQL OK

Alors :

* la config FastAPI n’est pas celle utilisée
    OU
* une variable .env écrase config.py

⸻

2. TON .env écrase la config

Sur ta capture je vois :

class Config:
    env_file = ".env"

Donc même si tu modifies config.py,
Pydantic peut charger les valeurs du .env.

Et le .env peut encore contenir :

15100

⸻

Vérifie IMMÉDIATEMENT

cat /srv/api/asterisk/.env

Cherche :

* DATABASE_URL
* MYSQL_PORT
* 15100

⸻

Très probable

Je pense que ton .env contient encore :

15100

et écrase ton config.py.

⸻

3. Vérifie ce que FastAPI lit réellement

Dans Python :

source /srv/api/asterisk/env/bin/activate
python3

Puis :

from config import settings
print(settings.database_url)

C’est LA commande clé.

Tu verras :

* soit 15000
* soit 15100

⸻

Si tu vois encore 15100

Alors le .env écrase tout.

Corrige le .env.

⸻

Ensuite

systemctl --user restart fastapi_app.service

Puis :

systemctl --user status fastapi_app.service

Tu devrais enfin voir :

active (running)
