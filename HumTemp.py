import Adafruit_DHT as dht
import time
from datetime import datetime as dt
import sqlite3 as sql

import shared


def log_weather(delay):
    while True:
        db = sql.connect("Logs/Conditions.db")
        cur = db.cursor()
        try:
            h, t = dht.read_retry(dht.DHT22, 24)
            shared.TEMP = t * 9 / 5 + 32
            shared.HUMID = h
            cur.execute(
                """INSERT INTO conditions(UTC, Local, Temp, Humidity) VALUES(?,?,?,?)""",
                (dt.utcnow(), dt.now(), t * 9 / 5 + 32, h),
            )
        except:
            shared.TEMP = "NA"
            shared.HUMID = "NA"
            cur.execute(
                """INSERT INTO conditions(UTC, Local, Temp, Humidity) VALUES(?,?,?,?)""",
                (dt.utcnow(), dt.now(), None, None),
            )
        db.commit()
        db.close()
        time.sleep(delay)


if __name__ == "__main__":
    log_weather(10)
