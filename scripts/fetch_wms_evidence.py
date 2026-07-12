import csv
import pathlib
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_geometry_overlays import evidence_bbox, find_parcel_rings, pixel


OUTPUT_DIR = ROOT / "reports" / "evidence"
SELECTED = ROOT / "data" / "derived" / "selected_parcels.csv"


def build_url(base: str, params: dict[str, str]) -> str:
    return f"{base}?{urllib.parse.urlencode(params)}"


def fetch(url: str, output: pathlib.Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    output.write_bytes(data)


def annotate_crosshair(
    path: pathlib.Path,
    reference_point: tuple[float, float],
    bbox: tuple[float, float, float, float],
) -> None:
    image = Image.open(path).convert("RGBA")
    draw = ImageDraw.Draw(image)
    cx, cy = pixel(reference_point, bbox, image.size)
    color = (220, 0, 0, 255)
    draw.line((cx - 18, cy, cx - 5, cy), fill=color, width=3)
    draw.line((cx + 5, cy, cx + 18, cy), fill=color, width=3)
    draw.line((cx, cy - 18, cx, cy - 5), fill=color, width=3)
    draw.line((cx, cy + 5, cx, cy + 18), fill=color, width=3)
    draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), outline=color, width=2)
    image.save(path)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ortho_base = "https://ags.cuzk.cz/arcgis1/services/ORTOFOTO/MapServer/WMSServer"
    kn_base = "https://services.cuzk.gov.cz/wms/local-km-wms.asp"

    with SELECTED.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            case_id = row["case_id"]
            x = float(row["reference_x_sjtsk"])
            y = float(row["reference_y_sjtsk"])
            rings = find_parcel_rings(row["national_ref"])
            bbox_values = evidence_bbox(rings)
            bbox = ",".join(str(value) for value in bbox_values)

            common = {
                "SERVICE": "WMS",
                "VERSION": "1.1.1",
                "REQUEST": "GetMap",
                "STYLES": "",
                "SRS": "EPSG:5514",
                "BBOX": bbox,
                "WIDTH": "1000",
                "HEIGHT": "1000",
                "FORMAT": "image/png",
            }

            ortho_path = OUTPUT_DIR / f"{case_id}_{row['national_ref']}_ortho.png".replace("/", "-")
            ortho_url = build_url(ortho_base, {**common, "LAYERS": "0"})
            fetch(ortho_url, ortho_path)
            annotate_crosshair(ortho_path, (x, y), bbox_values)

            kn_path = OUTPUT_DIR / f"{case_id}_{row['national_ref']}_kn.png".replace("/", "-")
            kn_url = build_url(kn_base, {**common, "LAYERS": "KN", "BGCOLOR": "0xFFFFFF", "TRANSPARENT": "FALSE"})
            fetch(kn_url, kn_path)
            annotate_crosshair(kn_path, (x, y), bbox_values)

            print(f"wrote {ortho_path} and {kn_path}")


if __name__ == "__main__":
    main()
