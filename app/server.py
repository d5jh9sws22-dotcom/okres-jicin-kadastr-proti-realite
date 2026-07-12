import json
import mimetypes
import pathlib
import sqlite3
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import unquote, urlparse


ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "app.sqlite"
STATIC_DIR = ROOT / "app" / "static"
EVIDENCE_DIR = ROOT / "reports" / "evidence"
MODEL_PATH = ROOT / "ml" / "parcel_atom_mlp.pt"
TRAIN_SCRIPT = ROOT / "ml" / "train_pytorch.py"
PYTHON_BIN = ROOT / ".venv" / "bin" / "python"

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

VERDICT_LEVELS = {
    "match": "Odpovídá",
    "partial": "Částečně odpovídá",
    "mostly": "Převážně odpovídá",
    "mismatch": "Pravděpodobný nesoulad",
    "unknown": "Nelze potvrdit",
}

RISK_LEVELS = {"Nízké", "Střední", "Vysoké"}
ASSESSMENT_FIELDS = {
    "observed_state": "stav_z_ortofota",
    "accessibility_indicator": "indikator_pristupnosti",
    "environment_indicator": "indikator_zivotniho_prostredi",
    "geometry_indicator": "indikator_geometrie",
    "finding": "nalez",
    "action": "dalsi_krok",
}


def connect(readonly: bool = True) -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"database not found: {DB_PATH}. Run scripts/build_app_db.py first.")
    if readonly:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}


def get_parcels() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id_pripadu AS case_id,
                okres AS district,
                obec AS municipality,
                katastralni_uzemi AS zoning,
                cislo_parcely AS label,
                narodni_reference AS national_ref,
                vymera_m2 AS area_m2,
                druh_pozemku AS land_type,
                zpusob_vyuziti AS land_use,
                souradnice_x_sjtsk AS reference_x_sjtsk,
                souradnice_y_sjtsk AS reference_y_sjtsk,
                osm_sirka AS osm_lat,
                osm_delka AS osm_lon,
                osm_priblizeni AS osm_zoom,
                odkaz_vlastnictvi AS ownership_reference,
                zdroj_dat AS data_source,
                importovano_dne AS imported_at,
                duvod_vyberu AS selection_reason,
                oficialni_popis AS official_label,
                stav_z_ortofota AS observed_state,
                zaver AS verdict,
                uroven_zaveru AS verdict_level,
                jistota AS confidence,
                riziko AS risk,
                indikator_pristupnosti AS accessibility_indicator,
                indikator_zivotniho_prostredi AS environment_indicator,
                indikator_geometrie AS geometry_indicator,
                nalez AS finding,
                dalsi_krok AS action,
                ortofoto_obrazek AS ortho_image,
                kn_obrazek AS kn_image,
                prekryv_obrazek AS overlay_image
            FROM parcely
            ORDER BY id_pripadu
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def get_parcel(case_id: str) -> dict:
    for parcel in get_parcels():
        if parcel["case_id"] == case_id:
            return parcel
    raise KeyError(case_id)


def get_sources() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT nazev AS name, uloha AS role, url, dukaz AS evidence FROM zdroje ORDER BY id").fetchall()
    return [row_to_dict(row) for row in rows]


def get_methodology() -> dict:
    with connect() as conn:
        row = conn.execute("SELECT obsah FROM metodika WHERE id = 1").fetchone()
    if row is None:
        raise RuntimeError("methodology row missing")
    return json.loads(row["obsah"])


def get_stats() -> dict:
    parcels = get_parcels()
    total_area = sum(parcel["area_m2"] for parcel in parcels)
    by_verdict: dict[str, int] = {}
    by_land_type: dict[str, int] = {}
    for parcel in parcels:
        by_verdict[parcel["verdict"]] = by_verdict.get(parcel["verdict"], 0) + 1
        by_land_type[parcel["land_type"]] = by_land_type.get(parcel["land_type"], 0) + 1
    return {
        "parcel_count": len(parcels),
        "total_area_m2": total_area,
        "total_area_ha": round(total_area / 10000, 2),
        "by_verdict": by_verdict,
        "by_land_type": by_land_type,
        "risk_count": sum(1 for parcel in parcels if parcel["risk"] != "Nízké"),
    }


def get_map_layers() -> dict:
    parcels = get_parcels()
    return {
        "base_layers": [
            {
                "id": "osm",
                "name": "OpenStreetMap",
                "role": "Orientační mapový kontext",
                "url": "https://www.openstreetmap.org",
            },
            {
                "id": "cuzk_ortho_wms",
                "name": "ČÚZK Ortofoto WMS",
                "role": "Ortofoto důkaz",
                "url": "https://ags.cuzk.cz/arcgis1/services/ORTOFOTO/MapServer/WMSServer?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0",
            },
            {
                "id": "cuzk_kn_wms",
                "name": "ČÚZK Katastrální mapa WMS",
                "role": "Katastrální mapový důkaz",
                "url": "https://services.cuzk.gov.cz/wms/local-km-wms.asp?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0",
            },
            {
                "id": "cpx_overlay",
                "name": "CPX parcel boundary overlay",
                "role": "Lokální důkaz hranice parcely z CPX",
                "url": None,
            },
        ],
        "parcels": [
            {
                "case_id": parcel["case_id"],
                "label": parcel["label"],
                "municipality": parcel["municipality"],
                "district": parcel["district"],
                "national_ref": parcel["national_ref"],
                "land_type": parcel["land_type"],
                "verdict": parcel["verdict"],
                "risk": parcel["risk"],
                "center": {
                    "lat": parcel["osm_lat"],
                    "lon": parcel["osm_lon"],
                    "zoom": parcel["osm_zoom"],
                    "sjtsk_x": parcel["reference_x_sjtsk"],
                    "sjtsk_y": parcel["reference_y_sjtsk"],
                },
                "evidence": {
                    "ortho": parcel["ortho_image"],
                    "kn": parcel["kn_image"],
                    "overlay": parcel["overlay_image"],
                },
            }
            for parcel in parcels
        ],
    }


def get_analytics() -> dict:
    parcels = get_parcels()
    predictions = {prediction["case_id"]: prediction for prediction in get_ml_predictions()}
    return {
        "summary": get_stats(),
        "outputs": [
            {
                "case_id": parcel["case_id"],
                "parcel": f"{parcel['municipality']} {parcel['label']}",
                "official_land_type": parcel["land_type"],
                "observed_state": parcel["observed_state"],
                "verdict": parcel["verdict"],
                "confidence": parcel["confidence"],
                "risk": parcel["risk"],
                "accessibility_indicator": parcel["accessibility_indicator"],
                "environment_indicator": parcel["environment_indicator"],
                "geometry_indicator": parcel["geometry_indicator"],
                "evidence_sources": parcel["data_source"],
                "ml_prediction": predictions[parcel["case_id"]],
            }
            for parcel in parcels
        ],
    }


def get_ml_run() -> dict:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                id,
                nazev_modelu AS model_name,
                knihovna AS framework,
                verze_torch AS torch_version,
                natrenovano_dne AS trained_at,
                pocet_vzorku AS training_samples,
                epochy AS epochs,
                finalni_loss AS final_loss,
                finalni_presnost AS final_accuracy,
                parametry AS parameters,
                poznamka AS note
            FROM behy_modelu
            WHERE id = 1
            """
        ).fetchone()
    if row is None:
        raise FileNotFoundError("ML run missing. Run ml/train_pytorch.py first.")
    data = row_to_dict(row)
    data["parameters"] = json.loads(data["parameters"])
    data["model_artifact"] = str(pathlib.Path(MODEL_PATH.parent.name) / MODEL_PATH.name)
    data["model_artifact_exists"] = MODEL_PATH.exists()
    return data


def get_ml_predictions() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                p.id_pripadu AS case_id,
                p.predikovany_druh AS predicted_land_type,
                p.predikovany_popis AS predicted_label,
                p.jistota AS confidence,
                p.entropie AS entropy,
                p.shoda AS agreement,
                p.pravdepodobnosti AS probabilities,
                p.vysvetleni AS explanation,
                parcely.druh_pozemku AS official_land_type
            FROM predikce_modelu p
            JOIN parcely ON parcely.id_pripadu = p.id_pripadu
            ORDER BY p.id_pripadu
            """
        ).fetchall()
    predictions = []
    for row in rows:
        prediction = row_to_dict(row)
        prediction["probabilities"] = json.loads(prediction["probabilities"])
        predictions.append(prediction)
    return predictions


def get_ml_prediction(case_id: str) -> dict:
    for prediction in get_ml_predictions():
        if prediction["case_id"] == case_id:
            return prediction
    raise KeyError(case_id)


def get_atom_samples() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id_atom_vzorku AS atom_sample_id,
                zdrojovy_zip AS source_zip,
                zdrojove_xml AS source_xml,
                gml_id,
                obec AS municipality,
                katastralni_uzemi AS zoning,
                cislo_parcely AS label,
                narodni_reference AS national_ref,
                vymera_m2 AS area_m2,
                druh_pozemku AS land_type,
                popis_druhu AS land_type_label,
                zpusob_vyuziti AS land_use,
                souradnice_x_sjtsk AS reference_x_sjtsk,
                souradnice_y_sjtsk AS reference_y_sjtsk
            FROM atomove_vzorky
            ORDER BY id_atom_vzorku
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def get_atom_sample(atom_sample_id: str) -> dict:
    atom_sample_id = atom_sample_id.upper().strip()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                id_atom_vzorku AS atom_sample_id,
                zdrojovy_zip AS source_zip,
                zdrojove_xml AS source_xml,
                gml_id,
                obec AS municipality,
                katastralni_uzemi AS zoning,
                cislo_parcely AS label,
                narodni_reference AS national_ref,
                vymera_m2 AS area_m2,
                druh_pozemku AS land_type,
                popis_druhu AS land_type_label,
                zpusob_vyuziti AS land_use,
                souradnice_x_sjtsk AS reference_x_sjtsk,
                souradnice_y_sjtsk AS reference_y_sjtsk
            FROM atomove_vzorky
            WHERE id_atom_vzorku = ?
            """,
            (atom_sample_id,),
        ).fetchone()
    if row is None:
        raise KeyError(atom_sample_id)
    return row_to_dict(row)


def get_training_samples() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                tv.id,
                tv.typ_zdroje AS source_type,
                tv.id_pripadu AS case_id,
                tv.id_atom_vzorku AS atom_sample_id,
                tv.stitek_druhu AS land_type,
                tv.popis_stitku AS label,
                tv.cesta_obrazku AS image_path,
                tv.poznamka AS note,
                tv.vytvoreno_dne AS created_at,
                av.obec AS atom_municipality,
                av.katastralni_uzemi AS atom_zoning,
                av.cislo_parcely AS atom_label,
                av.vymera_m2 AS atom_area_m2
            FROM treninkove_vzorky tv
            LEFT JOIN atomove_vzorky av ON av.id_atom_vzorku = tv.id_atom_vzorku
            ORDER BY tv.id DESC
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_training_sample(payload: dict) -> dict:
    source_type = str(payload.get("source", "parcela")).lower().strip()
    note = str(payload.get("note", "")).strip() or "Doplňkový trénovací vzorek z lokální evidence."
    if source_type not in {"parcela", "atom"}:
        raise ValueError(f"Nepodporovaný typ vzorku: {source_type}")

    case_id = None
    atom_sample_id = None
    image_path = None

    if source_type == "atom":
        atom = get_atom_sample(str(payload.get("atom_sample_id", "")))
        atom_sample_id = atom["atom_sample_id"]
        land_type = str(payload.get("land_type") or atom["land_type"]).strip()
        if land_type != atom["land_type"]:
            raise ValueError("ATOM vzorek musí používat druh pozemku z ČÚZK.")
    else:
        case_id = str(payload.get("case_id", "")).upper().strip()
        land_type = str(payload.get("land_type", "")).strip()
        parcel = get_parcel(case_id)
        image_path = parcel["ortho_image"]

    if land_type not in LAND_LABELS:
        raise ValueError(f"Nepodporovaný druh pozemku: {land_type}")

    now = datetime.now(timezone.utc).isoformat()
    with connect(readonly=False) as conn:
        cursor = conn.execute(
            """
            INSERT INTO treninkove_vzorky (
                typ_zdroje, id_pripadu, id_atom_vzorku, stitek_druhu, popis_stitku, cesta_obrazku, poznamka, vytvoreno_dne
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_type, case_id, atom_sample_id, land_type, LAND_LABELS[land_type], image_path, note, now),
        )
        conn.commit()
        new_id = int(cursor.lastrowid)
    return next(sample for sample in get_training_samples() if sample["id"] == new_id)


def delete_training_sample(sample_id: int) -> dict:
    with connect(readonly=False) as conn:
        cursor = conn.execute("DELETE FROM treninkove_vzorky WHERE id = ?", (sample_id,))
        conn.commit()
    if cursor.rowcount != 1:
        raise KeyError(str(sample_id))
    return {"deleted": sample_id}


def update_assessment(case_id: str, payload: dict) -> dict:
    required = {*ASSESSMENT_FIELDS, "verdict_level", "confidence", "risk"}
    missing = sorted(required - payload.keys())
    unexpected = sorted(payload.keys() - required)
    if missing:
        raise ValueError(f"Chybí pole hodnocení: {', '.join(missing)}")
    if unexpected:
        raise ValueError(f"Nepodporovaná pole hodnocení: {', '.join(unexpected)}")

    verdict_level = str(payload["verdict_level"]).strip()
    if verdict_level not in VERDICT_LEVELS:
        raise ValueError(f"Nepodporovaná úroveň závěru: {verdict_level}")

    risk = str(payload["risk"]).strip()
    if risk not in RISK_LEVELS:
        raise ValueError(f"Nepodporovaná úroveň rizika: {risk}")

    try:
        confidence = float(payload["confidence"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Jistota musí být číslo od 0 do 1.") from exc
    if not 0 <= confidence <= 1:
        raise ValueError("Jistota musí být číslo od 0 do 1.")

    values = {}
    for api_name, column_name in ASSESSMENT_FIELDS.items():
        value = str(payload[api_name]).strip()
        if not value:
            raise ValueError(f"Pole {api_name} nesmí být prázdné.")
        values[column_name] = value

    with connect(readonly=False) as conn:
        cursor = conn.execute(
            """
            UPDATE parcely
            SET
                stav_z_ortofota = ?,
                zaver = ?,
                uroven_zaveru = ?,
                jistota = ?,
                riziko = ?,
                indikator_pristupnosti = ?,
                indikator_zivotniho_prostredi = ?,
                indikator_geometrie = ?,
                nalez = ?,
                dalsi_krok = ?
            WHERE id_pripadu = ?
            """,
            (
                values["stav_z_ortofota"],
                VERDICT_LEVELS[verdict_level],
                verdict_level,
                confidence,
                risk,
                values["indikator_pristupnosti"],
                values["indikator_zivotniho_prostredi"],
                values["indikator_geometrie"],
                values["nalez"],
                values["dalsi_krok"],
                case_id,
            ),
        )
        conn.commit()
    if cursor.rowcount != 1:
        raise KeyError(case_id)
    return get_parcel(case_id)


def run_training() -> dict:
    if not PYTHON_BIN.exists():
        raise FileNotFoundError(f"Python virtualenv missing: {PYTHON_BIN}")
    result = subprocess.run(
        [str(PYTHON_BIN), str(TRAIN_SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return {
        "status": "hotovo",
        "run": get_ml_run(),
        "predictions": get_ml_predictions(),
        "training_samples": get_training_samples(),
        "log": json.loads(result.stdout),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ViagemParcelAnalyst/1.0"

    def send_error(self, code: int, message: Optional[str] = None, explain: Optional[str] = None) -> None:
        payload = {"error": message or self.responses.get(code, ("Error",))[0]}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/api/health":
                self.send_json({"ok": True, "database": str(DB_PATH), "parcel_count": get_stats()["parcel_count"]})
            elif path == "/api/parcels":
                self.send_json(get_parcels())
            elif path.startswith("/api/parcels/"):
                self.send_json(get_parcel(path.rsplit("/", 1)[-1].upper()))
            elif path == "/api/sources":
                self.send_json(get_sources())
            elif path == "/api/methodology":
                self.send_json(get_methodology())
            elif path == "/api/stats":
                self.send_json(get_stats())
            elif path == "/api/map-layers":
                self.send_json(get_map_layers())
            elif path == "/api/analytics":
                self.send_json(get_analytics())
            elif path == "/api/ml/run":
                self.send_json(get_ml_run())
            elif path == "/api/ml/predictions":
                self.send_json(get_ml_predictions())
            elif path.startswith("/api/ml/predictions/"):
                self.send_json(get_ml_prediction(path.rsplit("/", 1)[-1].upper()))
            elif path == "/api/training-samples":
                self.send_json(get_training_samples())
            elif path == "/api/atom-samples":
                self.send_json(get_atom_samples())
            elif path.startswith("/media/evidence/"):
                self.send_file(EVIDENCE_DIR, path.removeprefix("/media/evidence/"))
            else:
                relative = "index.html" if path in {"/", ""} else path.lstrip("/")
                self.send_file(STATIC_DIR, relative)
        except ValueError as exc:
            self.send_error(400, str(exc))
        except KeyError:
            self.send_error(404, "Not found")
        except FileNotFoundError:
            self.send_error(404, "File not found")
        except Exception as exc:
            self.send_error(500, str(exc))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/api/training-samples":
                self.send_json(create_training_sample(self.read_json()))
            elif path == "/api/ml/train":
                self.send_json(run_training())
            else:
                self.send_error(404, "Not found")
        except ValueError as exc:
            self.send_error(400, str(exc))
        except KeyError:
            self.send_error(404, "Not found")
        except FileNotFoundError:
            self.send_error(404, "File not found")
        except Exception as exc:
            self.send_error(500, str(exc))

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path.startswith("/api/training-samples/"):
                self.send_json(delete_training_sample(int(path.rsplit("/", 1)[-1])))
            else:
                self.send_error(404, "Not found")
        except ValueError as exc:
            self.send_error(400, str(exc))
        except KeyError:
            self.send_error(404, "Not found")
        except Exception as exc:
            self.send_error(500, str(exc))

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        parts = path.strip("/").split("/")
        try:
            if len(parts) == 4 and parts[:2] == ["api", "parcels"] and parts[3] == "assessment":
                case_id = parts[2].upper()
                self.send_json(update_assessment(case_id, self.read_json()))
            else:
                self.send_error(404, "Not found")
        except ValueError as exc:
            self.send_error(400, str(exc))
        except KeyError:
            self.send_error(404, "Not found")
        except Exception as exc:
            self.send_error(500, str(exc))

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Neplatné JSON tělo požadavku.") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON tělo požadavku musí být objekt.")
        return payload

    def send_json(self, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, root: pathlib.Path, relative: str) -> None:
        target = (root / relative).resolve()
        if root.resolve() not in target.parents and target != root.resolve():
            raise FileNotFoundError(relative)
        if not target.is_file():
            raise FileNotFoundError(relative)
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    host = "127.0.0.1"
    port = 8765
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Viagem Parcel Analyst running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
