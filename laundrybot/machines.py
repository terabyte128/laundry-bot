import attr
import enum

from flask import current_app

from laundrybot.models import db, Load
from laundrybot.util import local_from_ts, local_time


@attr.s(frozen=True)
class MachineType:
    id = attr.ib(type=int)
    name = attr.ib(type=str)
    cycle_threshold = attr.ib(type=float)
    num_cycles = attr.ib(type=int)


class MachineData(enum.Enum):
    WASHER = MachineType(id=1, name="washer", cycle_threshold=7, num_cycles=7)
    DRYER = MachineType(id=2, name="dryer", cycle_threshold=4, num_cycles=1)


def update_machine(
    machine: MachineType,
    previous_reading: float,
    previous_ts,
    current_reading: float,
    current_ts,
):
    last_load_this_machine = (
        Load.query.filter_by(machine_id=machine.id)
        .order_by(Load.start_time.desc())
        .first()
    )

    # we passed a threshold but haven't reached the total number of cycles
    # transition to a new cycle if there's a load; don't end the load yet
    if (
        last_load_this_machine
        and last_load_this_machine.cycle_number < machine.num_cycles
        and (
            (
                previous_reading < machine.cycle_threshold
                and current_reading >= machine.cycle_threshold
            )
            or (
                previous_reading >= machine.cycle_threshold
                and current_reading < machine.cycle_threshold
            )
        )
    ):
        current_app.logger.info(
            f"transitioning {last_load_this_machine.start_time} to cycle "
            f"{last_load_this_machine.cycle_number + 1}"
        )
        last_load_this_machine.cycle_number += 1
        db.session.add(last_load_this_machine)

    # someone just started the machine
    elif (
        previous_reading < machine.cycle_threshold
        and current_reading >= machine.cycle_threshold
    ):
        current_app.logger.info(f"{machine.name} is starting")

        last_loads = [last_load_this_machine]

        # specifically for dryer: also check the last washer load
        last_washer_load = None

        if machine == MachineData.DRYER.value:
            last_washer_load = (
                Load.query.filter_by(machine_id=MachineData.WASHER.value.id)
                .order_by(Load.start_time.desc())
                .first()
            )

            if last_washer_load and not last_washer_load.collected:
                last_loads.append(last_washer_load)

        for load in last_loads:
            # assume any uncollected load was collected
            if load and not load.collected:
                current_app.logger.info(
                    f"load from {load.start_time} assumed collected"
                )

                # this shouldn't ever happen, but if that last load hasn't been
                # marked finished, then do that
                end_time = load.end_time or current_ts.datetime

                load.end_time = end_time
                load.collected = True

                db.session.add(load)

        # start a new load
        # TODO mark the new load as the same person who finished last_washer_load
        new_load = Load(machine_id=machine.id, start_time=current_ts.datetime)
        db.session.add(new_load)

    # the machine just finished
    elif (
        previous_reading >= machine.cycle_threshold
        and current_reading < machine.cycle_threshold
    ):
        # mark the last load finished but not collected
        if last_load_this_machine and not last_load_this_machine.end_time:
            last_load_this_machine.end_time = current_ts.datetime

            current_app.logger.info(
                f"load from {local_from_ts(last_load_this_machine.start_time)} is complete"
            )

            # TODO bug the person whose load just finished
            db.session.add(last_load_this_machine)

    db.session.commit()  # send it!!
