def invalid_config(field):
    choice = input(
        f"Invalid {field} detected. Would you like to use the defualt? [y/n] "
    )
    if choice.lower() in ("y", "yes"):
        return True
    else:
        return False
