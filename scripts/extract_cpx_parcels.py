import csv
import pathlib
import sys
import zipfile
import xml.sax
from typing import Optional


def local_name(name: str) -> str:
    return name.rsplit(":", 1)[-1]


def href_tail(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.rstrip("/").rsplit("/", 1)[-1]


class ParcelHandler(xml.sax.ContentHandler):
    def __init__(self, source_zip: str, xml_name: str, rows: list[dict[str, str]]):
        super().__init__()
        self.source_zip = source_zip
        self.xml_name = xml_name
        self.rows = rows
        self.stack: list[str] = []
        self.record: Optional[dict[str, str]] = None
        self.text_target: Optional[str] = None
        self.text_parts: list[str] = []

    def startElement(self, name: str, attrs: xml.sax.xmlreader.AttributesImpl) -> None:
        tag = local_name(name)
        self.stack.append(tag)

        if tag == "CadastralParcel":
            self.record = {
                "source_zip": self.source_zip,
                "source_xml": self.xml_name,
                "gml_id": attrs.get("gml:id", ""),
                "area_m2": "",
                "label": "",
                "national_ref": "",
                "administrative_unit": "",
                "zoning": "",
                "land_type": "",
                "land_use": "",
                "reference_x_sjtsk": "",
                "reference_y_sjtsk": "",
            }
            return

        if self.record is None:
            return

        if tag == "administrativeUnit":
            self.record["administrative_unit"] = attrs.get("xlink:title", "")
        elif tag == "zoning":
            self.record["zoning"] = attrs.get("xlink:title", "")
        elif tag == "landType":
            self.record["land_type"] = href_tail(attrs.get("xlink:href"))
        elif tag == "landUse":
            self.record["land_use"] = href_tail(attrs.get("xlink:href"))
        elif tag in {"areaValue", "label", "nationalCadastralReference", "pos"}:
            if tag != "pos" or "referencePoint" in self.stack:
                self.text_target = tag
                self.text_parts = []

    def characters(self, content: str) -> None:
        if self.text_target:
            self.text_parts.append(content)

    def endElement(self, name: str) -> None:
        tag = local_name(name)

        if self.record is not None and self.text_target == tag:
            value = "".join(self.text_parts).strip()
            if tag == "areaValue":
                self.record["area_m2"] = value
            elif tag == "label":
                self.record["label"] = value
            elif tag == "nationalCadastralReference":
                self.record["national_ref"] = value
            elif tag == "pos" and value:
                parts = value.split()
                if len(parts) >= 2:
                    self.record["reference_x_sjtsk"] = parts[0]
                    self.record["reference_y_sjtsk"] = parts[1]
            self.text_target = None
            self.text_parts = []

        if tag == "CadastralParcel" and self.record is not None:
            self.rows.append(self.record)
            self.record = None

        self.stack.pop()


def parse_zip(path: pathlib.Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(path) as archive:
        xml_names = [name for name in archive.namelist() if name.lower().endswith(".xml")]
        if len(xml_names) != 1:
            raise RuntimeError(f"{path}: expected one XML file, got {xml_names}")
        xml_name = xml_names[0]
        parser = xml.sax.make_parser()
        parser.setFeature(xml.sax.handler.feature_namespaces, False)
        parser.setContentHandler(ParcelHandler(path.name, xml_name, rows))
        with archive.open(xml_name) as source:
            parser.parse(source)
    return rows


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: extract_cpx_parcels.py output.csv cpx.zip [cpx.zip ...]")

    output = pathlib.Path(sys.argv[1])
    rows: list[dict[str, str]] = []
    for raw in sys.argv[2:]:
        rows.extend(parse_zip(pathlib.Path(raw)))

    fieldnames = [
        "source_zip",
        "source_xml",
        "gml_id",
        "area_m2",
        "label",
        "national_ref",
        "administrative_unit",
        "zoning",
        "land_type",
        "land_use",
        "reference_x_sjtsk",
        "reference_y_sjtsk",
    ]
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} parcels to {output}")


if __name__ == "__main__":
    main()
