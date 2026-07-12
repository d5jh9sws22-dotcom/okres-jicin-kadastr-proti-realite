import pandas as pd


def main() -> None:
    df = pd.read_csv("data/derived/cpx_parcels.csv")
    print(df.groupby("land_type").size().sort_values(ascending=False).to_string())
    print()

    cols = [
        "zoning",
        "label",
        "national_ref",
        "area_m2",
        "land_type",
        "land_use",
        "reference_x_sjtsk",
        "reference_y_sjtsk",
    ]
    for land_type in [
        "ArableGround",
        "Grassland",
        "Forest",
        "WaterArea",
        "OtherArea",
        "BuiltUpArea",
        "Garden",
        "Orchard",
    ]:
        print(f"--- {land_type}")
        candidates = df[df["land_type"].eq(land_type)].sort_values("area_m2", ascending=False)
        print(candidates[cols].head(12).to_string(index=False))
        print()


if __name__ == "__main__":
    main()
