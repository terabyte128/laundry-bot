from flask import Blueprint, request, jsonify

from laundrybot.models import db, Machine
from laundrybot.util import local_time
from laundrybot.machines import MachineData, MachineType, update_machine
from laundrybot.responses import build_full_response

blp = Blueprint("api", __name__)


@blp.route("/update", methods=("POST",))
def update_readings():
    readings: dict[MachineType, any] = {
        MachineData.WASHER.value: request.form.get("washer"),
        MachineData.DRYER.value: request.form.get("dryer"),
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

    old_values = {}

    for machine_type, value in readings.items():
        # stash old values
        machine = Machine.query.get(machine_type.id)
        last_reading = machine.last_reading
        updated_at = machine.updated_at

        old_values[machine_type] = (
            last_reading,
            updated_at,
        )

        # then update them
        machine.last_reading = value
        machine.updated_at = ts.datetime

        db.session.add(machine)

    # commit before doing more work
    db.session.commit()

    # trigger machine updates for new readings
    for machine_type, value in readings.items():
        update_machine(machine_type, *old_values[machine_type], value, ts)

    return build_full_response(), 200


@blp.route("/button", methods=("POST",))
def push_button():
    person = request.form.get("person")
    # TODO logic here
