# VIAGEM Analýza parcel

Lokální analytická aplikace pro porovnání katastrálního zápisu parcely s viditelným stavem v terénu. Spojuje data ČÚZK CPX, ortofoto, katastrální mapu, ruční závěr analytika a podpůrný model PyTorch v jednom pracovním rozhraní.

## Co aplikace řeší

Pro pět parcel v okrese Jičín zobrazuje:

- oficiální druh a způsob využití z ČÚZK INSPIRE CPX,
- ortofoto, katastrální mapu a ortofoto s úplnou CPX hranicí parcely,
- ruční posouzení viditelného stavu, rizika a dalšího kroku,
- textové indikátory přístupnosti, limitů a geometrie,
- podpůrnou predikci tabulkového modelu PyTorch,
- audit zdrojů a metodická omezení.

OpenStreetMap slouží pouze jako orientační kontext. Důkazní část stojí na CPX, ortofotu, katastrální mapě a auditovatelném rozhodnutí analytika.

## Hlavní funkce

- Vyhledávání a filtrování parcel podle obce, čísla, druhu, rizika a závěru.
- Synchronizovaný výběr parcely v seznamu, mapových kartách, detailu a analytických panelech.
- Přepínání předchozí a další viditelné parcely.
- Důkazní prohlížeč bez ořezu pro čtvercové výřezy ortofota, CPX hranice a KN.
- Geometricky odvozené WMS výřezy, které obsahují celou parcelu i u ploch větších než 1 km².
- Česká vysvětlení sekcí, nápovědy u nadpisů a popisy ovládacích prvků.
- Responzivní pracovní layout: tři sloupce na širokém displeji, dvě nebo jedna pracovní oblast na menších zařízeních.
- Panel `Analytik` pro úpravu ručního závěru, jistoty, rizika, pozorovaného stavu, dalšího kroku a indikátorů.
- Neměnné oficiální CPX atributy v panelu analytika; ruční editace se týká pouze analytického posouzení.
- PyTorch panel s během modelu, predikcemi, pravděpodobnostmi a správou doplňkových trénovacích vzorků.
- Izolovaný smoke test, který nemění pracovní databázi ani produkční model.

## Technický stack

- Python 3.9+
- SQLite
- Python standard library pro HTTP server a API
- HTML, CSS a JavaScript bez sestavovacího kroku
- PyTorch 2.8 pro tabulkový model parcelních atributů
- Pillow pro důkazní snímky a CPX overlay
- pandas pro souhrn kandidátů z CPX CSV

Přesné verze jsou v `requirements.txt`.

## Instalace

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Konfigurační proměnné nejsou potřeba. Aplikace naslouchá pouze na `127.0.0.1`.

## Spuštění

```bash
.venv/bin/python app/server.py
```

Otevřete:

```txt
http://127.0.0.1:8765
```

Uživatelské rozhraní i API obsluhuje stejný lokální server.

## Práce analytika

1. Vyberte parcelu v levém seznamu nebo v mapových kartách.
2. Porovnejte `Ortofoto`, `Hranice` a `KN` v důkazním prohlížeči.
3. Zkontrolujte oficiální stav, pozorovanou realitu, indikátory a podpůrnou predikci.
4. V panelu `Analytik` upravte odůvodněný závěr, jistotu, riziko a další krok.
5. Uložte změnu tlačítkem `Uložit závěr analytika`.

Oficiální druh pozemku, číslo parcely, výměra, CPX reference a zdrojová data nelze tímto panelem měnit. Finální závěr zůstává odpovědností analytika.

## PyTorch

Model `ParcelAtomMLP` používá pouze tabulkové atributy:

- 480 parcel z tabulky `atomove_vzorky`,
- pět analytických parcel z tabulky `parcely`,
- volitelné řádky z tabulky `treninkove_vzorky`,
- výměru, parcelní označení, způsob využití, katastrální území a S-JTSK souřadnice.

Ortofoto slouží k ručnímu důkaznímu posouzení; tento model obrazová data nenačítá.

Trénování z terminálu:

```bash
.venv/bin/python ml/train_pytorch.py
```

Trénování z aplikace:

1. Otevřete sekci `PyTorch`.
2. Volitelně přidejte parcelní nebo ATOM vzorek.
3. Stiskněte `Spustit trénování`.

Výstupy:

- `ml/parcel_atom_mlp.pt`,
- jeden aktuální řádek v `behy_modelu`,
- pět aktuálních řádků v `predikce_modelu`.

Predikce pomáhá řadit případy ke kontrole; nenahrazuje ruční závěr.

## API

```txt
GET    /api/health
GET    /api/stats
GET    /api/parcels
GET    /api/parcels/{id_pripadu}
PUT    /api/parcels/{id_pripadu}/assessment
GET    /api/map-layers
GET    /api/analytics
GET    /api/sources
GET    /api/methodology
GET    /api/ml/run
GET    /api/ml/predictions
GET    /api/ml/predictions/{id_pripadu}
GET    /api/atom-samples
GET    /api/training-samples
POST   /api/training-samples
DELETE /api/training-samples/{id}
POST   /api/ml/train
GET    /media/evidence/{soubor}
```

`PUT /api/parcels/{id_pripadu}/assessment` přijímá celý analytický závěr:

```json
{
  "verdict_level": "partial",
  "confidence": 0.72,
  "risk": "Střední",
  "observed_state": "Popis stavu viditelného na ortofotu.",
  "finding": "Odůvodněný závěr analytika.",
  "action": "Doporučený další krok.",
  "accessibility_indicator": "Co je nutné ověřit k přístupu.",
  "environment_indicator": "Známé limity a chybějící vrstvy.",
  "geometry_indicator": "Interpretace hranice a rozsahu parcely."
}
```

Podporované úrovně závěru jsou `match`, `partial`, `mostly`, `mismatch` a `unknown`. Jistota musí být číslo od 0 do 1 a riziko musí být `Nízké`, `Střední` nebo `Vysoké`.

## Databáze

Pracovní databáze je `data/app.sqlite`. Používá české názvy tabulek:

```txt
parcely
zdroje
metodika
behy_modelu
predikce_modelu
atomove_vzorky
treninkove_vzorky
```

Obnova databáze odstraní její aktuální obsah a sestaví jej z lokálních zdrojů:

```bash
.venv/bin/python scripts/build_app_db.py
```

Po obnově databáze spusťte znovu trénování, aby vznikla metadata běhu a predikce.

## Reprodukovatelný datový postup

Úplný postup ze surových CPX ZIP souborů:

```bash
.venv/bin/python scripts/extract_cpx_parcels.py data/derived/cpx_parcels.csv data/raw/cpx/*.zip
.venv/bin/python scripts/summarize_candidates.py
.venv/bin/python scripts/fetch_wms_evidence.py
.venv/bin/python scripts/build_geometry_overlays.py
.venv/bin/python scripts/build_app_db.py
.venv/bin/python ml/train_pytorch.py
.venv/bin/python scripts/smoke_check.py
```

`fetch_wms_evidence.py` vyžaduje síťové připojení k ČÚZK. Bounding box se počítá z celé CPX geometrie, rozšíří se o okraj a zachová čtvercový poměr pro 1000 × 1000 px výstup. Kříž označuje skutečný referenční bod parcely uvnitř tohoto výřezu.

## Kontrola kvality

```bash
node --check app/static/app.js
PYTHONPYCACHEPREFIX=/tmp/viagem-analytics-pycache .venv/bin/python -m py_compile app/server.py ml/train_pytorch.py scripts/*.py
.venv/bin/python -m pip check
.venv/bin/python scripts/smoke_check.py
```

Smoke test používá dočasnou kopii databáze, modelu a trénovacího skriptu. Ověřuje:

- start lokálního serveru a skutečné připojení k databázi,
- všechny dokumentované GET endpointy,
- načtení HTML, CSS, JavaScriptu a PNG důkazu,
- přidání, validaci a smazání trénovacího vzorku,
- validovanou editaci analytického závěru,
- spuštění 120 epoch PyTorch přes API,
- pět predikcí a existenci nového modelového artefaktu.

## Struktura projektu

```txt
app/server.py                         lokální server, API a validace zápisů
app/static/index.html                 sémantická struktura rozhraní
app/static/styles.css                 responzivní pracovní layout a nápovědy
app/static/app.js                     klientský stav, renderování a ovládání
data/app.sqlite                       pracovní databáze
data/derived/selected_parcels.csv     pět vybraných parcel
data/derived/cpx_parcels.csv          úplný lokální CPX extrakt
data/raw/cpx/                         zdrojové CPX ZIP soubory
reports/evidence/                     ortofoto, KN a CPX overlay
scripts/extract_cpx_parcels.py        reprodukovatelná extrakce CPX
scripts/fetch_wms_evidence.py         WMS důkazy pro celou geometrii
scripts/build_geometry_overlays.py    vykreslení CPX hranic
scripts/build_app_db.py               sestavení SQLite databáze
scripts/smoke_check.py                izolovaný integrační test
ml/train_pytorch.py                   trénování ParcelAtomMLP
ml/parcel_atom_mlp.pt                 aktuální uložený model
SPEC.md                               technická specifikace
```

## Omezení

- Listy vlastnictví a přístupová práva nejsou součástí lokálního CPX extraktu.
- LPIS, ÚHÚL, záplavová území, ochranná pásma a územní plán nejsou importované.
- Ortofoto neprokazuje právní stav ani důvod vzniku porostu.
- Model pracuje s malým lokálním tabulkovým souborem a slouží pouze jako podpůrný signál.
- Obnova databáze je destruktivní a následně vyžaduje nové trénování.

## Řešení problémů

- `File not found` u `/api/ml/run`: spusťte `.venv/bin/python ml/train_pytorch.py`.
- Chybějící parcely: spusťte `.venv/bin/python scripts/build_app_db.py` a potom trénování.
- Chybějící nebo neúplný důkaz: spusťte WMS import a následně CPX overlay.
- Obsazený port `8765`: ukončete proces, který port používá, a spusťte server znovu.
- Chyba importu knihoven: spusťte `.venv/bin/python -m pip install -r requirements.txt` a `.venv/bin/python -m pip check`.
- Smoke test nemůže otevřít lokální port: povolte procesu lokální síťové spojení na `127.0.0.1`.
