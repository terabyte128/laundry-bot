import json
import datetime

from laundrybot.models import Load, Machine
from laundrybot.machines import MachineData


def build_response(**kwargs):
    return "\n".join(
        [f"{key}={json.dumps(value)}" for key, value in kwargs.items()]
    )


def build_full_response():

    washer = Machine.query.get(MachineData.WASHER.value.id)
    dryer = Machine.query.get(MachineData.DRYER.value.id)

    washer_load = washer.loads.order_by(Load.start_time.desc()).first() or Load(
        collected=True,
    )
    dryer_load = dryer.loads.order_by(Load.start_time.desc()).first() or Load(
        collected=True,
    )

    resp = {
        "washer": washer.last_reading,
        "washer_running": washer_load.end_time is None,
        "washer_cycle": washer_load.cycle_number,
        "washer_user": washer_load.roommate.name
        if washer_load.roommate and not washer_load.collected
        else None,
        "washer_collected": washer_load.collected,
        "dryer": dryer.last_reading,
        "dryer_running": dryer_load.end_time is None,
        "dryer_cycle": dryer_load.cycle_number,
        "dryer_user": dryer_load.roommate.name
        if dryer_load.roommate and not dryer_load.collected
        else None,
        "dryer_collected": dryer_load.collected,
    }

    return build_response(**resp)
