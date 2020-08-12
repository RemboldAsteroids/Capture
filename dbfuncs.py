import sqlite3 as lite
from datetime import datetime as dt


def add_session(id_: str):
    with lite.connect("Logs/Observations.db") as db:
        cur = db.cursor()
        cur.execute("INSERT INTO sessions(id) VALUES (?);", (id_,))
        db.commit()


def update_session(id_: str, update_dict: dict):
    with lite.connect("Logs/Observations.db") as db:
        cur = db.cursor()
        for key in update_dict:
            cmd = 'UPDATE sessions SET "{}"="{}" WHERE id="{}";'.format(
                key, update_dict[key], id_
            )
            cur.execute(cmd)
        db.commit()


def get_last_session_id():
    with lite.connect("Logs/Observations.db") as db:
        cur = db.cursor()
        cur.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1;")
        id_ = cur.fetchall()
        if len(id_)>0:
            output = id_[0][0]
        else:
            output = None
    return output


def get_entry(id_: str, column: str):
    with lite.connect(
        "Logs/Observations.db", detect_types=lite.PARSE_DECLTYPES | lite.PARSE_COLNAMES
    ) as db:
        cur = db.cursor()
        cur.execute('SELECT "{}" FROM sessions WHERE id="{}";'.format(column, id_))
        entry = cur.fetchall()[0][0]
    return entry
