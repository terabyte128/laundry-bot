import arrow


def local_time():
    return arrow.utcnow().to("America/Los_Angeles")


def local_from_ts(ts):
    return arrow.get(ts, tzinfo="America/Los_Angeles")
