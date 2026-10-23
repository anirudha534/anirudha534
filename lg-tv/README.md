# LG 50UA82006LA toolkit (TV at 192.168.29.179)

Run everything from a computer on the **same Wi‑Fi/LAN** as the TV.

## 1. Remove ads (do in this order)

1. **On the TV** (no tools needed):
   - Settings → General → System → Additional Settings → Home Settings → **Home Promotion: Off**
   - Same menu: **Live Plus: Off**
   - Settings → General → Support/Privacy → **User Agreements**: untick Viewing Information, Interest-Based & Cross Device Advertising
   - Settings → General → Support/Privacy → **Limit AdTracking: On**, and **Reset Advertising ID**
   (menu names vary slightly by webOS version.)
2. **Network-level block** (the strong fix):
   - Pi-hole / AdGuard Home: add `blocklist/lg-ads.txt`.
   - dnsmasq/OpenWrt: copy `blocklist/lg-ads.dnsmasq.conf` into `/etc/dnsmasq.d/`.
   - Point your router's DHCP DNS at that server, and block outbound UDP/TCP 53 from the TV
     except to it (LG TVs sometimes hardcode 8.8.8.8).
   - Some home-screen ads are served from the same hosts as content; if an app breaks, remove the
     matching domain from the list.

## 2. Control / inspect the TV

    pip install -r requirements.txt
    python lgtv.py discover
    python lgtv.py pair        # accept the prompt on the TV
    python lgtv.py apps
    python lgtv.py settings option   # dump settings; try categories: option, picture, network

## 3. Cleaner UI (ad-free launcher)

The stock webOS home screen can't be reskinned, but `launcher/` is a minimal app grid with no
promotions. Install with LG's webOS CLI and a free LG developer account:

1. Install the **Developer Mode** app on the TV, log in, turn Dev Mode on, note the passphrase.
2. `npm i -g @webos-tools/cli`
3. `ares-setup-device --add tv -i "host=192.168.29.179" -i "port=9922" -i "username=prisoner"`
4. `ares-novacom --device tv --getkey` (enter the passphrase)
5. `ares-package launcher && ares-install --device tv com.anirudha.cleanlauncher_1.0.0_all.ipk`
6. `ares-launch --device tv com.anirudha.cleanlauncher`

Dev Mode expires every ~50 hours unless renewed in the Developer Mode app.
