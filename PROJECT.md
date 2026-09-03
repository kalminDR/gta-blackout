# Grand Theft Attention — projektdokumentáció

**Állapot dátuma:** 2026. szeptember 3.
**Cél:** ha ez a beszélgetés elveszik, ebből a fájlból pontosan innen folytatható a munka.
**Használat:** új beszélgetés indításakor töltsd fel ezt a fájlt, plusz a kódfájlokat.

---

## 1. Mi ez a projekt

Nyilvános mérőprojekt arról, hogy a **Grand Theft Auto VI megjelenése mennyi
figyelmet von el a világtól**, és mennyi munka marad emiatt elvégezetlenül.

**Megjelenés: 2026. november 19., csütörtök.** Csak PS5 és Xbox Series X|S,
PC-s verzió a rajtnál nincs. A dátumot már kétszer csúsztatták (eredetileg
2025 ősz, majd 2026. május 26., végül november 19.), tehát **harmadik
halasztásra készülni kell**.

Az, hogy csütörtök, kulcsfontosságú: hétköznap, tehát a produktivitási
narratíva működik. Az, hogy konzolexkluzív, azt jelenti, hogy **magáról a
játékról nincs közvetlen játékosszám-adatunk** (nincs Steam). Ezért minden
forrásunk azt méri, ami *körülötte* történik.

### A tulajdonos

Péter Kalmár, [eureka] (eureka.works) — L&D tanácsadás, komoly játékok,
gamifikált tanulás. Nem programozó. A projekt elsősorban **marketing/brand
játék**, de úgy, hogy komolyan vehető legyen és nemzetközi sajtó átvehesse.

### A narratíva (ez a legfontosabb döntés)

**Nem** az a sztori, hogy „a gémerek lógnak a melóból". Az olcsó, mindenki
azt fogja írni, és ellentétes azzal, amiben az [eureka] hisz.

**A sztori:** egyetlen játék egy nap alatt több önkéntes figyelmet és
viselkedésváltozást vált ki, mint a legtöbb céges képzés egy év alatt.
Emberek hónapokkal előre terveznek, szabadságot vesznek ki, hajnalban
kelnek — manager, deadline és LMS-emlékeztető nélkül. Ugyanezek az emberek
egy kötelező e-learninget nem fejeznek be.

A transzteoretikus modell nyelvén: precontemplation → action, teljesen külső
nyomás nélkül. A záró állítás: **nem az a baj, hogy a GTA elviszi a
figyelmet, hanem hogy a tréninged nem éri meg a figyelmet.**

Ez a keret egyszerre komolyan vehető (kérdés, nem morális ítélet), vicces
(az adat maga szórakoztató) és [eureka]-alakú.

---

## 2. Név, domain, jogi keret

**Megvásárolt domainek (GoDaddy, 2026. szeptember):**
- `grandtheftattention.com` — **ezt használjuk**
- `attentionheist.com` — tartalék, ha jogi nyomás jönne

**Miért van tartalék:** a név a Take-Two védjegyét használja. Ők
pereskedősek. A név önmagában paródiaként védhető, **de csak akkor, ha a
vizuál nem hasonlít a Rockstar arculatára.**

**Ezért az oldalon tilos:** Pricedown betűtípus, Vice City neonrózsaszín-
türkiz paletta, hivatalos logó, trailer stillek, karakterek, pálmafás
naplemente. Ha az oldal GTA-marketinganyagnak néz ki, az összemosás
szándéka bizonyítható.

**A lábléc kötelező eleme:** nyilatkozat, hogy nincs kapcsolat a Rockstar
Gamesszel és a Take-Two Interactive-val, és hogy ez szójáték.

**Későbbi lépés:** 60 nap után a domain átvihető GoDaddy-ról Cloudflare
Registrarba (nincs árrés, ellenállóbb jogi nyomásra). Most ne bonyolítsuk.

---

## 3. Jelenlegi állapot

### Repó

**github.com/kalminDR/gta-blackout** — publikus.

A publikusság nem véletlen: minden mérés egy időbélyeges commit, ami
utólag nem hamisítható. Ez a projekt hitelességi alapja. Ha újságíró
megkérdezi, honnan az adat, a repó linkje a válasz.

### Fájlok a repóban

```
collect.py                      óránkénti gyűjtő
summarise.py                    az összegző
indices.py                      a négy panel és a placebo-számítás
backfill.py                     egyszeri történelmi letöltés
index.html                      a nyilvános oldal
README.md                       rövid beüzemelési leírás
github-query.sql                BigQuery lekérdezés (nem fut automatikusan)
.github/workflows/collect.yml   óránkénti ütemezés
.github/workflows/backfill.yml  kézzel indítható
data/YYYY-MM-DD/HHMM.json       nyers pillanatképek
data/backfill/*.json            történelmi adat
public/latest.json              jelenlegi állapot + változások
public/series.json              teljes idősor
public/chart.json               csak az indexek (kis fájl a grafikonhoz)
```

### A gyűjtés

**Elindult: 2026-09-02 09:14 UTC.** Óránként fut, GitHub Actions
ütemezéssel, ingyen, szerver nélkül.

| Forrás | Állapot | Megjegyzés |
|---|---|---|
| `twitch` | **működik** | top 100 stream, játék és nyelv szerint |
| `steam` | **működik** | 8 játék egyidejű játékosszáma |
| `steam_charts` | **működik** | teljes top 100; `concurrent_in_game` üresen jön, csak `peak_in_game` és a **rangsor** használható |
| `hackernews` | **működik** | `max_item_id`, ebből számoljuk az óránkénti ütemet |
| `youtube` | **működik** | Rockstar csatorna + trailer |
| `traffic` | **működik** | TomTom, 6 város × 3 pont |
| `console_status` | **működik** | PSN + Xbox szolgáltatásállapot |
| `console_prices` | **kulcsra vár** | eBay, jóváhagyás alatt |
| `retail_stock` | **elhagyva** | Best Buy, amerikai telefonszám kell |

Elvetve a vizsgálat után: **GitHub** (botok, lásd 4. szakasz),
**Stack Overflow** (elfogyott), **Reddit** (API bezárt), **tőzsde**
(Yahoo blokkol).

Backfillelve, `data/backfill/`-ben: **MTA utasszám** (validálva, erős),
**Wikipédia** hat nyelven (egészséges, nő), **Stack Overflow**
(csak a feljegyzés kedvéért).

### Beállított GitHub secretek

Beállítva: `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`, `YOUTUBE_API_KEY`,
`TOMTOM_API_KEY`.

Nincs beállítva: `STEAM_API_KEY` (opcionális, nélküle is megy),
`EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `ENTSOE_TOKEN` (a token megvan,
csak fel kell venni), `BESTBUY_API_KEY` (nem is lesz).

**Titkos kulcsot ne másolj chatbe vagy képernyőképre.** Ha mégis
megtörtént, generálj újat — mindegyik szolgáltatásnál egy gomb.

---

## 4. Elvetett és függő források — és miért

Ez a szakasz azért fontos, hogy ne kezdjük újra ezeket a zsákutcákat.

### A legfontosabb tanulság: mi hal meg és mi marad

Négy digitális forrást vizsgáltunk meg alaposan, és **hármat kidobtunk**:
Reddit, GitHub, Stack Overflow. Mind a három technológiai, API-függő,
és mind a három ugyanabba az irányba dőlt el.

Ami viszont kiválónak bizonyult, az MTA utasszám: **fizikai, állami,
unalmas.**

**Ebből következik a beszerzési szabály: ne tech-API-kat keressünk, hanem
kormányzati, fizikai méréseket.** Ide tartozik az áramfogyasztás, a
közlekedési utasszám és a forgalom. Ezek nem szűnnek meg, nem zárnak be,
és nem kell hozzájuk jóváhagyás.

### Az MTA — a projekt legerősebb forrása (validálva 2026. szeptember 3.)

Kilenc közlekedési mód, napi bontás, 2023 januárjától, állami nyílt adat.
Ellenőriztük, hogy tényleg embereket mér-e, és igen:

**A hétvége látszik.** Metró 59%, busz 54%, a két elővárosi vasút 50-50%,
a tisztán ingázóvonal Staten Island-i vasút **33%**. Ezzel szemben a
hidak-alagutak 95%, mert hétvégén az ingázást felváltja a kirándulás.

**A munkaszüneti napok látszanak.** Metró a szokásos hét-napjához mérve:
karácsony **37%**, hálaadás **45%**, újév **49%**, július 4. **61%**.
Sima novemberi csütörtök: 110%.

**Az érzékenység.** Egy novemberen belül a tiszta csütörtökök szórása
2023-ban 0,7%, 2024-ben 1,0%, 2025-ben 0,4%. **A kimutatási küszöb tehát
nagyjából 1,5–2%**, ami kb. 90 000 utas. Ha ennyivel kevesebben szállnak
metróra november 19-én, azt látjuk, és nem lehet a szokásos ingadozásra
fogni.

**Két kódba írandó szabály.** A hálaadást minden alapvonalból ki kell
zárni (november negyedik csütörtökje). És **azonos éven belül** kell
hasonlítani, mert az utasszám évi ~5%-kal nő a járvány utáni
visszaállás miatt.

**2026-os összehasonlító csütörtökök:** november 5. és 12., plusz az
októberiek. Hálaadás idén november 26., tehát a rajtot nem zavarja.

**Súlyozásnál:** a metró, busz és a két vasút erős ingázási jel. A
hidak-alagutak és a manhattani behajtás gyenge, mert hétvégén is majdnem
ugyanannyi.

**Reddit — halott.** 2025 novemberében bevezették a Responsible Builder
Policyt, ami megszüntette az önkiszolgáló API-hozzáférést. Új fejlesztő nem
tud alkalmazást regisztrálni. A nyilvános `.json` végpontok 2026. május
30-án elhaltak, 403-at adnak. Kereskedelmi hozzáférés évi ~12 000 dollártól.
**Helyette: Hacker News**, ami ingyenes és kulcs nélküli.

**Tőzsdei árfolyam — elvetve.** A Yahoo Finance 429-cel utasítja el a
GitHub Actions IP-tartományait, a Stooq is elzárkózik. Hat próbálkozás,
mind sikertelen. **Nem baj: a Yahoo a percenkénti adatot 30 napig
visszamenőleg is kiadja.** Teendő: **2026. december 1-jén** kézzel letölteni
a TTWO, SONY és MSFT novemberi percadatát. Ez a projekt egyetlen kötött
naptári dátuma.

**GitHub / GH Archive — elvetve, 2026. szeptember 3.** Ez volt a
legígéretesebb forrás, és a legalaposabban megvizsgált. Két BigQuery
lekérdezés után egyértelmű lett, hogy nem használható.

*Az első jel:* 2026 augusztusában a commitok napi ritmusa **megfordult**.
Csúcs hajnali 3-kor, mélypont délután 3-kor, és hétvégén 110% a hétköznapi
szinthez képest. Ember nem így dolgozik; ezek CI-rendszerek és kódoló
ügynökök.

*A megerősítés:* botok kiszűrése után, óránkénti mediánban, 2025-09-ről
2026-08-ra: issue kommentek 2 483 → **49**, review kommentek 1 477 → **23**,
pull requestek 7 131 → **138**, csillagozás 5 003 → **50**. Eközben a
commitok 68 497 → **122 065**. A kommentek 98%-a eltűnt, miközben a
commitok duplázódtak — ez nem viselkedésváltozás, hanem az archívum
hibája. A törés 2026 májusában kezdődött.

*A ritmus romlása hónapról hónapra a kommenteken:* 2025-09-ben csúcs
14:00 UTC, hétvége 62% (tankönyvi emberi munkahét). 2026-05-re csúcs
23:00, hétvége 265%.

**Ez publikálható tartalom.** Az októberi módszertani íráshoz: megnéztük a
világ legnagyobb nyilvános munkanaplóját, és elutasítottuk, itt a
bizonyíték. Aki leírja, mit dobott ki, annak a megtartott forrásait is
elhiszik.

**Stack Overflow — elvetve, 2026. szeptember 3.** Heti kérdésszám:
2023 január **20 940**, 2025 augusztus **1 437**. Napi medián 2026
augusztusban: **43 kérdés**, ami a 2023-as szint 1,44%-a. Ekkora
számnál a véletlen ingadozás ±6, tehát egy 15%-os visszaesés
megkülönböztethetetlen a zajtól. Az ok közismert: a nyelvi modellek
elvitték a kérdéseket.

**Best Buy — elvetve.** Ingyenes API van, de a regisztrációhoz amerikai
telefonszám kell SMS-ellenőrzéssel. Nem éri meg egyetlen ország egyetlen
boltláncáért.

**eBay — jóváhagyásra vár.** developer.ebay.com, kézi elbírálás, pár nap.
A kód készen áll, csak a két secret kell. **Production kulcs kell, nem
Sandbox** (a sandbox kitalált adatot ad).

**Kiskereskedelmi ár — novemberre halasztva.** A Keepa API havi 49 euró,
de nem kell az API. A **Keepa weboldal havi 19 eurós előfizetése**
tartalmaz grafikont és adatexportot, az adata pedig **visszamenőleges**
(Amazon árelőzmény US/UK/DE és további piacokra). Teendő novemberben vagy
decemberben: egy hónapra előfizetni, exportálni a PS5, PS5 Pro és Xbox
Series X árelőzményét, lemondani. Összesen 19 euró.

**ENTSO-E (európai áramfogyasztás) — MEGVAN, 2026. szeptember 3.**
A token megérkezett. A My Account → Web API Access oldalon generálható
újra, ha elveszne. GitHub-secret neve: `ENTSOE_TOKEN`.

Ez a forrás a GitHub és a Stack Overflow kiesése után **felértékelődött**:
óránkénti, minden EU-tagállamra, visszamenőleges, állami
hálózatüzemeltetőktől. Pontosan abból a családból való, ami bevált.

---

## 5. Költségvetés

**Eddig elköltve:** 2 domain, kb. 22 euró/év.

**A projekt futtatása havi 0 forint.** GitHub Actions ingyenes, Cloudflare
Pages ingyenes, minden adatforrás ingyenes.

**Egyetlen tervezett kiadás:** Keepa, 19 euró, egyszer.

**Lehetséges később:** Cloudflare Workers fizetős csomag havi 5 dollárért,
de csak ha november 19-én tényleg beszakad a forgalom.

Péter havi 100 dollárig hajlandó költeni. **Nem kell.**

---

## 6. Kutatási eredmények — amit már utánanéztünk

Ezeket ne kelljen újra keresni.

### A konkurencia már lelőtte a főcímet

2026 augusztus végén végigment a sajtón, hogy a GTA VI megjelenése **egy
milliárd dollárnál többe kerülhet az amerikai gazdaságnak**. Forrás: José
Montalvo, Pompeu Fabra egyetem. A számítás: feltételezett 1,5 millió ember
× egy amerikai dolgozó éves GDP-hozzájárulása (70 000 dollár).
**Nyilvános módszertan nincs**, az egyik cikk maga is akadémikus
megjegyzésnek nevezi.

**Következtetés:** a főcím elment, de mindenki tippel és senki nem mér.
A mi pozíciónk: *mi megmértük, és megmutatjuk, hogyan.*

### A GTA V precedens gyenge

A mindenhol idézett szám egy **IGN olvasói szavazás**: 10 995 kitöltő, 46%
mondta, hogy már betáblázta a napot, további 19%, hogy betegre jelenti
magát. Ez a világ legelfogultabb mintája (gémer oldal olvasói), mégis 13
éve kering kutatásként.

**Egyetlen valódi adminisztratív adat:** a kanadai Saskatchewan tartomány
közszolgálatában 2013. szeptember 17. (a GTA V megjelenése) felkerült a
2013–2014-es legtöbb betegszabadságos napok top 25-ös listájára.

**Következtetés:** a GTA V produktivitási hatásáról nincs komoly kutatás.
Ez a hiány maga az indok, amiért a projekt létezik.

### A Cloudflare módszertana — ezt másoljuk

A Cloudflare 2026 nyarán publikált elemzést a foci vb-ről, és pontosan azt
a módszert használta, amire szükségünk van:

- **négyhetes, tornát megelőző alapvonal**
- nem különbség, hanem **arány, kettes alapú logaritmusban** (a növekedés
  és csökkenés így szimmetrikus a nulla körül)
- meccsenként a **kezdés utáni kétórás ablak**
- rangsorhoz az **abszolút eltérések mediánja** (a kiugrás és a visszaesés
  egyaránt hatásnak számít)

**Hatásméret:** Brazília–Japán alatt a brazil forgalom a normális **60%-ára**
esett (nappali meccs). Bosznia egy esti meccs alatt **70%-ra**.

**Stratégiai figyelmeztetés:** a Cloudflare szinte biztosan megcsinálja a
saját GTA VI elemzését is. **Internetforgalomban nem lehet őket lenyomni.**
Amiben verhetetlenek vagyunk: sok független forrás összefésülése, a saját
bevallásos réteg, és az L&D-poén a végén.

### Az áram kalibrációja

A brit hálózat évtizedek óta méri a „TV pickup" jelenséget:

- **1990-es vb-elődöntő, Anglia–NSZK: 2800 MW** keresletugrás (kb. 1,1
  millió vízforraló egyszerre)
- **2018, Anglia–Tunézia: 600 MW**, pedig a hálózat 500-at várt

Ez a **felső határ**: egy tökéletesen szinkronizált országos tévéesemény
0,5–3 GW-ot mozgat. Egy játékmegjelenés **nem szinkronizált**, tehát ennek
töredékét várhatjuk. Magyar becslés: 40 000 plusz konzol = 8 MW egy 5 GW-os
terhelésen = 0,15%, ami a rendszerirányítói előrejelzési hiba alatt van.

**Következtetés:** országos szinten valószínűleg nem látszik. EU-szinten
összeadva van esély, mert a zaj részben kioltja egymást. Érdemes megcsinálni
és **őszintén kiírni, ha a zajszint alatt marad.**

### Akadémiai precedens

**Edmans, García & Norli (2007), Journal of Finance** — 39 ország adatán:
egy vb-kieséses meccs elvesztése után a vesztes ország tőzsdéje másnap
**49 bázisponttal** esik. Erősebb a kis papíroknál és a fontosabb
meccseknél.

Ez a legjobb hivatkozás arra, hogy egy sportesemény hangulati hatása valódi
pénzben mérhető, lektorált csúcsfolyóiratban.

**Az őszinteség kedvéért kiírandó:** egy friss, még nem lektorált
munkaanyag szerint a hatás alig kimutatható a mély, globális piacokon.

### Egyéb

**Halo 3, 2007:** ugyanez a jelenség „Halo Holiday" néven; több kiadó emiatt
tolta péntekre a megjelenéseit. **A GTA VI viszont csütörtökön jön** — jó
bekezdés a cikkbe.

**A 9/11-et hagyjuk ki.** Tragédia egy videojáték mellé téve ízléstelen, és
a sajtó arról fog írni, nem az adatról.

**Felnőttoldalak forgalmi statisztikáit is hagyjuk ki.** Virális, de
tönkretenné az [eureka] nevét.

---

## 7. Az index módszertana

Ez a projekt szellemi magja.

### Miért index és nem nyers szám

Az újságíró nem azt idézi, hogy „3,1 millióan játszottak", hanem hogy
„a Grand Theft Attention index 340-en tetőzött". **Az index a miénk, a nyers
szám nem.**

### Hogyan épül

**100 = teljesen szokásos óra.**

Minden mérést **ugyanahhoz az órához ugyanazon a hétköznapon** hasonlítunk
(szerda 14:00 a korábbi szerda 14:00-khoz), mert a napi és heti ciklus
nagyobb, mint bármilyen megjelenés hatása lesz. Ez a szezonális igazítás.

Az alapvonal a hasonló órák **mediánja** (nem átlaga, hogy egy kiugró
mérés ne rontsa el).

Minden metrika **először elosztódik a saját alapvonalával**, és csak a
kapott arányokat átlagoljuk **mértani középpel**. Ez fontos: ha a nyers
számokat adnánk össze, a milliós Steam-adat agyonnyomná a többit. A mértani
közép az arányok helyes átlaga (egy duplázódás és egy felezés kioltja
egymást).

### A négy panel (átépítve 2026. szeptember 2-án)

A `summarise.py` azóta átalakult: két index helyett **négy panel** van,
és az `indices.py` külön modulban számol.

| Panel | Mit mér | Irány nov. 19-én |
|---|---|---|
| **Attention** | GTA VI nézők, csatornák, trailer megtekintés/óra | fel |
| **Displacement** | Steam-játékok, Twitch GTA-n kívüli nézők | **le** |
| **Work & Mobility** | forgalom hat városban, Hacker News | le |
| **Infrastructure** | PSN és Xbox incidensek | fel |

**A Displacement a legfontosabb javítás.** Korábban a Steam-kosár az
Attention Indexben volt, „fel" iránnyal — csakhogy a Steam pont azt méri,
hogy *más* játékokkal kevesebbet játszanak. Ha november 19-én beüt a
hatás, a Twitch felmegy, a Steam lemegy, és a két komponens **kioltotta
volna egymást**. Az index nem mozdult volna. Ez a legrosszabb fajta hiba:
nem hibaüzenetet ad, hanem hihető nullát.

**Placebo-csütörtökök.** Ugyanaz a számítás minden korábbi csütörtökre,
így nem azt mondjuk, hogy „az index 180 volt", hanem hogy „az eltérés
nagyobb volt, mint a korábbi csütörtökök 99%-án". Ez majdnem ingyen van,
mert az adat úgyis ott lesz, és sokkal erősebb mondat.

**`frozen_metrics`.** Ha egy forrás soha nem mozdul (a YouTube
csatornastatisztikát erősen cache-eli, a feliratkozószám százezerre
kerekített), az örökre nulla eltérést ad, és lefelé húzza a panel
mediánját a „nem történik semmi" felé. Az ilyet a kód automatikusan
kihagyja és kiírja a nevét.

**Kumulált szám helyett sebesség.** Az összes megtekintés sosem csökken,
tehát az alapvonaltól magától elsodródik. Helyette óránkénti változás.

**Alapvonal-küszöbök:** `min_samples_hour_of_week` 6,
`min_samples_hour_of_day` 10. Ezért mutat az oldal szeptemberben még
`null` értékeket — **ez helyes viselkedés**, az első indexek október
elején jelennek meg.

### Fokozatos leépülés

1. Elég minta ugyanabból a hét-órából → `hour_of_week` alapvonal
2. Ha nincs, ugyanaz a napszak → `hour_of_day` alapvonal
3. Ha az sincs → **üres**, nem kitalált szám

`MIN_BASELINE_SAMPLES = 2`. A `baseline_quality` mező őszintén kiírja,
melyik szint volt használható.

---

## 8. A weboldal

### Vizuális koncepció

**Sávos nyomtatópapír** — az a folytonos, halványzöld-fehér csíkos papír,
amire a nagygépek évtizedeken át printelték a jelentéseket. Ez nem retró
poén: a projekt szó szerint **egy gép, ami 79 napon át óránként lenyom egy
sort.** Ráadásul semmiben nem hasonlít a Rockstar arculatára, ami jogilag
lényeges.

**Paletta:**
```
--paper:    #F1F3EC   papír
--bar:      #DCE6D8   a zöld sáv
--ink:      #16241B   mélyzöld-fekete
--ink-soft: #5B6B5E   halvány szöveg
--rule:     #B9C7B6   vonalak
--red:      #B93326   főkönyvi piros: a mínusz
```

**Betűk:** Archivo (900) a címekhez, IBM Plex Mono mindenhez. Két
világosan elkülönülő hang: a gép kimenete és az ember érvelése.

**Nyelv: angol.** Nemzetközi sajtót akarunk.

### Szerkezet

1. **Attention Index** nagy számban, betöltéskor egyszer felpörög
2. **Grafikon**, ami szeptembertől november 19-ig fut, és a **jobb oldala
   üres** — az üresség maga az üzenet. 24 órás csúszó medián, hogy a vonal
   ne legyen szőrös. A skála magától kinyílik, ha jön a csúcs.
3. **A főkönyv:** minden mérés egy sor, sávos háttéren, **a csökkenés
   pirossal**
4. Mit mérünk és miért
5. Email-feliratkozás
6. Lábléc: [eureka], védjegynyilatkozat

### Tudatos döntések

- **Nincs tizedesjegy.** Az alapvonal néhány mintából épül; a 97,8 hamis
  pontosságot sugallna.
- **Nincs index, amíg nincs mihez hasonlítani.** „building the baseline"
  jelenik meg, nem egy hamis 100.
- Mobilon a heti oszlop elrejtve (négy számoszlop olvashatatlan).
- Ha az adat nem tölthető be, ezt kiírja, nem mutat nullát.

### Hostolás

**Cloudflare Pages**, ugyanabból a repóból, ingyen. Minden gyűjtői commit
után magától frissül. Nincs szerver, nincs karbantartás.

Az email-gyűjtéshez **Cloudflare Worker** kell. Az `index.html`-ben van egy
`SIGNUP_ENDPOINT` konstans; amíg üres, az űrlap **őszintén megmondja, hogy
még nem működik**, ahelyett hogy úgy tenne, mintha elküldte volna.

---

## 9. Hibák, amiket már megtaláltunk

Ezekbe ne fussunk bele újra.

**A GitHub webes szerkesztője elrontja a YAML-t.** Beillesztéskor
automatikusan behúz, a YAML-ban pedig a behúzás a jelentés. Eredmény:
„Invalid workflow file", és minden push után egy azonnal bukó futás.
**Megoldás: a `.yml` fájlokat mindig fájlként tölteni fel** (Add file →
Upload files), a mappán belülről, soha ne a ceruzával.

**A konzolstátusz 340 000 karaktert adott vissza** (43 ország × 5
szolgáltatás × több nyelv), a fájl 97%-át. **Megoldás:** csak azt mentjük,
hány szolgáltatást néztünk és melyiknek van gondja. 340 000 → 329 karakter.
*Ha valaha újraírjuk a gyűjtőt, ezt a tömörítést nem szabad elhagyni.*

**Az orosz PlayStation Store 2022 óta „hibás"** a PSN státuszban. Ez
állandó állapot, nem valódi incidens. Novemberben ne ezen csodálkozzunk.

**A forgalmi mérés eleinte rossz volt.** Városközponti koordinátákat
használtunk, a TomTom pedig a legközelebbi útszakaszt adja vissza — New York
egy 90 méteres mellékutcára esett (soha nincs dugó), London pedig hívásonként
más szakaszt adott. **Megoldás:** városonként 3 pont nagy bevezető utakon,
és a másodpercek összeadása, majd osztás (nem a százalékok mediánja), mert
így minden szakasz a saját hosszával számít.

**A TomTom `frc` mezője szöveg** (`FRC4`), nem szám. Az útkategória
diagnosztika: 0 = autópálya, 7 = mellékutca. Ha idővel emelkedik, a mérési
pont lecsúszott.

**A Hacker News számlálója pár percet késik.** Rövid szüneteknél (4–11 perc)
szisztematikusan alábecsül: 280–587 jött ki 865–991 helyett. **Megoldás:**
csak **fél óránál hosszabb és 3 óránál rövidebb** szüneteknél számolunk
ütemet, egyébként üres.

**Ne indítsd kézzel a gyűjtést.** Rövid szüneteket csinál, ami rontja a
mérést. Hagyd az óránkénti ütemezésre.

**Az egészségellenőrző háromféle állapotot ismer.** `ok` / `waiting for key`
(nincs kulcs — ez döntés, nem hiba, **nem küld emailt**) / `DEAD` (van
kulcs, mégsem ad adatot — email megy). Ez azért fontos, mert napi 24 hamis
riasztás után az ember minden riasztást figyelmen kívül hagy.

---

## 10. Következő lépések

### Azonnal (szeptember 3-4.)

1. **ENTSO-E token újragenerálása** (a régi képernyőképen látszott), majd
   felvenni GitHub-secretként `ENTSOE_TOKEN` néven.
2. **`index.html` feltöltése a repóba.** Jelenleg nincs fenn, ezért az
   oldalnak nincs URL-je. Utána GitHub Pages: Settings → Pages → Deploy
   from a branch → main → / (root). Ideiglenes cím:
   `https://kalmindr.github.io/gta-blackout/`
3. **Az `index.html` hozzáigazítása az új adatszerkezethez.** A `summarise.py`
   azóta átépült: az index már nem `attention_index` néven a gyökérben van,
   hanem egy `indices` blokkban (`attention`, `displacement`, `work`,
   `infrastructure`), plusz van `panels` és `placebo`. Az oldal még a régi
   helyen keres.
4. **Forgalmi ellenőrzés.** Varsó 212%-os késést adott szeptember 3-án
   reggel — vagy baleset, vagy elcsúszott pont. New York továbbra is
   gyanúsan gyakran 0,0%. Ha ismétlődik, cserélni kell a koordinátákat.

### Rövid távon (szeptember)

- A napi adatok (MTA, Wikipédia, GitHub) beépítése egy **külön napi
  indexbe**, több éves alapvonallal. Ez teszi a Work Indexet védhetővé.
- Cloudflare Pages beüzemelése a grandtheftattention.com-ra.
- Cloudflare Worker az email-gyűjtéshez, majd `SIGNUP_ENDPOINT` kitöltése.
- **Az oldal publikálása szeptember közepén.**
- eBay kulcsok beállítása, amint megjön a jóváhagyás.
- **ENTSO-E gyűjtő megírása** a most megszerzett tokennel.
- **Chicago napi utasszám** (data.cityofchicago.org, nyílt adat, ingyenes,
  kulcs nélkül). Egy második, független metróhálózat sokkal erősebb
  állítást enged: ha két város egyszerre esik, az nem véletlen.

### Október — az első sajtómomentum

**Ez a projekt legfontosabb hónapja.**

Publikálni a módszertant és a **jóslatot, mielőtt bármi történne**. Ez a
különbség aközött, hogy utólag rátaláltál egy mintázatra, és aközött, hogy
megjósoltad. Két sajtómomentum egy helyett.

Ekkor élesedik a bevallásos gomb is („kivettem szabit" / „betegre
jelentkeztem" / „bemegyek, de nem fogok dolgozni", országgal és
iparággal). GDPR: semmi azonosítható, országnál és iparágnál mélyebbre nem
megyünk.

### November 1–18

Felfutási tartalom hetente. **A launch napi szövegeket előre megírni** —
november 19-én nem lesz idő fogalmazni.

### November 19–20

Élő üzem. Ezen a napon nem elemzünk, csak posztolunk.

### December 1. — kötött dátum

**TTWO, SONY, MSFT percenkénti árfolyam letöltése** a Yahoo 30 napos
ablakából. Utána eltűnik.

### November vége — a jelentés

Itt jön az L&D lezárás: az önkéntes és a kötelező figyelem
összehasonlítása, és itt kerül az [eureka] neve a lap aljára. Ez az, amit
egy HR-igazgató fél év múlva is megnyit.

### A GDP-kalkulátor

**Mérni nem tudjuk.** A lánc: mért visszaesés → feltételezett létszám →
feltételezett óraszám → OECD egy munkaórára jutó GDP → dollár. **Csak az
első láncszem mérés.**

Ezt nem elrejteni kell, hanem **csúszkákra tenni**: az olvasó maga állítja a
feltételezéseket és látja a végösszeget. Így a szám nem a mi állításunk,
hanem egy nyitott számítás. Pontosan ez hiányzik a Montalvo-féle
becslésből.

**Nagyságrend:** a világ napi GDP-je kb. 300 milliárd dollár. Hihető becslés
1 és néhány milliárd között. Tíz milliárd nevetséges, százmillió érdektelen.

### A szabadságról

**Nem mérhető.** Sehol nincs napi bontású, nyilvános szabadságadat. Három
közelítés: MTA utasszám (hányan utaztak), Kastle Systems beléptetőkártya-
adat (heti bontás, amerikai irodák), és a saját bevallásos gombunk.

**Ezt ki kell írni az oldalra: becsüljük, nem mérjük.** Aki ezt leírja
magától, annak a többi számát is elhiszik.

---

## 11. Külső javaslatok — mit vettünk át és mit nem

Egy ChatGPT-review átnézte a projektet 2026. szeptember 2-án. A döntés
megszületett, ne kelljen újra végigvitatni.

**Átvéve:** a Steam-előjel javítása (ebből lett a Displacement panel),
YouTube kumulált szám helyett óránkénti sebesség, Twitch GTA-kategória
külön követése, placebo-csütörtökök, helyi idő a városoknál, valamint
mért/modellezett/bevallott címkék (`evidence` mező — a JSON-ban benne
van, az oldalon még nincs kirajzolva).

**Kihagyva:** Cloudflare Radar (licencfeltételek), Bluesky (folyamatos
kapcsolatot igényel, nem fér az óránkénti ütemezésbe), és a javasolt
méretű vállalati panel (5–20 cég, 78 nap alatt nem reális).

**Nyitva hagyva:** a vállalati panel *kicsinyített* változata. Egy-két
ügyfél, egyetlen aggregált szám. Ez saját, első kézből származó adat
lenne, amit senki más nem tud reprodukálni.

**A reviewer klasszikus hibája**, amire figyelni kell a jövőben is: tíz új
adatforrást javasolt egy szó nélkül arról, ki csinálja meg 78 nap alatt.
Minden javaslat helyes külön-külön, együtt viszont megölik a projektet.

## 12. Az oldal három élete

A legtöbb ilyen projekt csak a középsőt építi meg, és november 20-án
meghal.

1. **Megjelenés előtt:** visszaszámláló és jóslat. Egyetlen dolga van:
   email címeket és bevallásokat gyűjteni.
2. **A megjelenés napján:** élő műszerfal.
3. **Utána:** jelentés. **Az [eureka] szempontjából ez ér a legtöbbet**,
   mert itt van a szakmai poén, és ez fog évekig ott ülni a neten.

### Halasztási terv

A dátum **konfigurációs érték** a kódban (`RELEASE` az index.html-ben),
nincs beégetve. Legyen a fiókban egy megírt poszt arra az esetre, ha
harmadszor is csúszik. Aki elsőként reagál egy halasztásra kész, vicces
oldallal, az is nyer valamit.

---

## 13. Amit egy új beszélgetésben tudni kell rólam

- **Nem vagyok programozó.** Lépésről lépésre kell elmagyarázni, hova
  kattintsak.
- A kódot **ne csak megírd, hanem teszteld is**, és mondd el, mit
  ellenőriztél. Ez eddig többször megfogott valódi hibát.
- **Ne találj ki adatot.** Ha egy végpontot nem tudsz letesztelni, mondd meg,
  és építs be diagnosztikát, amiből az első éles futás után kiderül.
- Ha valami nem működik, **inkább ejtsük**, mint hogy órákat öljünk bele —
  főleg ha visszamenőleg úgyis megszerezhető.
