import json
import math
import pathlib
import random
import sqlite3
from datetime import datetime, timezone

import torch
import torch.nn as nn


ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "app.sqlite"
MODEL_PATH = ROOT / "ml" / "parcel_atom_mlp.pt"

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

PARAMETERS = {
    "seed": 20260709,
    "epochs": 120,
    "learning_rate": 0.018,
    "hidden_width": 64,
    "dropout_probability": 0.18,
    "label_smoothing": 0.04,
    "temperature": 1.18,
    "batch_size": 64,
    "atom_sample_count": 480,
    "numeric_noise_sigma": 0.025,
    "feature_dropout_probability": 0.08,
    "area_log_scale": True,
}


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"database not found: {DB_PATH}. Run scripts/build_app_db.py first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}


def load_parcels() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id_pripadu AS case_id,
                katastralni_uzemi AS zoning,
                cislo_parcely AS label,
                vymera_m2 AS area_m2,
                druh_pozemku AS land_type,
                zpusob_vyuziti AS land_use,
                souradnice_x_sjtsk AS reference_x_sjtsk,
                souradnice_y_sjtsk AS reference_y_sjtsk
            FROM parcely
            ORDER BY id_pripadu
            """
        ).fetchall()
    if not rows:
        raise RuntimeError("no parcels found in data/app.sqlite")
    return [row_to_dict(row) for row in rows]


def load_atom_samples() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id_atom_vzorku AS atom_sample_id,
                katastralni_uzemi AS zoning,
                cislo_parcely AS label,
                vymera_m2 AS area_m2,
                druh_pozemku AS land_type,
                zpusob_vyuziti AS land_use,
                souradnice_x_sjtsk AS reference_x_sjtsk,
                souradnice_y_sjtsk AS reference_y_sjtsk
            FROM atomove_vzorky
            ORDER BY id_atom_vzorku
            """
        ).fetchall()
    samples = [row_to_dict(row) for row in rows]
    if len(samples) != PARAMETERS["atom_sample_count"]:
        raise RuntimeError(f"expected {PARAMETERS['atom_sample_count']} ATOM samples, got {len(samples)}")
    return samples


def load_training_samples() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                tv.typ_zdroje AS source_type,
                tv.id_pripadu AS case_id,
                tv.id_atom_vzorku AS atom_sample_id,
                tv.stitek_druhu AS land_type,
                COALESCE(av.katastralni_uzemi, p.katastralni_uzemi) AS zoning,
                COALESCE(av.cislo_parcely, p.cislo_parcely) AS label,
                COALESCE(av.vymera_m2, p.vymera_m2) AS area_m2,
                COALESCE(av.zpusob_vyuziti, p.zpusob_vyuziti) AS land_use,
                COALESCE(av.souradnice_x_sjtsk, p.souradnice_x_sjtsk) AS reference_x_sjtsk,
                COALESCE(av.souradnice_y_sjtsk, p.souradnice_y_sjtsk) AS reference_y_sjtsk
            FROM treninkove_vzorky tv
            LEFT JOIN atomove_vzorky av ON av.id_atom_vzorku = tv.id_atom_vzorku
            LEFT JOIN parcely p ON p.id_pripadu = tv.id_pripadu
            ORDER BY tv.id
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def validate_land_types(rows: list[dict]) -> None:
    unsupported = sorted({row["land_type"] for row in rows} - set(LAND_LABELS))
    if unsupported:
        raise RuntimeError(f"unsupported land type classes: {unsupported}")


def category_values(rows: list[dict], key: str, limit: int) -> list[str]:
    counts = {}
    for row in rows:
        value = row[key] or ""
        counts[value] = counts.get(value, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [value for value, _ in ranked[:limit]]


def base_numeric(row: dict) -> list[float]:
    area = max(float(row["area_m2"]), 1.0)
    label = str(row["label"])
    land_use = row["land_use"] or ""
    return [
        math.log(area),
        1.0 if label.startswith("st.") else 0.0,
        1.0 if "/" in label else 0.0,
        1.0 if land_use else 0.0,
        float(row["reference_x_sjtsk"]) / 1_000_000.0,
        float(row["reference_y_sjtsk"]) / 1_000_000.0,
    ]


class FeatureEncoder:
    def __init__(self, rows: list[dict]):
        self.land_use_values = category_values(rows, "land_use", 28)
        self.zoning_values = category_values(rows, "zoning", 16)
        numeric = torch.tensor([base_numeric(row) for row in rows], dtype=torch.float32)
        self.mean = numeric.mean(dim=0)
        self.std = numeric.std(dim=0).clamp_min(1e-4)

    def encode(self, row: dict) -> torch.Tensor:
        numeric = (torch.tensor(base_numeric(row), dtype=torch.float32) - self.mean) / self.std
        land_use = row["land_use"] or ""
        zoning = row["zoning"] or ""
        land_use_bits = [1.0 if land_use == value else 0.0 for value in self.land_use_values]
        zoning_bits = [1.0 if zoning == value else 0.0 for value in self.zoning_values]
        return torch.cat([numeric, torch.tensor(land_use_bits + zoning_bits, dtype=torch.float32)])

    def to_payload(self) -> dict:
        return {
            "land_use_values": self.land_use_values,
            "zoning_values": self.zoning_values,
            "mean": self.mean.tolist(),
            "std": self.std.tolist(),
        }


class AtomDataset(torch.utils.data.Dataset):
    def __init__(self, features: torch.Tensor, labels: torch.Tensor, seed: int):
        self.features = features
        self.labels = labels
        self.seed = seed

    def __len__(self) -> int:
        return self.features.shape[0]

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        generator = torch.Generator().manual_seed(self.seed + index * 7919)
        x = self.features[index].clone()
        noise = torch.randn(x.shape, generator=generator) * PARAMETERS["numeric_noise_sigma"]
        mask = torch.rand(x.shape, generator=generator) > PARAMETERS["feature_dropout_probability"]
        return (x + noise) * mask.float(), self.labels[index]


class ParcelAtomMLP(nn.Module):
    def __init__(self, input_width: int, class_count: int):
        super().__init__()
        hidden = PARAMETERS["hidden_width"]
        dropout = PARAMETERS["dropout_probability"]
        self.net = nn.Sequential(
            nn.Linear(input_width, hidden),
            nn.LayerNorm(hidden),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, class_count),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def entropy(probabilities: torch.Tensor) -> float:
    probs = probabilities.clamp_min(1e-9)
    return float(-(probs * probs.log()).sum().item())


def explanation(official: str, predicted: str, confidence: float, ent: float) -> str:
    if ent > 1.6 or confidence < 0.5:
        if official == predicted:
            return "ATOM model vrací stejnou třídu jako katastr, ale s vyšší nejistotou; parcelu má dál potvrdit analytik nad ortofotem a CPX hranicí."
        return "ATOM model je nejistý a neshoduje se s katastrem; jde o kandidáta na ruční kontrolu, ne o automatický právní závěr."
    if official == predicted:
        return "Model trénovaný na ATOM/CPX atributech se shoduje s oficiálním druhem; výsledek podporuje, ale nenahrazuje ruční kontrolu reality."
    return f"Model z ATOM/CPX atributů preferuje {LAND_LABELS[predicted]} místo {LAND_LABELS[official]}; ověřit proti ortofotu a dalším vrstvám."


def main() -> None:
    torch.manual_seed(PARAMETERS["seed"])
    random.seed(PARAMETERS["seed"])

    parcels = load_parcels()
    atom_samples = load_atom_samples()
    extra_samples = load_training_samples()
    training_rows = [*atom_samples, *parcels, *extra_samples]
    validate_land_types(training_rows)

    classes = sorted({row["land_type"] for row in training_rows})
    class_to_index = {land_type: index for index, land_type in enumerate(classes)}
    encoder = FeatureEncoder(training_rows)

    features = torch.stack([encoder.encode(row) for row in training_rows])
    labels = torch.tensor([class_to_index[row["land_type"]] for row in training_rows], dtype=torch.long)
    dataset = AtomDataset(features, labels, PARAMETERS["seed"])
    loader = torch.utils.data.DataLoader(dataset, batch_size=PARAMETERS["batch_size"], shuffle=True)

    model = ParcelAtomMLP(input_width=features.shape[1], class_count=len(classes))
    optimizer = torch.optim.AdamW(model.parameters(), lr=PARAMETERS["learning_rate"], weight_decay=0.001)
    criterion = nn.CrossEntropyLoss(label_smoothing=PARAMETERS["label_smoothing"])

    final_loss = math.nan
    final_accuracy = math.nan
    for _ in range(PARAMETERS["epochs"]):
        correct = 0
        seen = 0
        loss_total = 0.0
        model.train()
        for batch_features, target in loader:
            optimizer.zero_grad()
            logits = model(batch_features)
            loss = criterion(logits, target)
            loss.backward()
            optimizer.step()
            loss_total += float(loss.item()) * batch_features.shape[0]
            correct += int((logits.argmax(dim=1) == target).sum().item())
            seen += batch_features.shape[0]
        final_loss = loss_total / seen
        final_accuracy = correct / seen

    model.eval()
    predictions = []
    with torch.no_grad():
        for row in parcels:
            x = encoder.encode(row).unsqueeze(0)
            logits = model(x)[0] / PARAMETERS["temperature"]
            probabilities = torch.softmax(logits, dim=0)
            predicted_index = int(probabilities.argmax().item())
            predicted_land_type = classes[predicted_index]
            confidence = float(probabilities[predicted_index].item())
            ent = entropy(probabilities)
            probs_by_class = {land_type: float(probabilities[index].item()) for index, land_type in enumerate(classes)}
            agreement = "agree" if predicted_land_type == row["land_type"] and confidence >= 0.5 and ent <= 1.6 else "review"
            predictions.append(
                {
                    "case_id": row["case_id"],
                    "predicted_land_type": predicted_land_type,
                    "predicted_label": LAND_LABELS[predicted_land_type],
                    "confidence": confidence,
                    "entropy": ent,
                    "agreement": agreement,
                    "probabilities": json.dumps(probs_by_class, ensure_ascii=False),
                    "explanation": explanation(row["land_type"], predicted_land_type, confidence, ent),
                }
            )

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "classes": classes,
            "encoder": encoder.to_payload(),
            "parameters": PARAMETERS,
            "final_loss": final_loss,
            "final_accuracy": final_accuracy,
        },
        MODEL_PATH,
    )

    with connect() as conn:
        conn.execute("DELETE FROM predikce_modelu")
        conn.execute("DELETE FROM behy_modelu")
        conn.execute(
            """
            INSERT INTO behy_modelu (
                id, nazev_modelu, knihovna, verze_torch, natrenovano_dne, pocet_vzorku,
                epochy, finalni_loss, finalni_presnost, parametry, poznamka
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ParcelAtomMLP",
                "PyTorch",
                torch.__version__,
                datetime.now(timezone.utc).isoformat(),
                len(training_rows),
                PARAMETERS["epochs"],
                final_loss,
                final_accuracy,
                json.dumps(PARAMETERS, ensure_ascii=False),
                f"Model je trénovaný na {len(atom_samples)} reálných ATOM/CPX parcelách z ČÚZK, 5 analytických parcelách a {len(extra_samples)} ručně vybraných vzorcích.",
            ),
        )
        conn.executemany(
            """
            INSERT INTO predikce_modelu (
                id_pripadu, predikovany_druh, predikovany_popis, jistota, entropie,
                shoda, pravdepodobnosti, vysvetleni
            ) VALUES (
                :case_id, :predicted_land_type, :predicted_label, :confidence, :entropy,
                :agreement, :probabilities, :explanation
            )
            """,
            predictions,
        )
        conn.commit()

    print(
        json.dumps(
            {
                "model": str(MODEL_PATH),
                "torch": torch.__version__,
                "training_samples": len(training_rows),
                "atom_samples": len(atom_samples),
                "manual_samples": len(extra_samples),
                "epochs": PARAMETERS["epochs"],
                "final_loss": round(final_loss, 4),
                "final_accuracy": round(final_accuracy, 4),
                "predictions": predictions,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
