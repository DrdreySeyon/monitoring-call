#!/usr/bin/env python3

from panoramisk import Manager
import pymysql
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

AMI_HOST = "127.0.0.1"
AMI_PORT = 5039
AMI_USER = "ami_user"
AMI_PASS = "85_ioU@5w7"

MYSQL_HOST = "asterisk-bdd-biatk.hom.mycloud.intrabpce.fr"
MYSQL_USER = "biatkadmin"
MYSQL_PASS = "AgNyhYhqTO5WtZMJBp_9"
MYSQL_DB   = "asterisk"
MYSQL_PORT = 15100


def mysql_connect():

    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        port=MYSQL_PORT,
        autocommit=True
    )


manager = Manager(
    host=AMI_HOST,
    port=AMI_PORT,
    username=AMI_USER,
    secret=AMI_PASS
)


@manager.register_event('Hangup')
async def handle_hangup(manager, event):

    context = event.get('Context')

    uniqueid = event.get('Uniqueid')
    cause = event.get('Cause')
    cause_txt = event.get('Cause-txt')
    tech_cause = event.get('TechCause')

    logging.info(
        "Call ended : %s cause=%s (%s) ERROR:%s",
        uniqueid,
        cause,
        cause_txt,
        tech_cause
    )

    try:

        conn = mysql_connect()

        with conn.cursor() as cur:

            cur.execute("""
                UPDATE calls
                SET
                    hangup_cause=%s,
                    hangup_cause_detail=%s,
                    sip_error_code=%s
                WHERE channel_id=%s
            """, (
                cause,
                cause_txt,
                tech_cause,
                uniqueid
            ))

        conn.close()

    except Exception as e:

        logging.error(
            "Database error : %s",
            str(e)
        )


async def main():

    await manager.connect()

    logging.info("AMI listener started")

    while True:
        await asyncio.sleep(3600)


asyncio.run(main())

