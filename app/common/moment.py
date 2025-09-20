import pendulum


def moment(datetime_string: str = None, timezone_string: str = "UTC") -> pendulum.DateTime :
    if datetime_string:
        date_object = pendulum.parse(datetime_string).in_tz(timezone_string)
    else:
        date_object = pendulum.now(tz=timezone_string)
    
    return date_object