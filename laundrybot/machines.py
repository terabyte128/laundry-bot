import attr
import enum

from flask import current_app

from laundrybot.models import db, Load


@attr.s(frozen=True)
class MachineType:
    id = attr.ib(type=int)
    name = attr.ib(type=str)
    cycle_threshold = attr.ib(type=float)


class MachineData(enum.Enum):
    WASHER = MachineType(id=1, name="washer", cycle_threshold=7)
    DRYER = MachineType(id=2, name="dryer", cycle_threshold=4)


def passed_threshold(prev: float, current: float, threshold: float, pos=True):
    """Whether the difference between prev and current passes
    threshold, either in the positive or negative direction."""
    if pos:
        return prev < threshold and current >= threshold
    else:
        return prev >= threshold and current < threshold


def mark_finished_and_collected(db, loads: dict[Load], timestamp):
    for load in loads:
        # assume any uncollected load was collected
        if load and not load.collected:
            current_app.logger.info(
                f"load from {load.start_time} assumed collected"
            )

            # this shouldn't ever happen, but if that last load hasn't been
            # marked finished, then do that
            end_time = load.end_time or timestamp

            load.end_time = end_time
            load.collected = True

            db.session.add(load)


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

    if (
        # has been idle for > TIMEOUT
        last_load_this_machine
        and current_reading < machine.cycle_threshold
        and (
            current_ts - last_load_this_machine.last_change_time
        ).total_seconds()
        > current_app.config["IDLE_TIMEOUT"]
    ):
        # assume that it is done: mark last load finished but not collected
        if last_load_this_machine and not last_load_this_machine.end_time:
            last_load_this_machine.end_time = current_ts

            current_app.logger.info(
                f"load from {last_load_this_machine.start_time} is complete"
            )

            # TODO bug the person whose load just finished
            db.session.add(last_load_this_machine)

    # started using power
    elif passed_threshold(
        previous_reading, current_reading, machine.cycle_threshold, True
    ):
        current_app.logger.info(f"{machine.name} started using power")

        # there is an existing, unfinished load
        if last_load_this_machine and not last_load_this_machine.end_time:
            # just bump the change time
            last_load_this_machine.last_change_time = current_ts
            db.session.add(last_load_this_machine)

        # there is either no load, or one that has finished
        # so this is an entirely new one
        else:
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

            mark_finished_and_collected(db, last_loads, current_ts)

            # start a new load
            current_app.logger.info(f"starting new load in {machine.name}")
            new_load = Load(
                machine_id=machine.id,
                start_time=current_ts,
                last_change_time=current_ts,
            )

            # mark new load as same person as old load
            if last_washer_load and last_washer_load.roommate:
                current_app.logger.info(
                    f"assigning to {last_washer_load.roommate.name}"
                )
                new_load.roommate = last_washer_load.roommate

            db.session.add(new_load)

    # stopped using power
    elif passed_threshold(
        previous_reading, current_reading, machine.cycle_threshold, False
    ):
        current_app.logger.info(f"{machine.name} stopped using power")

        # just bump the change time
        if last_load_this_machine:
            last_load_this_machine.last_change_time = current_ts
            db.session.add(last_load_this_machine)

    db.session.commit()  # send it!!
