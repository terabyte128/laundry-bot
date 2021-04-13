import json
import datetime

from laundrybot.models import Load, Machine
from laundrybot.machines import MachineData


def build_response(**kwargs):
    return (
        "\n".join(
            [f"{key}={json.dumps(value)}" for key, value in kwargs.items()]
        )
        + "\n"
    )


def build_full_response():
    now = datetime.datetime.now()

    washer = Machine.query.get(MachineData.WASHER.value.id)
    dryer = Machine.query.get(MachineData.DRYER.value.id)

    washer_load = washer.loads.order_by(Load.start_time.desc()).first() or Load(
        end_time=now,
        collected=True,
        last_change_time=now,
    )
    dryer_load = dryer.loads.order_by(Load.start_time.desc()).first() or Load(
        end_time=now,
        collected=True,
        last_change_time=now,
    )

    resp = {
        "washer": washer.last_reading,
        "washer_running": washer_load.end_time is None,
        "washer_sec_since_change": (
            now - washer_load.last_change_time
        ).total_seconds(),
        "washer_user": washer_load.roommate.name
        if washer_load.roommate and not washer_load.collected
        else None,
        "washer_collected": washer_load.collected,
        "dryer": dryer.last_reading,
        "dryer_running": dryer_load.end_time is None,
        "dryer_last_change_time": (
            now - dryer_load.last_change_time
        ).total_seconds(),
        "dryer_user": dryer_load.roommate.name
        if dryer_load.roommate and not dryer_load.collected
        else None,
        "dryer_collected": dryer_load.collected,
    }

    return build_response(**resp)
