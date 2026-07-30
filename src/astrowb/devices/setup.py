"""Building the observatory configuration (the JSON file `--observatory` reads) without editing it by hand:
ASCOM Alpaca devices are found on the network (UDP discovery, then each server's list of devices)."""

import json
from pathlib import Path

KINDS = ("mount", "camera", "filterwheel", "focuser", "dome", "monitor", "conditions", "rotator", "panel")
ALPACA_ONLY = ("rotator", "panel")
ALPACA_TYPES = {  # Alpaca DeviceType -> our device kind
    "telescope": "mount",
    "camera": "camera",
    "filterwheel": "filterwheel",
    "focuser": "focuser",
    "dome": "dome",
    "safetymonitor": "monitor",
    "observingconditions": "conditions",
    "rotator": "rotator",
    "covercalibrator": "panel",
}
RULE_DEFAULTS = {"min_alt": 15.0, "sun_max_alt": -6.0, "max_humidity": 90.0, "max_wind": 12.0}


def discover(timeout=2, search=None, devices_of=None):
    """[{kind, name, address, number}] of every Alpaca device answering on the local network."""
    if search is None or devices_of is None:
        from alpaca import discovery, management

        search = search or (lambda: discovery.search_ipv4(numquery=2, timeout=timeout))
        devices_of = devices_of or management.configureddevices
    found = []
    for address in search():
        try:
            listed = devices_of(address)
        except Exception:  # a server that answers discovery but not the management API: skip it
            continue
        for d in listed:
            kind = ALPACA_TYPES.get(str(d.get("DeviceType", "")).lower())
            if kind:
                found.append(
                    {"kind": kind, "name": d.get("DeviceName", ""), "address": address, "number": d["DeviceNumber"]}
                )
    return found


def make_config(site, devices, rules=None, phd2=None, remote=False, token=None, focus=None):
    """devices: [{kind, protocol: "alpaca" | "indi", address, number (Alpaca) or name (INDI)}];
    focus: {"offsets": {filter: steps}, "temp_coeff": steps per degree, "temp_step": degrees}."""
    out = {"site": dict(site), "devices": {}, "rules": RULE_DEFAULTS | dict(rules or {})}
    for d in devices:
        if d["kind"] in out["devices"]:
            raise ValueError(f"two devices for {d['kind']}")
        if d["protocol"] == "alpaca":
            out["devices"][d["kind"]] = {"alpaca": d["address"], "number": int(d.get("number") or 0)}
        else:
            out["devices"][d["kind"]] = {"indi": d["address"], "device": d["name"]}
    if focus and (focus.get("offsets") or focus.get("temp_coeff")):
        out["focus"] = dict(focus)
    if phd2:
        host, _, port = phd2.rpartition(":")
        out["phd2"] = {"host": host or "127.0.0.1", "port": int(port or 4400)}
    out["listen"] = ("0.0.0.0" if remote else "127.0.0.1") + ":11112"  # remote: other computers may connect
    if token:
        out["token"] = token
    return out


def problems(config):
    """What would stop the observatory or make it unsafe, in plain words (empty: fine)."""
    out = []
    site = config.get("site", {})
    if config.get("listen", "").startswith("0.0.0.0") and not config.get("tls"):
        out.append("other computers may connect without encryption: turn on HTTPS unless the network is private")
    if not -90 <= float(site.get("lat", 999)) <= 90 or not -180 <= float(site.get("lon", 999)) <= 360:
        out.append("the site's latitude / longitude are missing or out of range")
    devices = config.get("devices", {})
    if "mount" in devices and not ({"monitor", "conditions"} & set(devices)):
        out.append("no safety monitor or weather sensor: the supervisor cannot see rain or clouds")
    for kind, spec in devices.items():
        if not (spec.get("alpaca") or spec.get("indi")):
            out.append(f"{kind}: no address")
        if "indi" in spec and not spec.get("device"):
            out.append(f"{kind}: no INDI device name")
        if "indi" in spec and kind in ALPACA_ONLY:
            out.append(f"{kind}: only ASCOM Alpaca is supported for this device")
    return out


def save(config, path):
    path = Path(path)
    if path.exists() and "token" not in config:  # keep the token: remote clients already use it
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("token"):
            config = config | {"token": old["token"]}
    path.write_text(json.dumps(config, indent=1), encoding="utf-8")
    return path
