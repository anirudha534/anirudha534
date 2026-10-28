# POCO F5: Layered landscape / retro bands (HyperOS + Lawnchair)

Menu names vary between HyperOS versions, so treat the paths below as a guide, not exact.

## Wallpapers

Each design has a `_lock.png` (full detail) and a `_home.png` (blurred, lighter, so icons stay readable).

| Set | Look |
|---|---|
| 01_dusk_rose | Peach sky, plum mountain layers |
| 02_misty_teal | Pale blue sky, teal mountain layers |
| 03_golden_hour | Gold sky, terracotta mountain layers |
| 04_retro_sunset | Cream, mustard, orange and rust rings (like the orange-stripe S25 reference) |
| 05_retro_dusk | Pink, violet and blue rings |
| 06_retro_sage | Cream, sage and teal rings |

Set the `_lock` image on the lock screen and the `_home` image on the home screen. The darkest tones are deep plum, brown or navy, never pure black.

## Lock screen: big typographic clock

- Settings > Wallpaper and personalization > Lock screen > Clock style. Pick the largest, boldest number style (you already have the stacked one).
- Match the clock colour to the wallpaper: a warm brown on 03/04, deep plum on 01, deep teal on 02/06. Use white only if the background behind the clock is dark enough.
- Keep notifications to icons only.

## Home screen: widget dashboard

- **Free:** long-press the home screen > Widgets and use the HyperOS and Lawnchair widgets (clock, weather, calendar, battery). In Lawnchair, keep the At a Glance widget at the top.
- **Custom look (optional, paid):** KWGT (Kustom Widget Maker) lets you build glass-card widgets like the Samsung-style ones in your screenshots. The free version has limits. I can't create KWGT presets from here, so you would import or build them in the app.
- Layout idea: one big widget card (date, weather, battery) at the top, 4 dock apps at the bottom, nothing in between.

## Smoother, more fluid animations

HyperOS animation speed can be tuned:

1. Settings > About phone > tap "OS version" 7 times to enable developer options.
2. Settings > Additional settings > Developer options.
3. Set **Window animation scale**, **Transition animation scale** and **Animator duration scale** to **0.5x** for snappier motion. Try **0.75x** if 0.5x feels too abrupt.
4. In Settings > Home screen (or Lawnchair settings), check the animation or transition options and turn the app opening animation on.
5. Keep the refresh rate on 120 Hz (Settings > Display > Refresh rate).

This makes HyperOS feel faster. It won't copy iOS physics. For that you would need a different ROM, which you chose not to pursue.

## Icons

Lawnchair > Home settings > Icon style: try the **Themed icon source** tab for tinted single-colour icons, or Lines Free on a mid-tone wallpaper such as 04 or 05. On the lighter homes, white outlines will be faint, so prefer themed icons there.
