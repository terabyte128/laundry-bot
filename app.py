import arrow
import re
import random
import sqlite3

from flask import request, Flask, g, render_template, flash, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = "somethingreallysecret"

DATABASE = "db.sqlite3"
MACHINES = {}


def local_time():
    return arrow.utcnow().to("America/Los_Angeles")


def local_from_ts(ts):
    return arrow.get(ts, tzinfo="America/Los_Angeles")


def get_db() -> sqlite3.Connection:
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.before_first_request
def create_tables():
    db = get_db()
    c = db.cursor()

    c.execute(
        """
        create table if not exists machine (
            id integer primary key,
            name string not null,
            last_reading real,
            updated_at integer
        );
        """
    )

    c.execute(
        """
        create table if not exists load (
            id integer primary key,
            machine_id integer not null,
            owner text,
            cycle_number integer default 1,
            start_time integer not null,
            end_time integer,
            collected not null default false,
            foreign key (machine_id) references machine(id) on delete cascade
        );
        """
    )
    db.commit()

    c.execute("select name from machine")
    existing = map(lambda x: x[0], c.fetchall())

    for machine in ["washer", "dryer"]:
        if not machine in existing:
            # add anything that's not there. assume 0 amps and last updated a long time ago
            c.execute(
                "insert into machine (name, last_reading, updated_at) values (?,?,?)",
                (machine, 0, 0),
            )

    db.commit()

    # stash the name -> id mapping
    c.execute("select id, name from machine")
    for row in c.fetchall():
        MACHINES[row[1]] = row[0]


def latest_load(c):
    c.execute(
        """
        select load.id, load.start_time, load.end_time, load.collected from load 
        join machine on load.machine_id = machine.id 
        where machine.name = 'dryer' 
        order by start_time desc 
        limit 1
        """
    )
    return c.fetchone()


def update_dryer(previous_reading, previous_ts, current_reading, current_ts):
    db = get_db()
    c = db.cursor()

    old_load = latest_load(c)

    # someone just started the dryer
    if previous_reading < 4 and current_reading >= 4:
        app.logger.info("Dryer is starting")
        # if there's an uncollected load in progress, assume it was collected
        if old_load and not old_load[3]:
            app.logger.info(
                f"load from {local_from_ts(old_load[1])} is assumed collected"
            )

            # this shouldn't ever happen, but if the load is not marked as finished, then do that
            end_time = old_load[2] or current_ts.int_timestamp

            c.execute(
                "update load set end_time = ?, collected = ? where id = ?",
                (end_time, True, old_load[0]),
            )

        # create a new load
        c.execute(
            "insert into load (machine_id, start_time) values (?, ?)",
            (MACHINES["dryer"], local_time().int_timestamp),
        )

    # the dryer just finished
    elif previous_reading > 4 and current_reading <= 4:
        # if there's a load in progress, end it but do NOT set collected
        if old_load and not fetched[2]:
            app.logger.info(f"load from {local_from_ts(old_load[1])} is complete")

            c.execute(
                "update load set end_time = ? where id = ?",
                (current_ts.int_timestamp, old_load[0]),
            )

            # TODO bug the person who's stuff is done

    db.commit()


def update_washer(previous_reading, previous_ts, current_reading, current_ts):
    db = get_db()
    c = db.cursor()

    old_load = latest_load(c)

    # TODO
    # if previous_reading < 7 and current_reading >= 7:


def update_load(machine, previous_reading, previous_ts, current_reading, current_ts):
    if machine == "dryer":
        update_dryer(previous_reading, previous_ts, current_reading, current_ts)


@app.route("/api/update", methods=("POST",))
def update_readings():
    db = get_db()
    c = db.cursor()

    readings = {
        "washer": request.form.get("washer"),
        "dryer": request.form.get("dryer"),
    }

    errors = {}

    for machine, value in readings.items():
        if not value:
            errors[machine] = "value was not provided"
        else:
            try:
                readings[machine] = float(value)
            except ValueError:
                errors[machine] = "value is not a number"

    if len(errors) > 0:
        return jsonify(errors), 200

    ts = local_time()

    c.execute("select name, last_reading, updated_at from machine")

    previous = {v[0]: (v[1], local_from_ts(v[2])) for v in c.fetchall()}

    for machine, value in readings.items():
        c.execute(
            "update machine set last_reading = ?, updated_at = ? where name = ?",
            (value, ts.int_timestamp, machine),
        )

    db.commit()

    for machine, value in readings.items():
        update_load(machine, *previous[machine], value, ts)

    return jsonify(readings), 201
