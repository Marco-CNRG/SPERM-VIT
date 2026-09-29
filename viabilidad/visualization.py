"""Dibujo de cajas, etiquetas y resumen sobre las imágenes."""

import cv2
import numpy as np

from .analysis import ImageSummary


def draw_results(image: np.ndarray, detections: list[dict], summary: ImageSummary) -> np.ndarray:
    annotated = image.copy()
    for detection in detections:
        x1, y1, x2, y2 = detection["box"]
        # OpenCV usa BGR: verde para vivo y rojo para muerto.
        color = (0, 220, 0) if detection["label"] == "vivo" else (0, 0, 230)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        text = f'{detection["label"]} | rojo {detection["red_percent"]:.1f}%'
        font, scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2
        (text_w, text_h), baseline = cv2.getTextSize(text, font, scale, thickness)
        label_y = max(y1, text_h + baseline + 4)
        left, top = x1, label_y - text_h - baseline - 4
        right = min(x1 + text_w + 8, annotated.shape[1] - 1)
        cv2.rectangle(annotated, (left, top), (right, label_y + 1), (15, 15, 15), -1)
        cv2.putText(annotated, text, (x1 + 3, label_y - baseline - 2), font, scale, color, thickness, cv2.LINE_AA)

    panel = [
        f"Espermatozoides detectados: {summary.total}",
        f"Vivos: {summary.vivos} ({summary.porcentaje_vivos:.1f}%)",
        f"Muertos: {summary.muertos} ({summary.porcentaje_muertos:.1f}%)",
    ]
    font, scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
    line_h = 28
    panel_w = max(cv2.getTextSize(line, font, scale, thickness)[0][0] for line in panel) + 22
    panel_h = line_h * len(panel) + 16
    overlay = annotated.copy()
    cv2.rectangle(overlay, (0, 0), (min(panel_w, image.shape[1] - 1), min(panel_h, image.shape[0] - 1)), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.78, annotated, 0.22, 0, annotated)
    for line_index, line in enumerate(panel):
        cv2.putText(annotated, line, (10, 25 + line_index * line_h), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return annotated
