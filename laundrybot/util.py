import arrow
from laundrybot.models import Load, Machine


def local_time():
    return arrow.utcnow().to("America/Los_Angeles")


def local_from_ts(ts):
    return arrow.get(ts, tzinfo="America/Los_Angeles")


def build_response(pairs: dict[str, any]):
    return "\n".join([f"{key}={value}" for key, value in pairs.items()])
