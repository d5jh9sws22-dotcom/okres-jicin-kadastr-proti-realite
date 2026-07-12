import sys
import zipfile
import xml.etree.ElementTree as ET


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: print_first_parcel.py path/to/cpx.zip")

    with zipfile.ZipFile(sys.argv[1]) as archive:
        with archive.open(archive.namelist()[0]) as source:
            for _, element in ET.iterparse(source, events=("end",)):
                if element.tag.endswith("CadastralParcel"):
                    print(ET.tostring(element, encoding="unicode")[:8000])
                    return

    raise SystemExit("no CadastralParcel element found")


if __name__ == "__main__":
    main()
