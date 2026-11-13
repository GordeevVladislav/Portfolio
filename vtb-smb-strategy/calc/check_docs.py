#!/usr/bin/env python3
"""Проверяет, что ключевые цифры модели (calc/key_figures.json) совпадают с цифрами в README и docs/.

Запуск после python3 calc/model.py:  python3 calc/check_docs.py
Код возврата 1, если какая-либо цифра в документе устарела.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = json.loads((ROOT / "calc" / "key_figures.json").read_text(encoding="utf-8"))

# файл -> ключи, значения которых должны встречаться в тексте дословно
EXPECT = {
    "README.md": ["start_avg", "avg_segment_m18", "avg_base_after", "covered_clients", "extra_products",
                  "core_total", "total_low", "total_high", "core_existing", "nonbank_existing",
                  "acq_existing_low", "acq_existing_high", "bank_target", "manager_share_time"],
    "docs/04-trajectory-implementation.md": ["avg_segment_m18", "avg_base_after", "start_avg", "manager_share_time"],
    "docs/05-economics-risks.md": ["core_existing", "nonbank_existing", "acq_existing_low",
                                   "acq_existing_high", "core_new_10", "total_low", "total_high"],
}

bad = 0
for rel, keys in EXPECT.items():
    text = (ROOT / rel).read_text(encoding="utf-8")
    for k in keys:
        if KEY[k] not in text:
            bad += 1
            print(f"РАСХОЖДЕНИЕ: {rel}: нет значения {k} = {KEY[k]}")
print("Все ключевые цифры совпадают." if not bad else f"Расхождений: {bad}")
sys.exit(1 if bad else 0)
