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