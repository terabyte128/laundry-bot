from flask import Blueprint, request, jsonify, current_app

from laundrybot.models import db, Machine, Roommate, Load
from laundrybot.util import local_time
from laundrybot.machines import MachineData, MachineType, update_machine
from laundrybot.responses import build_response, build_full_response

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
    name = request.form.get("name")
    roommate = Roommate.query.filter_by(name=name).first()

    if roommate is None:
        current_app.logger.warning(f"Could not find roommate with name {name}")
        return build_response(error=f"Roommate {name} not found"), 404

    last_load = Load.query.order_by(Load.start_time.desc()).first()

    if last_load and not last_load.collected:
        if last_load.roommate != roommate:
            # link the most recently started load to the person who pushed the button
            current_app.logger.info(
                f"linking load from {last_load.start_time} to {roommate.name}"
            )
            last_load.roommate = roommate

        else:
            # mark the load as collected
            current_app.logger.info(
                f"marking load by {roommate.name} from {last_load.start_time} as collected"
            )
            last_load.collected = True

        db.session.add(last_load)

    else:
        # assume they started a new washer load, and link it to them
        # cycle number will be 0 because it hasn't actually started yet
        # this will be incremented once it starts
        load = Load(
            machine_id=MachineData.WASHER.value.id,
            roommate=roommate,
            cycle_number=0,
            start_time=local_time().datetime,
        )
        current_app.logger.info(
            f"creating new washer load {load.start_time} for {roommate.name}"
        )

        db.session.add(load)

    db.session.commit()

    return build_full_response(), 200
