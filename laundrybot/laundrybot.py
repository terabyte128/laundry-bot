from flask import Flask
from flask_migrate import Migrate

from laundrybot.models import db, Machine
from laundrybot.machines import MachineData
from laundrybot.blueprints import api

config = {
    "SQLALCHEMY_DATABASE_URI": "sqlite:///db.sqlite3",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
}


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(**config)

    db.init_app(app)
    Migrate(app, db)

    app.register_blueprint(api.blp, url_prefix="/api")

    # add fixtures for the machines that don't already exist
    @app.before_first_request
    def create_machines():
        with app.app_context():
            for data in MachineData:
                machine_type = data.value
                machine = Machine.query.get(machine_type.id)

                if machine is None:
                    app.logger.info(f"Adding machine {machine_type}")
                    machine = Machine(
                        id=machine_type.id, name=machine_type.name
                    )
                    db.session.add(machine)

            db.session.commit()

    return app
