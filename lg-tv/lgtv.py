#!/usr/bin/env python3
"""Find and control an LG webOS TV on the local network.

  python lgtv.py discover            find LG TVs (SSDP) and probe the default IP
  python lgtv.py pair                pair with the TV (accept the prompt on screen)
  python lgtv.py apps                list installed apps / launch points
  python lgtv.py launch <app_id>     launch an app
  python lgtv.py toast "hello"       show a notification on the TV
  python lgtv.py settings <category> dump system settings (find ad/privacy keys)
  python lgtv.py set <category> key=value [key=value ...]
"""
import asyncio
import json
import socket
import sys
from pathlib import Path

import aiowebostv

TV_IP = "192.168.29.179"  # LG 50UA82006LA
KEY_FILE = Path(__file__).with_name(".lgtv-key")


def discover():
    msg = "\r\n".join([
        "M-SEARCH * HTTP/1.1", "HOST: 239.255.255.250:1900", 'MAN: "ssdp:discover"',
        "MX: 3", "ST: urn:schemas-upnp-org:device:MediaRenderer:1", "", ""]).encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(4)
    s.sendto(msg, ("239.255.255.250", 1900))
    seen = {}
    try:
        while True:
            data, addr = s.recvfrom(4096)
            text = data.decode(errors="ignore")
            if "webos" in text.lower() or "lg" in text.lower():
                seen[addr[0]] = text.split("\r\n")[0]
    except socket.timeout:
        pass
    for ip in seen:
        print("SSDP: LG/webOS device at", ip)
    if not seen:
        print("SSDP: nothing found (multicast may be blocked), trying direct probe")
    for port in (3000, 3001):
        with socket.socket() as p:
            p.settimeout(2)
            ok = p.connect_ex((TV_IP, port)) == 0
        print(f"{TV_IP}:{port} {'open' if ok else 'closed'}")


async def with_tv(fn):
    key = KEY_FILE.read_text().strip() if KEY_FILE.exists() else None
    tv = aiowebostv.WebOsClient(TV_IP, client_key=key, connect_timeout=30)
    await tv.connect()  # first run: accept the prompt on the TV
    if tv.client_key and tv.client_key != key:
        KEY_FILE.write_text(tv.client_key)
        print("paired, key saved to", KEY_FILE)
    try:
        await fn(tv)
    finally:
        await tv.disconnect()


async def main(argv):
    cmd, args = argv[0], argv[1:]
    if cmd == "pair":
        return await with_tv(lambda tv: asyncio.sleep(0))
    if cmd == "apps":
        async def f(tv):
            for a in (await tv.get_apps_all()).values():
                print(f"{a['id']:45} {a.get('title')}")
        return await with_tv(f)
    if cmd == "launch":
        return await with_tv(lambda tv: tv.launch_app(args[0]))
    if cmd == "toast":
        return await with_tv(lambda tv: tv.send_message(args[0]))
    if cmd == "settings":
        async def f(tv):
            r = await tv.request("com.webos.settingsservice/getSystemSettings",
                                 {"category": args[0]})
            print(json.dumps(r.get("settings", r), indent=2))
        return await with_tv(f)
    if cmd == "set":
        settings = dict(kv.split("=", 1) for kv in args[1:])
        async def f(tv):
            print(await tv.request("com.webos.settingsservice/setSystemSettings",
                                   {"category": args[0], "settings": settings}))
        return await with_tv(f)
    print(__doc__)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    elif sys.argv[1] == "discover":
        discover()
    else:
        asyncio.run(main(sys.argv[1:]))
