# Attention Heist — adatgyűjtő

Óránként pillanatképet készít öt olyan adatforrásról, amit visszamenőleg
**nem lehet** újra megszerezni. Minden futás egy JSON fájlt ír a `data/`
mappába, dátum szerinti almappákba:

```
data/2026-09-01/1400.json
data/2026-09-01/1500.json
```

## Beüzemelés

1. Hozz létre egy **publikus** GitHub repót, és töltsd fel ezt a három fájlt
   (`collect.py`, `README.md`, `.github/workflows/collect.yml`).
2. A repóban: **Settings → Actions → General → Workflow permissions** →
   állítsd "Read and write permissions"-re. Enélkül nem tud commitolni.
3. Az API kulcsokat a **Settings → Secrets and variables → Actions → New
   repository secret** alatt add meg. Amelyik hiányzik, azt a szkript
   egyszerűen kihagyja, tehát indulhatsz nulla kulccsal is.
4. **Actions** fül → `collect` → **Run workflow**. Ha lefutott és megjelent
   egy fájl a `data/` alatt, kész, innentől magától megy óránként.

## Kulcsok

| Secret neve | Honnan |
|---|---|
| `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET` | dev.twitch.tv → Register Your Application |
| `STEAM_API_KEY` | steamcommunity.com/dev/apikey (opcionális, nélküle is megy) |
| `YOUTUBE_API_KEY` | Google Cloud Console → YouTube Data API v3 |
| `TOMTOM_API_KEY` | developer.tomtom.com |

Változóként (nem secret, hanem *Variables* fül) megadható még a
`YOUTUBE_VIDEO_IDS` — vesszővel elválasztott videó ID-k. Minden új
trailernél ide kell felvenni az újat.

## Amit szándékosan nem csinál

Nem számol semmit. Csak nyers számokat ment. A képletet és az indexet
később, az adat birtokában írjuk meg, és akkor a teljes múltra
visszamenőleg újraszámolható.

## GDELT — kézzel, böngészőből

A GDELT a GitHub megosztott gépeit blokkolja (429 minden kérésre, még
egyetlen, lassított hívásra is), ezért kikerült az óránkénti gyűjtésből.
Az adata viszont visszamenőleges, tehát elég hetente egyszer, kézzel.

Nyisd meg ezt a címet a böngésződben, és mentsd el a JSON-t
`data/backfill/gdelt_volume.json` néven:

```
https://api.gdeltproject.org/api/v2/doc/doc?query=%28%22grand%20theft%20auto%20vi%22%20OR%20%22grand%20theft%20auto%206%22%20OR%20%22gta%20vi%22%20OR%20%22gta%206%22%29&mode=timelinevolraw&timespan=3m&format=json
```

Az országbontáshoz cseréld a `mode=timelinevolraw` részt
`mode=timelinesourcecountry`-ra, a nyelvihez `mode=timelinelang`-ra.

A `timespan=3m` három hónapot jelent; novemberben állítsd `6m`-re.

## Amit nem ez gyűjt, mert utólag is megvan

GH Archive (GitHub események), Wikimedia pageview és edit API,
Stack Exchange API, ENTSO-E áramfogyasztás, EIA (US), Google Trends,
Kastle Systems irodai beléptetés, MTA napi utasszám.
Ezekkel novemberig nem kell foglalkozni.
