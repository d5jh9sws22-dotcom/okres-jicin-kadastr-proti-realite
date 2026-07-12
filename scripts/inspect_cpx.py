import collections
import sys
import zipfile
import xml.etree.ElementTree as ET


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect_cpx.py path/to/cpx.zip")

    counts: collections.Counter[str] = collections.Counter()
    with zipfile.ZipFile(sys.argv[1]) as archive:
        with archive.open(archive.namelist()[0]) as source:
            for _, element in ET.iterparse(source, events=("end",)):
                counts[local_name(element.tag)] += 1
                element.clear()

    for name, count in counts.most_common(120):
        print(f"{name}\t{count}")


if __name__ == "__main__":
    main()
