"""Keep zero-press reset records out of per-action diagnostic denominators."""


def action_records(records):
    return [r for r in records if 1 <= r.get("a", 0) <= 7]
