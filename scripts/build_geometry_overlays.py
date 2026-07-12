import csv
import pathlib
import zipfile
import xml.etree.ElementTree as ET
from typing import Optional

from PIL import Image, ImageDraw


ROOT = pathlib.Path(__file__).resolve().parents[1]
SELECTED_PATH = ROOT / "data" / "derived" / "selected_parcels.csv"
RAW_CPX_DIR = ROOT / "data" / "raw" / "cpx"
EVIDENCE_DIR = ROOT / "reports" / "evidence"
OUTPUT_DIR = ROOT / "reports" / "evidence"
MINIMUM_EVIDENCE_SPAN_M = 1000.0
EVIDENCE_PADDING_RATIO = 0.08


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> Optional[str]:
    for child in element.iter():
        if local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def geometry_pos_lists(parcel: ET.Element) -> list[list[tuple[float, float]]]:
    rings: list[list[tuple[float, float]]] = []
    inside_geometry = False
    for element in parcel.iter():
        name = local_name(element.tag)
        if name == "geometry":
            inside_geometry = True
        elif inside_geometry and name == "posList" and element.text:
            values = [float(value) for value in element.text.split()]
            if len(values) % 2 != 0:
                raise ValueError("odd coordinate count in CPX posList")
            rings.append(list(zip(values[0::2], values[1::2])))
    if not rings:
        raise ValueError(f"no polygon rings found for {child_text(parcel, 'nationalCadastralReference')}")
    return rings


def find_parcel_rings(national_ref: str) -> list[list[tuple[float, float]]]:
    ku_code = national_ref.split("-", 1)[0]
    matches = list(RAW_CPX_DIR.glob(f"{ku_code}_*.zip"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one CPX ZIP for {ku_code}, got {matches}")

    with zipfile.ZipFile(matches[0]) as archive:
        xml_names = [name for name in archive.namelist() if name.endswith(".xml")]
        if len(xml_names) != 1:
            raise RuntimeError(f"{matches[0]}: expected one XML file")
        with archive.open(xml_names[0]) as source:
            for _, element in ET.iterparse(source, events=("end",)):
                if local_name(element.tag) != "CadastralParcel":
                    continue
                if child_text(element, "nationalCadastralReference") == national_ref:
                    return geometry_pos_lists(element)
                element.clear()

    raise LookupError(f"parcel not found in CPX: {national_ref}")


def pixel(coord: tuple[float, float], bbox: tuple[float, float, float, float], size: tuple[int, int]) -> tuple[float, float]:
    x, y = coord
    min_x, min_y, max_x, max_y = bbox
    width, height = size
    px = (x - min_x) / (max_x - min_x) * width
    py = (max_y - y) / (max_y - min_y) * height
    return px, py


def evidence_bbox(rings: list[list[tuple[float, float]]]) -> tuple[float, float, float, float]:
    points = [point for ring in rings for point in ring]
    if not points:
        raise ValueError("cannot build evidence bbox without geometry points")
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    geometry_span = max(max_x - min_x, max_y - min_y)
    span = max(MINIMUM_EVIDENCE_SPAN_M, geometry_span * (1 + EVIDENCE_PADDING_RATIO))
    radius = span / 2
    return center_x - radius, center_y - radius, center_x + radius, center_y + radius


def draw_overlay(row: dict[str, str], rings: list[list[tuple[float, float]]]) -> pathlib.Path:
    safe_ref = row["national_ref"].replace("/", "-")
    ortho_path = EVIDENCE_DIR / f"{row['case_id']}_{safe_ref}_ortho.png"
    if not ortho_path.exists():
        raise FileNotFoundError(ortho_path)

    bbox = evidence_bbox(rings)

    image = Image.open(ortho_path).convert("RGBA")
    boundary = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(boundary)
    for ring in rings:
        points = [pixel(point, bbox, image.size) for point in ring]
        if len(points) >= 3:
            draw.polygon(points, fill=(46, 138, 154, 38))
            draw.line(points, fill=(255, 255, 255, 230), width=8, joint="curve")
            draw.line(points, fill=(21, 95, 108, 255), width=4, joint="curve")

    draw.rectangle((14, 14, 275, 58), fill=(255, 255, 255, 210), outline=(21, 95, 108, 210), width=2)
    draw.text((26, 24), f"CPX hranice parcely {row['national_ref']}", fill=(21, 65, 56, 255))

    output = OUTPUT_DIR / f"{row['case_id']}_{safe_ref}_overlay.png"
    Image.alpha_composite(image, boundary).save(output)
    return output


def main() -> None:
    if not SELECTED_PATH.exists():
        raise FileNotFoundError(SELECTED_PATH)

    with SELECTED_PATH.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rings = find_parcel_rings(row["national_ref"])
            output = draw_overlay(row, rings)
            print(f"wrote {output}")


if __name__ == "__main__":
    main()
