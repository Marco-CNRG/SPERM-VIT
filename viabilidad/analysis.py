"""Carga del modelo YOLO y análisis de detecciones por imagen."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class ImageSummary:
    image: str
    folder: str
    total: int
    vivos: int
    muertos: int
    porcentaje_vivos: float
    porcentaje_muertos: float


class ViabilityAnalyzer:
    """Analiza imágenes con YOLO y clasifica cada caja por su contenido rojo."""
    """modifica el float para establecer distintos umbrales de viabilidad"""

    def __init__(self, model_path: Path, confidence: float = 0.25, image_size: int = 640,
                 device: str | None = None, red_threshold: float = 10.0):  
        self.model = YOLO(str(model_path))
        self.confidence = confidence
        self.image_size = image_size
        self.device = device
        self.red_threshold = red_threshold

    @staticmethod
    def red_pixel_mask(roi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Devuelve píxeles rojos y azules del ROI, descartando fondo y tonos neutros.

        La imagen de OpenCV llega en BGR; se convierte explícitamente a RGB.
        Se aplica un umbral de Otsu en escala de grises para quitar el fondo
        oscuro del ROI. Dentro del primer plano, solo se cuentan píxeles con
        señal suficiente y un canal rojo o azul claramente dominante. Los
        píxeles neutros no entran en el denominador del porcentaje.
        """
        rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB).astype(np.int16)
        red, blue = rgb[:, :, 0], rgb[:, :, 2]
        min_signal = 24
        min_dominance = 12
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        otsu_threshold, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        foreground = gray >= max(min_signal, otsu_threshold)
        red_pixels = foreground & (red >= min_signal) & (red >= blue + min_dominance)
        blue_pixels = foreground & (blue >= min_signal) & (blue >= red + min_dominance)
        return red_pixels, blue_pixels

    @staticmethod
    def _object_mask(result, index: int, box: tuple[int, int, int, int], shape: tuple[int, int]) -> np.ndarray:
        height, width = shape
        if result.masks is not None and index < len(result.masks.data):
            mask = result.masks.data[index].detach().cpu().numpy().astype(np.uint8)
            mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST) > 0
            x1, y1, x2, y2 = box
            region = np.zeros((height, width), dtype=bool)
            region[y1:y2, x1:x2] = mask[y1:y2, x1:x2]
            return region
        x1, y1, x2, y2 = box
        region = np.zeros((height, width), dtype=bool)
        region[y1:y2, x1:x2] = True
        return region

    def analyze(self, image: np.ndarray) -> list[dict]:
        height, width = image.shape[:2]
        options = {"source": image, "conf": self.confidence, "imgsz": self.image_size, "verbose": False}
        if self.device is not None:
            options["device"] = self.device
        result = self.model.predict(**options)[0]
        detections = []
        if result.boxes is None:
            return detections
        boxes = result.boxes.xyxy.detach().cpu().numpy()
        confidences = result.boxes.conf.detach().cpu().numpy()
        for index, (coordinates, confidence) in enumerate(zip(boxes, confidences)):
            x1, y1, x2, y2 = np.rint(coordinates).astype(int)
            x1, x2 = int(np.clip(x1, 0, width)), int(np.clip(x2, 0, width))
            y1, y2 = int(np.clip(y1, 0, height)), int(np.clip(y2, 0, height))
            if x2 <= x1 or y2 <= y1:
                continue
            object_mask = self._object_mask(result, index, (x1, y1, x2, y2), (height, width))[y1:y2, x1:x2]
            total_pixels = int(np.count_nonzero(object_mask))
            if not total_pixels:
                continue
            red_mask, blue_mask = self.red_pixel_mask(image[y1:y2, x1:x2])
            red_pixels = int(np.count_nonzero(red_mask & object_mask))
            blue_pixels = int(np.count_nonzero(blue_mask & object_mask))
            color_pixels = red_pixels + blue_pixels
            red_percent = 100.0 * red_pixels / color_pixels if color_pixels else 0.0
            detections.append({
                "box": (x1, y1, x2, y2),
                "confidence": float(confidence),
                "red_pixels": red_pixels,
                "blue_pixels": blue_pixels,
                "total_pixels": color_pixels,
                "blue_percent": 100.0 * blue_pixels / color_pixels if color_pixels else 0.0,
                "red_percent": red_percent,
                "label": "muerto" if red_percent > self.red_threshold else "vivo",
            })
        return detections


def make_summary(image_name: str, detections: list[dict], folder_name: str = ".") -> ImageSummary:
    total = len(detections)
    muertos = sum(item["label"] == "muerto" for item in detections)
    vivos = total - muertos
    return ImageSummary(
        image=image_name,
        folder=folder_name,
        total=total,
        vivos=vivos,
        muertos=muertos,
        porcentaje_vivos=100.0 * vivos / total if total else 0.0,
        porcentaje_muertos=100.0 * muertos / total if total else 0.0,
    )
