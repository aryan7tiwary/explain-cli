SIGNAL_NUMBER_TO_NAME = {
    1: "SIGHUP",
    2: "SIGINT",
    3: "SIGQUIT",
    6: "SIGABRT",
    9: "SIGKILL",
    11: "SIGSEGV",
    13: "SIGPIPE",
    14: "SIGALRM",
    15: "SIGTERM",
}

SIGNAL_NAME_TO_DESC = {
    "SIGHUP": "Hangup detected on controlling terminal or death of controlling process",
    "SIGINT": "Interrupt from keyboard (Ctrl+C)",
    "SIGQUIT": "Quit from keyboard (core dump)",
    "SIGABRT": "Abort signal from abort(3)",
    "SIGKILL": "Kill signal (cannot be caught or ignored)",
    "SIGSEGV": "Invalid memory reference",
    "SIGPIPE": "Broken pipe: write to pipe with no readers",
    "SIGALRM": "Timer signal from alarm(2)",
    "SIGTERM": "Termination signal",
}


def normalize_signal(sig: str):
    name = sig.upper()
    if not name.startswith("SIG"):
        name = "SIG" + name
    return name


def explain_signal_flag(arg: str, next_arg: str | None = None) -> str | None:
    # Forms: -9, -SIGKILL, --signal SIGKILL (we handle -s in CLI due to generic parsing)
    if arg.startswith('-') and len(arg) > 1:
        payload = arg[1:]
        # Numeric like -9
        if payload.isdigit():
            num = int(payload)
            name = SIGNAL_NUMBER_TO_NAME.get(num)
            if name:
                desc = SIGNAL_NAME_TO_DESC.get(name, "")
                return f"  {arg}: send {name} ({desc or 'signal'})"
        # Name like -KILL or -SIGKILL
        name = normalize_signal(payload)
        if name in SIGNAL_NAME_TO_DESC:
            desc = SIGNAL_NAME_TO_DESC[name]
            return f"  {arg}: send {name} ({desc})"
    # -s SIGKILL style handled by caller with next_arg
    if arg == '-s' and next_arg:
        val = next_arg
        if val.isdigit():
            num = int(val)
            name = SIGNAL_NUMBER_TO_NAME.get(num)
            if name:
                desc = SIGNAL_NAME_TO_DESC.get(name, "")
                return f"  -s {val}: send {name} ({desc or 'signal'})"
        name = normalize_signal(val)
        if name in SIGNAL_NAME_TO_DESC:
            desc = SIGNAL_NAME_TO_DESC[name]
            return f"  -s {val}: send {name} ({desc})"
    return None


