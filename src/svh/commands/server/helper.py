import ipaddress
import re


def isHost(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        pass

    domain_pattern = re.compile(r"^(?!-)(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$")
    if domain_pattern.match(value):
        return True

    return False


def invalid_config(field) -> bool:
    choice = input(
        f"Invalid {field} detected. Would you like to use the defualt? [y/n] "
    )
    if choice.lower() in ("y", "yes"):
        return True
    else:
        return False
