"""Interfaz de línea de comandos de la aplicación."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from .analysis import ImageSummary, ViabilityAnalyzer, make_summary
from .reporting import write_reports
from .visualization import draw_results

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Detecta espermatozoides y los clasifica según el porcentaje de píxeles rojos."
    )
    parser.add_argument("--source", type=Path, required=True, help="Carpeta de imágenes a procesar (obligatoria).")
    parser.add_argument("--model", type=Path, default=here / "detect_290926.pt", help="Ruta al modelo YOLO (.pt).")
    parser.add_argument("--output", type=Path, default=here / "resultados_viabilidad", help="Carpeta de resultados.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confianza mínima de detección (predeterminado: 0.25).")
    parser.add_argument("--red-threshold", type=float, default=20.0, help="Umbral rojo para clasificar como muerto (predeterminado: 20).")
    parser.add_argument("--imgsz", type=int, default=640, help="Tamaño de inferencia de YOLO.")
    parser.add_argument("--device", default=None, help="Dispositivo, por ejemplo cpu, 0 o 0,1. YOLO elige automáticamente si se omite.")
    return parser.parse_args()


def collect_images(source: Path) -> list[Path]:
    if source.is_file():
        if source.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"El archivo no es una imagen compatible: {source}")
        return [source]
    if not source.is_dir():
        raise FileNotFoundError(f"No existe la carpeta de imágenes: {source}")
    return sorted(path for path in source.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def run() -> int:
    args = parse_args()
    if not 0 <= args.conf <= 1:
        raise SystemExit("--conf debe estar entre 0 y 1.")
    if not 0 <= args.red_threshold <= 100:
        raise SystemExit("--red-threshold debe estar entre 0 y 100.")
    if not args.model.is_file():
        raise SystemExit(f"No se encontró el modelo: {args.model}")
    try:
        files = collect_images(args.source)
    except (ValueError, FileNotFoundError) as error:
        raise SystemExit(str(error)) from error
    if not files:
        raise SystemExit(f"No se encontraron imágenes compatibles en: {args.source}")

    args.output.mkdir(parents=True, exist_ok=True)
    annotated_dir = args.output / "imagenes_anotadas"
    annotated_dir.mkdir(parents=True, exist_ok=True)
    analyzer = ViabilityAnalyzer(args.model, args.conf, args.imgsz, args.device, args.red_threshold)
    summaries: list[ImageSummary] = []
    detection_rows: list[dict] = []

    for number, image_path in enumerate(files, start=1):
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            print(f"[{number}/{len(files)}] No se pudo leer: {image_path}")
            continue
        detections = analyzer.analyze(image)
        relative_path = image_path.relative_to(args.source) if args.source.is_dir() else Path(image_path.name)
        image_name = str(relative_path)
        folder_name = str(relative_path.parent) if str(relative_path.parent) != "." else "."
        summary = make_summary(image_name, detections, folder_name)
        summaries.append(summary)
        annotated = draw_results(image, detections, summary)
        output_image = annotated_dir / relative_path
        output_image.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output_image), annotated):
            print(f"[{number}/{len(files)}] No se pudo guardar: {output_image}")
        for object_number, detection in enumerate(detections, start=1):
            x1, y1, x2, y2 = detection["box"]
            detection_rows.append({
                "imagen": summary.image,
                "espermatozoide": object_number,
                "etiqueta": detection["label"],
                "porcentaje_pixeles_rojos": round(detection["red_percent"], 2),
                "porcentaje_pixeles_azules": round(detection["blue_percent"], 2),
                "pixeles_rojos": detection["red_pixels"],
                "pixeles_azules": detection["blue_pixels"],
                "pixeles_color_objeto": detection["total_pixels"],
                "confianza_yolo": round(detection["confidence"], 4),
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            })
        print(f"[{number}/{len(files)}] {summary.image}: {summary.total} espermatozoides; {summary.vivos} vivos, {summary.muertos} muertos")

    write_reports(args.output, summaries, detection_rows, args.red_threshold, args.conf)
    total = sum(item.total for item in summaries)
    vivos = sum(item.vivos for item in summaries)
    muertos = sum(item.muertos for item in summaries)
    pct_vivos = 100 * vivos / total if total else 0
    pct_muertos = 100 * muertos / total if total else 0
    print(f"\nEspermatozoides detectados: {total}; {vivos} vivos ({pct_vivos:.1f}%), {muertos} muertos ({pct_muertos:.1f}%).")
    print(f"Resultados guardados en: {args.output.resolve()}")
    return 0
