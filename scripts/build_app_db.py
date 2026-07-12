import csv
import json
import pathlib
import sqlite3


ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "app.sqlite"
SELECTED_PATH = ROOT / "data" / "derived" / "selected_parcels.csv"
CPX_PATH = ROOT / "data" / "derived" / "cpx_parcels.csv"
EVIDENCE_DIR = ROOT / "reports" / "evidence"
DATASET_UPDATED_AT = "2026-07-09"
ATOM_SAMPLE_LIMIT = 480

LAND_LABELS = {
    "ArableGround": "Orná půda",
    "Grassland": "Trvalý travní porost",
    "Forest": "Lesní pozemek",
    "WaterArea": "Vodní plocha",
    "OtherArea": "Ostatní plocha",
    "BuiltUpArea": "Zastavěná plocha",
    "Garden": "Zahrada",
    "Orchard": "Ovocný sad",
}

OSM_CONTEXT = {
    "A": {"lat": 50.3313, "lon": 15.2604, "zoom": 15},
    "B": {"lat": 50.4310, "lon": 15.5785, "zoom": 15},
    "C": {"lat": 50.3351, "lon": 15.2375, "zoom": 14},
    "D": {"lat": 50.3370, "lon": 15.3035, "zoom": 14},
    "E": {"lat": 50.4340, "lon": 15.3600, "zoom": 14},
}


ASSESSMENTS = {
    "A": {
        "official_label": "ArableGround = orná půda",
        "observed_state": "Souvislá obdělávaná pole, patrné zemědělské stopy, okraje s remízy.",
        "verdict": "Odpovídá",
        "verdict_level": "match",
        "confidence": 0.92,
        "risk": "Nízké",
        "accessibility": "K prověření přes okolní polní komunikace; LV ani věcná břemena nejsou v lokálním extraktu.",
        "environment": "Bez importované ochranné vrstvy; pro obchodní závěr doplnit LPIS a limity území.",
        "geometry": "CPX hranice a referenční bod jsou dostupné v ortofoto overlay výřezu.",
        "finding": "Ortofoto ukazuje velký souvislý zemědělský blok. Jsou patrné rozdíly plodin nebo sklizňového stavu a pravidelné stopy hospodaření.",
        "action": "Bez další eskalace; při obchodním rozhodnutí stačí standardní kontrola LPIS a právních omezení.",
    },
    "B": {
        "official_label": "Grassland = trvalý travní porost",
        "observed_state": "Referenční bod leží na louce, ale významná část parcely je porostlá vzrostlou vegetací nebo lesem.",
        "verdict": "Částečně odpovídá",
        "verdict_level": "partial",
        "confidence": 0.68,
        "risk": "Střední",
        "accessibility": "Přístupnost vyžaduje samostatnou kontrolu cest a LV; parcela je rozsáhlá a heterogenní.",
        "environment": "Stromový porost uvnitř parcely vyžaduje doplnění ÚHÚL a ochranných vrstev.",
        "geometry": "CPX overlay je zásadní, protože referenční bod sám nepopisuje celou parcelu.",
        "finding": "Samotný referenční bod podporuje zápis trvalého travního porostu. V rámci stejné velké parcely je ale rozsáhlý stromový porost, takže plocha je reálně heterogenní.",
        "action": "Ručně překrýt celou geometrii parcely s ortofotem, doplnit LPIS/ÚHÚL a rozhodnout, zda je nutná terénní kontrola.",
    },
    "C": {
        "official_label": "Forest = lesní pozemek",
        "observed_state": "Kompaktní lesní porost s různými věkovými strukturami a průseky.",
        "verdict": "Odpovídá",
        "verdict_level": "match",
        "confidence": 0.95,
        "risk": "Nízké",
        "accessibility": "Přístupnost není z CPX vyhodnocena; pro akvizici doplnit cesty, LV a lesnický režim.",
        "environment": "Lesní charakter znamená nutnost prověřit lesnické a ochranné limity.",
        "geometry": "Velká CPX geometrie odpovídá souvislému lesnímu komplexu v ortofotu.",
        "finding": "Ortofoto ukazuje souvislý lesní komplex. Průseky a věkové rozdíly nemění základní lesní charakter pozemku.",
        "action": "Bez nesouladu; pro akvizici doplnit standardní lesnická a ochranná omezení.",
    },
    "D": {
        "official_label": "WaterArea / Pond = vodní plocha / rybník",
        "observed_state": "Rybniční soustava, referenční bod leží ve vodní ploše.",
        "verdict": "Odpovídá",
        "verdict_level": "match",
        "confidence": 0.94,
        "risk": "Nízké",
        "accessibility": "Vodní plocha vyžaduje kontrolu hrází, přístupových cest a vodoprávního režimu mimo CPX.",
        "environment": "Vodní režim je hlavní limit; doplnit vodoprávní a ochranná pásma.",
        "geometry": "CPX hranice odpovídá rybniční soustavě z ortofota.",
        "finding": "Ortofoto ukazuje vodní plochu, hráze, vegetační pásy a navazující rybniční soustavu.",
        "action": "Bez nesouladu; pro akvizici ověřit vodoprávní a provozní režim rybníka.",
    },
    "E": {
        "official_label": "OtherArea / RecreationArea = ostatní plocha / rekreační plocha",
        "observed_state": "Rekreačně-přírodní areál, cesty, otevřené travnaté části, rozptýlené dřeviny a lokální areálové prvky.",
        "verdict": "Převážně odpovídá",
        "verdict_level": "mostly",
        "confidence": 0.78,
        "risk": "Střední",
        "accessibility": "Areálová a rekreační struktura vyžaduje doplnění územního plánu a přístupových práv.",
        "environment": "Smíšená rekreačně-přírodní plocha bez importované ochranné vrstvy; doplnit limity území.",
        "geometry": "CPX overlay podporuje závěr, že parcela je vnitřně členitá.",
        "finding": "Plocha není orná půda ani jednolitý les. Způsob využití rekreační plocha je přiměřený, ale parcela je vnitřně členitá.",
        "action": "Při dalším posouzení rozdělit plochu na funkční části a prověřit územní plán.",
    },
}

SOURCES = [
    {
        "name": "ČÚZK INSPIRE ATOM CPX",
        "role": "Rozšířený parcelní model pro trénovací ATOM vzorky a geometrii",
        "url": "https://services.cuzk.gov.cz/gml/inspire/cpx/epsg-5514/",
        "evidence": "Veřejná stahovací služba ATOM, ZIP/GML po katastrálních územích; lokální ZIP balíčky v data/raw/cpx a extrakt data/derived/cpx_parcels.csv",
    },
    {
        "name": "ČÚZK INSPIRE ATOM CP",
        "role": "Standardní INSPIRE téma Katastrální parcely",
        "url": "https://services.cuzk.gov.cz/gml/inspire/cp/epsg-5514/",
        "evidence": "Veřejná stahovací služba ATOM pro CP, použitá jako metodický zdroj pro strukturu parcelních dat",
    },
    {
        "name": "ČÚZK Ortofoto WMS",
        "role": "Vizuální kontrola reálného stavu",
        "url": "https://ags.cuzk.cz/arcgis1/services/ORTOFOTO/MapServer/WMSServer",
        "evidence": "Ortofoto výřezy v reports/evidence",
    },
    {
        "name": "ČÚZK Katastrální mapa WMS",
        "role": "Kontrola parcelní struktury",
        "url": "https://services.cuzk.gov.cz/wms/local-km-wms.asp",
        "evidence": "KN výřezy v reports/evidence",
    },
]

METHODOLOGY = {
    "useful": [
        "CPX bylo nejspolehlivější pro oficiální druh pozemku, výměru, parcelní číslo a referenční bod.",
        "CPX geometrie umožnila překreslit hranici celé parcely přes ortofoto a odhalit heterogenní plochy.",
        "Ortofoto bylo nejrychlejší pro ruční posouzení reality v terénu.",
        "KN WMS pomohlo kontrolovat, že důkazní výřez sedí na správnou parcelní strukturu.",
    ],
    "gaps": [
        "Referenční bod nestačí pro velké heterogenní parcely.",
        "Ortofoto samo nerozlišuje právní stav, botanický stav ani důvod vzniku porostu.",
        "Pro rozhodnutí o nesouladu je potřeba overlay celé geometrie a další vrstvy jako LPIS nebo ÚHÚL.",
    ],
    "scale": [
        "Normalizovat CPX do SQLite/PostGIS a generovat rizikové kandidáty podle druhu, výměry a vizuálního pokryvu.",
        "Pro každou parcelu automaticky vytvářet ortofoto + KN důkazní výřez.",
        "Finální závěr ponechat analytikovi v auditovatelné škále: odpovídá, částečně odpovídá, pravděpodobný nesoulad, nelze potvrdit.",
    ],
}


def required_evidence(case_id: str, national_ref: str) -> tuple[str, str, str]:
    safe_ref = national_ref.replace("/", "-")
    ortho = EVIDENCE_DIR / f"{case_id}_{safe_ref}_ortho.png"
    kn = EVIDENCE_DIR / f"{case_id}_{safe_ref}_kn.png"
    overlay = EVIDENCE_DIR / f"{case_id}_{safe_ref}_overlay.png"
    if not ortho.exists() or not kn.exists() or not overlay.exists():
        raise FileNotFoundError(f"missing evidence for {case_id}: {ortho} / {kn} / {overlay}")
    return f"/media/evidence/{ortho.name}", f"/media/evidence/{kn.name}", f"/media/evidence/{overlay.name}"


def atom_training_samples() -> list[dict]:
    if not CPX_PATH.exists():
        raise FileNotFoundError(CPX_PATH)
    grouped = {land_type: [] for land_type in LAND_LABELS}
    with CPX_PATH.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            land_type = row["land_type"]
            if land_type in grouped and row["area_m2"].isdigit():
                grouped[land_type].append(row)

    per_type = ATOM_SAMPLE_LIMIT // len(LAND_LABELS)
    selected = []
    for land_type, rows in grouped.items():
        if len(rows) < per_type:
            raise RuntimeError(f"not enough ATOM rows for {land_type}: {len(rows)}")
        rows.sort(key=lambda item: (item["source_zip"], item["zoning"], int(item["area_m2"]), item["label"]))
        step = len(rows) / per_type
        for index in range(per_type):
            selected.append(rows[int(index * step)])

    samples = []
    for index, row in enumerate(selected, start=1):
        samples.append(
            {
                "id_atom_vzorku": f"ATOM-{index:04d}",
                "zdrojovy_zip": row["source_zip"],
                "zdrojove_xml": row["source_xml"],
                "gml_id": row["gml_id"],
                "obec": row["administrative_unit"],
                "katastralni_uzemi": row["zoning"],
                "cislo_parcely": row["label"],
                "narodni_reference": row["national_ref"],
                "vymera_m2": int(row["area_m2"]),
                "druh_pozemku": row["land_type"],
                "popis_druhu": LAND_LABELS[row["land_type"]],
                "zpusob_vyuziti": row["land_use"] or None,
                "souradnice_x_sjtsk": float(row["reference_x_sjtsk"]),
                "souradnice_y_sjtsk": float(row["reference_y_sjtsk"]),
            }
        )
    return samples


def main() -> None:
    if not SELECTED_PATH.exists():
        raise FileNotFoundError(SELECTED_PATH)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE parcely (
            id_pripadu TEXT PRIMARY KEY,
            okres TEXT NOT NULL,
            obec TEXT NOT NULL,
            katastralni_uzemi TEXT NOT NULL,
            cislo_parcely TEXT NOT NULL,
            narodni_reference TEXT NOT NULL,
            vymera_m2 INTEGER NOT NULL,
            druh_pozemku TEXT NOT NULL,
            zpusob_vyuziti TEXT,
            souradnice_x_sjtsk REAL NOT NULL,
            souradnice_y_sjtsk REAL NOT NULL,
            osm_sirka REAL NOT NULL,
            osm_delka REAL NOT NULL,
            osm_priblizeni INTEGER NOT NULL,
            odkaz_vlastnictvi TEXT NOT NULL,
            zdroj_dat TEXT NOT NULL,
            importovano_dne TEXT NOT NULL,
            duvod_vyberu TEXT NOT NULL,
            oficialni_popis TEXT NOT NULL,
            stav_z_ortofota TEXT NOT NULL,
            zaver TEXT NOT NULL,
            uroven_zaveru TEXT NOT NULL,
            jistota REAL NOT NULL,
            riziko TEXT NOT NULL,
            indikator_pristupnosti TEXT NOT NULL,
            indikator_zivotniho_prostredi TEXT NOT NULL,
            indikator_geometrie TEXT NOT NULL,
            nalez TEXT NOT NULL,
            dalsi_krok TEXT NOT NULL,
            ortofoto_obrazek TEXT NOT NULL,
            kn_obrazek TEXT NOT NULL,
            prekryv_obrazek TEXT NOT NULL
        );

        CREATE TABLE zdroje (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazev TEXT NOT NULL,
            uloha TEXT NOT NULL,
            url TEXT NOT NULL,
            dukaz TEXT NOT NULL
        );

        CREATE TABLE metodika (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            obsah TEXT NOT NULL
        );

        CREATE TABLE behy_modelu (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nazev_modelu TEXT NOT NULL,
            knihovna TEXT NOT NULL,
            verze_torch TEXT,
            natrenovano_dne TEXT NOT NULL,
            pocet_vzorku INTEGER NOT NULL,
            epochy INTEGER NOT NULL,
            finalni_loss REAL NOT NULL,
            finalni_presnost REAL NOT NULL,
            parametry TEXT NOT NULL,
            poznamka TEXT NOT NULL
        );

        CREATE TABLE predikce_modelu (
            id_pripadu TEXT PRIMARY KEY REFERENCES parcely(id_pripadu),
            predikovany_druh TEXT NOT NULL,
            predikovany_popis TEXT NOT NULL,
            jistota REAL NOT NULL,
            entropie REAL NOT NULL,
            shoda TEXT NOT NULL,
            pravdepodobnosti TEXT NOT NULL,
            vysvetleni TEXT NOT NULL
        );

        CREATE TABLE atomove_vzorky (
            id_atom_vzorku TEXT PRIMARY KEY,
            zdrojovy_zip TEXT NOT NULL,
            zdrojove_xml TEXT NOT NULL,
            gml_id TEXT NOT NULL,
            obec TEXT NOT NULL,
            katastralni_uzemi TEXT NOT NULL,
            cislo_parcely TEXT NOT NULL,
            narodni_reference TEXT NOT NULL,
            vymera_m2 INTEGER NOT NULL,
            druh_pozemku TEXT NOT NULL,
            popis_druhu TEXT NOT NULL,
            zpusob_vyuziti TEXT,
            souradnice_x_sjtsk REAL NOT NULL,
            souradnice_y_sjtsk REAL NOT NULL
        );

        CREATE TABLE treninkove_vzorky (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            typ_zdroje TEXT NOT NULL CHECK (typ_zdroje IN ('parcela', 'atom')),
            id_pripadu TEXT,
            id_atom_vzorku TEXT REFERENCES atomove_vzorky(id_atom_vzorku),
            stitek_druhu TEXT NOT NULL,
            popis_stitku TEXT NOT NULL,
            cesta_obrazku TEXT,
            poznamka TEXT NOT NULL,
            vytvoreno_dne TEXT NOT NULL
        );
        """
    )

    with SELECTED_PATH.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            assessment = ASSESSMENTS[row["case_id"]]
            ortho, kn, overlay = required_evidence(row["case_id"], row["national_ref"])
            conn.execute(
                """
                INSERT INTO parcely (
                    id_pripadu, okres, obec, katastralni_uzemi, cislo_parcely, narodni_reference, vymera_m2,
                    druh_pozemku, zpusob_vyuziti, souradnice_x_sjtsk, souradnice_y_sjtsk, osm_sirka, osm_delka,
                    osm_priblizeni, odkaz_vlastnictvi, zdroj_dat, importovano_dne, duvod_vyberu, oficialni_popis,
                    stav_z_ortofota, zaver, uroven_zaveru, jistota, riziko, indikator_pristupnosti,
                    indikator_zivotniho_prostredi, indikator_geometrie, nalez, dalsi_krok,
                    ortofoto_obrazek, kn_obrazek, prekryv_obrazek
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["case_id"],
                    "Jičín",
                    row["zoning"],
                    row["zoning"],
                    row["label"],
                    row["national_ref"],
                    int(row["area_m2"]),
                    row["land_type"],
                    row["land_use"] or None,
                    float(row["reference_x_sjtsk"]),
                    float(row["reference_y_sjtsk"]),
                    OSM_CONTEXT[row["case_id"]]["lat"],
                    OSM_CONTEXT[row["case_id"]]["lon"],
                    OSM_CONTEXT[row["case_id"]]["zoom"],
                    "LV/vlastnictví není součástí lokálního CPX extraktu; doplnit přes Nahlížení do KN.",
                    "ČÚZK INSPIRE CPX, ČÚZK Ortofoto WMS, ČÚZK KN WMS, CPX overlay",
                    DATASET_UPDATED_AT,
                    row["selection_reason"],
                    assessment["official_label"],
                    assessment["observed_state"],
                    assessment["verdict"],
                    assessment["verdict_level"],
                    assessment["confidence"],
                    assessment["risk"],
                    assessment["accessibility"],
                    assessment["environment"],
                    assessment["geometry"],
                    assessment["finding"],
                    assessment["action"],
                    ortho,
                    kn,
                    overlay,
                ),
            )

    conn.executemany(
        "INSERT INTO zdroje (nazev, uloha, url, dukaz) VALUES (:name, :role, :url, :evidence)",
        SOURCES,
    )
    conn.execute("INSERT INTO metodika (id, obsah) VALUES (1, ?)", (json.dumps(METHODOLOGY, ensure_ascii=False),))
    conn.executemany(
        """
        INSERT INTO atomove_vzorky (
            id_atom_vzorku, zdrojovy_zip, zdrojove_xml, gml_id, obec, katastralni_uzemi,
            cislo_parcely, narodni_reference, vymera_m2, druh_pozemku, popis_druhu,
            zpusob_vyuziti, souradnice_x_sjtsk, souradnice_y_sjtsk
        ) VALUES (
            :id_atom_vzorku, :zdrojovy_zip, :zdrojove_xml, :gml_id, :obec, :katastralni_uzemi,
            :cislo_parcely, :narodni_reference, :vymera_m2, :druh_pozemku, :popis_druhu,
            :zpusob_vyuziti, :souradnice_x_sjtsk, :souradnice_y_sjtsk
        )
        """,
        atom_training_samples(),
    )
    conn.commit()
    conn.close()
    print(f"built {DB_PATH}")


if __name__ == "__main__":
    main()
