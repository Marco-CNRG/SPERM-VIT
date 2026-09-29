"""Escritura de CSV de resumen y detalle."""

import csv
from pathlib import Path
from typing import Iterable
from collections import defaultdict

from .analysis import ImageSummary


def write_csv(path: Path, headers: list[str], rows: Iterable[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(output: Path, summaries: list[ImageSummary], detection_rows: list[dict],
                  red_threshold: float, confidence: float) -> None:
    summary_rows = [
        {
            "imagen": item.image,
            "espermatozoides_detectados": item.total,
            "vivos": item.vivos,
            "muertos": item.muertos,
            "porcentaje_vivos": round(item.porcentaje_vivos, 2),
            "porcentaje_muertos": round(item.porcentaje_muertos, 2),
        }
        for item in summaries
    ]
    total_objects = sum(item.total for item in summaries)
    total_vivos = sum(item.vivos for item in summaries)
    total_muertos = sum(item.muertos for item in summaries)
    general_row = {
        "imagenes_procesadas": len(summaries),
        "espermatozoides_detectados": total_objects,
        "vivos": total_vivos,
        "muertos": total_muertos,
        "porcentaje_vivos": round(100 * total_vivos / total_objects, 2) if total_objects else 0,
        "porcentaje_muertos": round(100 * total_muertos / total_objects, 2) if total_objects else 0,
        "umbral_muerto_porcentaje_rojo": red_threshold,
        "confianza_minima_yolo": confidence,
    }
    write_csv(output / "resumen_por_imagen.csv", list(summary_rows[0]) if summary_rows else [
        "imagen", "espermatozoides_detectados", "vivos", "muertos", "porcentaje_vivos", "porcentaje_muertos"
    ], summary_rows)

    # Cada imagen aporta sus conteos a su carpeta y a cada carpeta contenedora.
    # Así el CSV incluye los totales de hojas y los acumulados de carpetas padre.
    folder_totals = defaultdict(lambda: {"imagenes": 0, "total": 0, "vivos": 0, "muertos": 0})
    for item in summaries:
        if item.folder == ".":
            continue
        parts = Path(item.folder).parts
        for depth in range(1, len(parts) + 1):
            folder_name = str(Path(*parts[:depth]))
            totals = folder_totals[folder_name]
            totals["imagenes"] += 1
            totals["total"] += item.total
            totals["vivos"] += item.vivos
            totals["muertos"] += item.muertos
    folder_rows = []
    for folder_name in sorted(folder_totals):
        totals = folder_totals[folder_name]
        total = totals["total"]
        folder_rows.append({
            "carpeta": folder_name,
            "imagenes": totals["imagenes"],
            "espermatozoides_detectados": total,
            "vivos": totals["vivos"],
            "muertos": totals["muertos"],
            "porcentaje_vivos": round(100 * totals["vivos"] / total, 2) if total else 0,
            "porcentaje_muertos": round(100 * totals["muertos"] / total, 2) if total else 0,
        })
    write_csv(output / "resumen_por_carpeta.csv", [
        "carpeta", "imagenes", "espermatozoides_detectados", "vivos", "muertos", "porcentaje_vivos", "porcentaje_muertos"
    ], folder_rows)
    write_csv(output / "resumen_general.csv", list(general_row), [general_row])
    write_csv(output / "detalle_detecciones.csv", [
        "imagen", "espermatozoide", "etiqueta", "porcentaje_pixeles_rojos", "porcentaje_pixeles_azules",
        "pixeles_rojos", "pixeles_azules", "pixeles_color_objeto", "confianza_yolo", "x1", "y1", "x2", "y2",
    ], detection_rows)
