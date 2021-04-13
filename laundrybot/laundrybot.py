import os

from flask import Flask, current_app
from flask_migrate import Migrate

from laundrybot.models import db, Machine, Roommate
from laundrybot.machines import MachineData
from laundrybot.blueprints import api

config = {
    "SQLALCHEMY_DATABASE_URI": "sqlite:///db.sqlite3",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "IDLE_TIMEOUT": float(os.environ.get("IDLE_TIMEOUT", 300)),
}


def create_fixtures():
    for data in MachineData:
        machine_type = data.value
        machine = Machine.query.get(machine_type.id)

        if machine is None:
            current_app.logger.info(f"Adding machine {machine_type}")
            machine = Machine(id=machine_type.id, name=machine_type.name)
            db.session.add(machine)

    for name in ["Sam", "Claire", "Luke", "Kris"]:
        roommate = Roommate.query.filter_by(name=name).first()

        if roommate is None:
            roommate = Roommate(name=name)
            current_app.logger.info(f"Adding roommate {roommate}")
            db.session.add(roommate)

    db.session.commit()


def create_app(**kwargs):
    app = Flask(__name__)
    config.update(kwargs)
    app.config.from_mapping(**config)

    db.init_app(app)
    Migrate(app, db)

    app.register_blueprint(api.blp, url_prefix="/api")

    # add fixtures for the machines that don't already exist
    @app.before_request
    def f():
        create_fixtures()

    return app
