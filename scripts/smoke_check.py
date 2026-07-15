import contextlib
import json
import pathlib
import shutil
import sqlite3
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app.server as app_server
from scripts import fetch_wms_evidence
from scripts.build_geometry_overlays import evidence_bbox, find_parcel_rings


def get_json(base_url: str, path: str) -> object:
    with urllib.request.urlopen(f"{base_url}{path}", timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"{path} returned {response.status}")
        return json.loads(response.read().decode("utf-8"))


def get_text(base_url: str, path: str) -> str:
    with urllib.request.urlopen(f"{base_url}{path}", timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"{path} returned {response.status}")
        return response.read().decode("utf-8")


def send_json(base_url: str, path: str, payload: dict, method: str = "POST", timeout: int = 10) -> object:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"{path} returned {response.status}")
        return json.loads(response.read().decode("utf-8"))


def send_json_error(base_url: str, path: str, payload: dict, expected_status: int, method: str = "POST") -> dict:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as error:
        if error.code != expected_status:
            raise RuntimeError(f"{path} returned {error.code}, expected {expected_status}") from error
        return json.loads(error.read().decode("utf-8"))
    raise RuntimeError(f"{path} did not return expected error {expected_status}")


def delete_json(base_url: str, path: str) -> object:
    request = urllib.request.Request(f"{base_url}{path}", method="DELETE")
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"{path} returned {response.status}")
        return json.loads(response.read().decode("utf-8"))


class SmokeHandler(app_server.Handler):
    def log_message(self, format: str, *args: object) -> None:
        return


def copy_database(source_path: pathlib.Path, target_path: pathlib.Path) -> None:
    with sqlite3.connect(f"file:{source_path}?mode=ro", uri=True) as source:
        with sqlite3.connect(target_path) as target:
            source.backup(target)


@contextlib.contextmanager
def isolated_server(db_path: pathlib.Path, model_path: pathlib.Path, train_script: pathlib.Path):
    original_paths = (app_server.DB_PATH, app_server.MODEL_PATH, app_server.TRAIN_SCRIPT)
    server = None
    thread = None
    try:
        app_server.DB_PATH = db_path
        app_server.MODEL_PATH = model_path
        app_server.TRAIN_SCRIPT = train_script
        server = ThreadingHTTPServer(("127.0.0.1", 0), SmokeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=5)
        app_server.DB_PATH, app_server.MODEL_PATH, app_server.TRAIN_SCRIPT = original_paths


def main() -> None:
    if not callable(fetch_wms_evidence.main):
        raise RuntimeError("WMS evidence script is not importable")

    forest_bbox = evidence_bbox(find_parcel_rings("669296-676/1"))
    if forest_bbox[2] - forest_bbox[0] <= 1000:
        raise RuntimeError("large-parcel evidence bbox is still clipped to one kilometre")

    with tempfile.TemporaryDirectory(prefix="viagem-analytics-smoke-") as temp_dir:
        temp_root = pathlib.Path(temp_dir)
        temp_db = temp_root / "data" / "app.sqlite"
        temp_model = temp_root / "ml" / "parcel_atom_mlp.pt"
        temp_train_script = temp_root / "ml" / "train_pytorch.py"
        temp_db.parent.mkdir(parents=True)
        temp_model.parent.mkdir(parents=True)
        copy_database(app_server.DB_PATH, temp_db)
        shutil.copy2(app_server.MODEL_PATH, temp_model)
        shutil.copy2(app_server.TRAIN_SCRIPT, temp_train_script)

        with isolated_server(temp_db, temp_model, temp_train_script) as base_url:
            health = get_json(base_url, "/api/health")
            parcels = get_json(base_url, "/api/parcels")
            parcel = get_json(base_url, "/api/parcels/A")
            stats = get_json(base_url, "/api/stats")
            map_layers = get_json(base_url, "/api/map-layers")
            analytics = get_json(base_url, "/api/analytics")
            sources = get_json(base_url, "/api/sources")
            methodology = get_json(base_url, "/api/methodology")
            ml_run = get_json(base_url, "/api/ml/run")
            ml_predictions = get_json(base_url, "/api/ml/predictions")
            ml_prediction = get_json(base_url, "/api/ml/predictions/A")
            atom_samples = get_json(base_url, "/api/atom-samples")
            sample = send_json(base_url, "/api/training-samples", {"case_id": "A", "land_type": "ArableGround", "note": "Smoke test"})
            samples = get_json(base_url, "/api/training-samples")
            delete_json(base_url, f"/api/training-samples/{sample['id']}")
            samples_after_delete = get_json(base_url, "/api/training-samples")
            invalid_atom = send_json_error(
                base_url,
                "/api/training-samples",
                {"source": "atom", "atom_sample_id": "ATOM-0006", "land_type": "Forest", "note": "Smoke validation"},
                400,
            )
            assessment_payload = {
                "verdict_level": "mismatch",
                "confidence": 0.4,
                "risk": "Vysoké",
                "observed_state": parcel["observed_state"],
                "finding": f"{parcel['finding']} Smoke test.",
                "action": parcel["action"],
                "accessibility_indicator": parcel["accessibility_indicator"],
                "environment_indicator": parcel["environment_indicator"],
                "geometry_indicator": parcel["geometry_indicator"],
            }
            updated_parcel = send_json(base_url, "/api/parcels/A/assessment", assessment_payload, method="PUT")
            invalid_assessment = send_json_error(
                base_url,
                "/api/parcels/A/assessment",
                {**assessment_payload, "confidence": 2},
                400,
                method="PUT",
            )
            training_result = send_json(base_url, "/api/ml/train", {}, timeout=180)
            index_html = get_text(base_url, "/")
            app_js = get_text(base_url, "/app.js")
            styles_css = get_text(base_url, "/styles.css")
            evidence_url = parcel["ortho_image"]
            with urllib.request.urlopen(f"{base_url}{evidence_url}", timeout=10) as response:
                evidence_type = response.headers.get_content_type()
                evidence_size = len(response.read())

            if health["ok"] is not True or health["parcel_count"] != 5:
                raise RuntimeError("health endpoint did not verify the parcel database")
            if len(parcels) != 5 or parcel["case_id"] != "A" or stats["parcel_count"] != 5:
                raise RuntimeError("parcel endpoints are incomplete")
            if len(map_layers["parcels"]) != 5 or not map_layers["base_layers"]:
                raise RuntimeError("map layers are incomplete")
            if len(analytics["outputs"]) != 5 or not sources or not methodology["useful"]:
                raise RuntimeError("analytics, source, or methodology endpoints are incomplete")
            if ml_run["model_name"] != "ParcelAtomMLP" or len(ml_predictions) != 5 or ml_prediction["case_id"] != "A":
                raise RuntimeError("ML outputs are incomplete")
            if len(atom_samples) != 480 or ml_run["parameters"]["atom_sample_count"] != 480:
                raise RuntimeError("ATOM samples are incomplete")
            if len(ml_predictions[0]["probabilities"]) != 8:
                raise RuntimeError("ML probability classes are incomplete")
            if ml_run["model_artifact_exists"] is not True:
                raise RuntimeError("trained model artifact is missing")
            if not any(item["id"] == sample["id"] for item in samples):
                raise RuntimeError("training sample add failed")
            if any(item["id"] == sample["id"] for item in samples_after_delete):
                raise RuntimeError("training sample delete failed")
            if "ATOM vzorek musí používat druh pozemku z ČÚZK." not in invalid_atom["error"]:
                raise RuntimeError("training sample validation did not return the expected JSON error")
            if updated_parcel["finding"] != assessment_payload["finding"] or updated_parcel["verdict"] != "Pravděpodobný nesoulad":
                raise RuntimeError("analyst assessment update failed")
            if "Jistota musí být číslo od 0 do 1." not in invalid_assessment["error"]:
                raise RuntimeError("analyst assessment validation failed")
            if training_result["run"]["model_name"] != "ParcelAtomMLP" or len(training_result["predictions"]) != 5:
                raise RuntimeError("PyTorch API training failed")
            if evidence_type != "image/png" or evidence_size < 1000:
                raise RuntimeError("evidence media endpoint is incomplete")
            if "OpenStreetMap kontext" not in index_html or "Mapová stránka" not in index_html:
                raise RuntimeError("mapové moduly rozhraní chybí")
            if "assessmentForm" not in index_html or "putJson" not in app_js or ".assessment-form" not in styles_css:
                raise RuntimeError("panel analytika nebo jeho klientská logika chybí")
            if "helpTooltip" not in index_html or "showHelpTooltip" not in app_js or "z-index: 2000" not in styles_css:
                raise RuntimeError("viewport tooltip layer is incomplete")
            if ".analysis-pane .training-base-grid" not in styles_css or "@media (min-width: 1181px)" not in styles_css:
                raise RuntimeError("narrow analytics-column grid rules are incomplete")
            if "mlPredictionTable" not in index_html or "mlRunGrid" not in index_html or "atomSampleSummary" not in index_html:
                raise RuntimeError("panel PyTorch v rozhraní chybí")

            print("smoke check passed")


if __name__ == "__main__":
    main()
