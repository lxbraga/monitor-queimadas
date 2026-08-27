"""Baixa o CSV diário de focos de queimadas do INPE para data/raw/.

Uso: python code/data_acquisition/fetch_inpe.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import requests

BASE_URL = (
    "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil"
)
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# O arquivo do dia pode ainda não ter sido publicado; recuamos até este limite.
MAX_LOOKBACK_DAYS = 5
TIMEOUT_SECONDS = 30


def daily_csv_url(day: date) -> str:
    return f"{BASE_URL}/focos_diario_br_{day.strftime('%Y%m%d')}.csv"


def fetch_latest_daily(raw_dir: Path = RAW_DIR) -> Path:
    """Baixa o CSV diário mais recente disponível e retorna o caminho salvo."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    for offset in range(MAX_LOOKBACK_DAYS + 1):
        day = date.today() - timedelta(days=offset)
        url = daily_csv_url(day)
        try:
            response = requests.get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            errors.append(f"{url}: {exc}")
            continue

        if response.status_code == 200 and response.content:
            destination = raw_dir / f"focos_diario_br_{day.strftime('%Y%m%d')}.csv"
            destination.write_bytes(response.content)
            return destination

        errors.append(f"{url}: HTTP {response.status_code}")

    raise RuntimeError(
        f"Nenhum CSV disponível nos últimos {MAX_LOOKBACK_DAYS} dias:\n"
        + "\n".join(errors)
    )


def main() -> int:
    print("Baixando focos de queimadas (INPE, CSV diário do Brasil)...")
    try:
        path = fetch_latest_daily()
    except RuntimeError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    line_count = sum(1 for _ in path.open(encoding="utf-8")) - 1
    print(f"Arquivo salvo em: {path}")
    print(f"Focos registrados: {line_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
