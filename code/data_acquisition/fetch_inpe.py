"""Baixa CSVs diários de focos de queimadas do INPE para data/raw/.

Uso: python code/data_acquisition/fetch_inpe.py [dias]
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


def fetch_day(day: date, raw_dir: Path = RAW_DIR) -> Path | None:
    """Baixa o CSV de um dia. Retorna o caminho salvo ou None se indisponível."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(daily_csv_url(day), timeout=TIMEOUT_SECONDS)
    except requests.RequestException:
        return None
    if response.status_code != 200 or not response.content:
        return None
    destination = raw_dir / f"focos_diario_br_{day.strftime('%Y%m%d')}.csv"
    destination.write_bytes(response.content)
    return destination


def fetch_latest_daily(raw_dir: Path = RAW_DIR) -> Path:
    """Baixa o CSV diário mais recente disponível e retorna o caminho salvo."""
    for offset in range(MAX_LOOKBACK_DAYS + 1):
        path = fetch_day(date.today() - timedelta(days=offset), raw_dir)
        if path:
            return path
    raise RuntimeError(
        f"Nenhum CSV disponível nos últimos {MAX_LOOKBACK_DAYS} dias."
    )


def fetch_last_days(days: int, raw_dir: Path = RAW_DIR) -> list[Path]:
    """Baixa os CSVs dos últimos dias e retorna os caminhos obtidos."""
    paths = []
    for offset in range(days + MAX_LOOKBACK_DAYS):
        path = fetch_day(date.today() - timedelta(days=offset), raw_dir)
        if path:
            paths.append(path)
        if len(paths) >= days:
            break
    if not paths:
        raise RuntimeError(
            f"Nenhum CSV disponível nos últimos {days + MAX_LOOKBACK_DAYS} dias."
        )
    return paths


def main() -> int:
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"Baixando focos de queimadas do INPE ({days} dia(s))...")
    try:
        paths = fetch_last_days(days)
    except RuntimeError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    for path in paths:
        line_count = sum(1 for _ in path.open(encoding="utf-8")) - 1
        print(f"{path.name}: {line_count} focos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
