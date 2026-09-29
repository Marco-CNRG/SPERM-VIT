#!/usr/bin/env python3
"""Interfaz gráfica sencilla para la evaluación de viabilidad espermática."""

from __future__ import annotations

import queue
import shutil
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2

from viabilidad.analysis import ImageSummary, ViabilityAnalyzer, make_summary
from viabilidad.cli import collect_images
from viabilidad.reporting import write_reports
from viabilidad.visualization import draw_results


if getattr(sys, "frozen", False):
    # En modo onedir el modelo queda como archivo independiente junto al EXE.
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent
MODEL_PATH = APP_DIR / "detect_290926.pt"


class ViabilityApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Viabilidad espermática")
        self.root.geometry("760x570")
        self.root.minsize(680, 520)
        self.root.configure(bg="#f4f7fb")

        self.source_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Selecciona la carpeta que contiene tus imágenes.")
        self.result_var = tk.StringVar(value="")
        self.events: queue.Queue = queue.Queue()
        self.running = False
        self.cancel_event = threading.Event()
        self.state_lock = threading.Lock()
        self.run_finished = True
        self.output_path: Path | None = None

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f4f7fb")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#f4f7fb", foreground="#183153", font=("Segoe UI", 23, "bold"))
        style.configure("Subtitle.TLabel", background="#f4f7fb", foreground="#52657a", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#183153", font=("Segoe UI", 12, "bold"))
        style.configure("Body.TLabel", background="#ffffff", foreground="#40536a", font=("Segoe UI", 10))
        style.configure("Status.TLabel", background="#ffffff", foreground="#52657a", font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 9))
        style.configure("Horizontal.TProgressbar", troughcolor="#e5edf6", background="#2776d2", thickness=12)

        self._build_ui()
        self.root.after(100, self._poll_events)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=(30, 25))
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Evaluación de viabilidad espermática", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="By: Marco Aragón. Contacto: aragon.marco@inifap.gob.mx",
            style="Subtitle.TLabel",
            wraplength=680,
        ).pack(anchor="w", pady=(5, 22))

        card = ttk.Frame(outer, style="Card.TFrame", padding=22)
        card.pack(fill="x")
        ttk.Label(card, text="1. Selecciona la carpeta de imágenes", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Se incluirán las imágenes que estén en subcarpetas.",
            style="Body.TLabel",
        ).pack(anchor="w", pady=(4, 13))

        path_row = ttk.Frame(card, style="Card.TFrame")
        path_row.pack(fill="x")
        self.path_entry = ttk.Entry(path_row, textvariable=self.source_var, state="readonly")
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.choose_button = ttk.Button(path_row, text="Elegir carpeta…", command=self._choose_folder)
        self.choose_button.pack(side="left", padx=(10, 0))

        run_card = ttk.Frame(outer, style="Card.TFrame", padding=22)
        run_card.pack(fill="both", expand=True, pady=(16, 0))
        ttk.Label(run_card, text="2. Ejecuta el análisis", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            run_card,
            text="Se guardarán las imágenes anotadas y los resúmenes CSV en una carpeta de resultados junto a la carpeta seleccionada.",
            style="Body.TLabel",
            wraplength=650,
        ).pack(anchor="w", pady=(4, 17))

        buttons = ttk.Frame(run_card, style="Card.TFrame")
        buttons.pack(anchor="w")
        self.run_button = ttk.Button(buttons, text="Analizar imágenes", style="Accent.TButton", command=self._start)
        self.run_button.pack(side="left")
        self.cancel_button = ttk.Button(buttons, text="Cancelar proceso", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(10, 0))
        self.progress = ttk.Progressbar(run_card, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(20, 8))
        ttk.Label(run_card, textvariable=self.status_var, style="Status.TLabel", wraplength=650).pack(anchor="w")

        self.result_label = ttk.Label(run_card, textvariable=self.result_var, style="CardTitle.TLabel", wraplength=650)
        self.result_label.pack(anchor="w", pady=(12, 0))
        self.open_button = ttk.Button(run_card, text="Abrir carpeta de resultados", command=self._open_output, state="disabled")
        self.open_button.pack(anchor="w", pady=(12, 0))

        footer = ttk.Label(
            outer,
            text="El modelo incluido es detect_290926.pt · Los ROI se procesan en memoria.",
            style="Subtitle.TLabel",
        )
        footer.pack(anchor="w", pady=(15, 0))

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona la carpeta con imágenes", mustexist=True)
        if folder:
            self.source_var.set(folder)
            self.result_var.set("")
            self.open_button.configure(state="disabled")
            self.status_var.set("Carpeta seleccionada. Pulsa «Analizar imágenes» para comenzar.")

    def _start(self) -> None:
        if self.running:
            return
        source_text = self.source_var.get().strip()
        if not source_text:
            messagebox.showinfo("Selecciona una carpeta", "Primero elige la carpeta que contiene tus imágenes.")
            return
        source = Path(source_text)
        if not source.is_dir():
            messagebox.showerror("Carpeta no válida", "La carpeta seleccionada ya no está disponible.")
            return
        if not MODEL_PATH.is_file():
            messagebox.showerror("No se encontró el modelo", f"No se encontró el modelo YOLO:\n{MODEL_PATH}")
            return
        try:
            files = collect_images(source)
        except (ValueError, FileNotFoundError) as error:
            messagebox.showerror("No se pudo leer la carpeta", str(error))
            return
        if not files:
            messagebox.showinfo("Sin imágenes", "No se encontraron imágenes compatibles en la carpeta seleccionada.")
            return

        output = self._available_output_path(source)
        self.output_path = None
        self.cancel_event = threading.Event()
        with self.state_lock:
            self.run_finished = False
        self.running = True
        self.progress.configure(value=0, maximum=len(files))
        self.status_var.set(f"Preparando análisis de {len(files)} imágenes…")
        self.result_var.set("")
        self.run_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.choose_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        thread = threading.Thread(target=self._process, args=(source, output, files, self.cancel_event), daemon=True)
        thread.start()

    @staticmethod
    def _available_output_path(source: Path) -> Path:
        base = source.parent / f"{source.name}_resultados_viabilidad"
        candidate = base
        suffix = 2
        while candidate.exists():
            candidate = source.parent / f"{source.name}_resultados_viabilidad_{suffix}"
            suffix += 1
        return candidate

    def _cancel(self) -> None:
        with self.state_lock:
            if not self.running or self.run_finished:
                return
            self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status_var.set("Cancelando… Se terminará la imagen en curso y se eliminarán los resultados parciales.")

    def _process(self, source: Path, output: Path, files: list[Path], cancel_event: threading.Event) -> None:
        staging: Path | None = None
        try:
            staging = Path(tempfile.mkdtemp(
                prefix=f".{source.name}_resultados_viabilidad_parcial_",
                dir=source.parent,
            ))
            if cancel_event.is_set():
                raise InterruptedError("cancelado")
            annotated_dir = staging / "imagenes_anotadas"
            annotated_dir.mkdir(parents=True, exist_ok=True)
            analyzer = ViabilityAnalyzer(MODEL_PATH, confidence=0.25, image_size=640, red_threshold=20.0)
            summaries: list[ImageSummary] = []
            detection_rows: list[dict] = []
            skipped = 0

            for number, image_path in enumerate(files, start=1):
                if cancel_event.is_set():
                    raise InterruptedError("cancelado")
                image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
                if image is None:
                    skipped += 1
                    self.events.put(("progress", number, len(files), f"No se pudo leer {image_path.name}; se omite."))
                    continue
                detections = analyzer.analyze(image)
                if cancel_event.is_set():
                    raise InterruptedError("cancelado")
                relative_path = image_path.relative_to(source)
                image_name = str(relative_path)
                folder_name = str(relative_path.parent) if str(relative_path.parent) != "." else "."
                summary = make_summary(image_name, detections, folder_name)
                summaries.append(summary)

                annotated = draw_results(image, detections, summary)
                destination = annotated_dir / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not cv2.imwrite(str(destination), annotated):
                    raise OSError(f"No se pudo guardar la imagen anotada: {destination}")

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
                self.events.put(("progress", number, len(files), image_name))

            if not summaries:
                raise RuntimeError("No se pudo procesar ninguna imagen.")
            if cancel_event.is_set():
                raise InterruptedError("cancelado")
            write_reports(staging, summaries, detection_rows, 20.0, 0.25)
            total = sum(item.total for item in summaries)
            vivos = sum(item.vivos for item in summaries)
            muertos = sum(item.muertos for item in summaries)
            result = {
                "images": len(summaries), "skipped": skipped, "total": total,
                "vivos": vivos, "muertos": muertos,
                "pct_vivos": 100 * vivos / total if total else 0,
                "pct_muertos": 100 * muertos / total if total else 0,
                "output": str(output),
            }
            with self.state_lock:
                if cancel_event.is_set():
                    raise InterruptedError("cancelado")
                staging.rename(output)
                self.run_finished = True
            self.events.put(("done", result))
        except InterruptedError:
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)
            with self.state_lock:
                self.run_finished = True
            self.events.put(("cancelled", None))
        except Exception as error:
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)
            with self.state_lock:
                self.run_finished = True
            self.events.put(("error", str(error)))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    _, current, total, image_name = event
                    self.progress.configure(value=current, maximum=total)
                    self.status_var.set(f"Procesando {current} de {total}: {image_name}")
                elif event[0] == "done":
                    result = event[1]
                    self.running = False
                    self.run_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.choose_button.configure(state="normal")
                    self.open_button.configure(state="normal")
                    self.output_path = Path(result["output"])
                    self.status_var.set(f"Proceso terminado. Resultados en: {result['output']}")
                    skipped_text = f" · Omitidas: {result['skipped']}" if result["skipped"] else ""
                    self.result_var.set(
                        f"{result['images']} imágenes · {result['total']} espermatozoides\n"
                        f"Vivos: {result['vivos']} ({result['pct_vivos']:.1f}%)  ·  "
                        f"Muertos: {result['muertos']} ({result['pct_muertos']:.1f}%){skipped_text}"
                    )
                elif event[0] == "cancelled":
                    self.running = False
                    self.run_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.choose_button.configure(state="normal")
                    self.open_button.configure(state="disabled")
                    self.output_path = None
                    self.status_var.set("Proceso cancelado. Se eliminaron los resultados parciales.")
                    self.result_var.set("")
                elif event[0] == "error":
                    self.running = False
                    self.run_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.choose_button.configure(state="normal")
                    self.status_var.set("El proceso no pudo completarse.")
                    messagebox.showerror("Error durante el análisis", event[1])
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _open_output(self) -> None:
        if not self.output_path or not self.output_path.is_dir():
            return
        try:
            import os
            import subprocess
            import sys
            if sys.platform.startswith("win"):
                os.startfile(self.output_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.output_path)])
            else:
                subprocess.Popen(["xdg-open", str(self.output_path)])
        except Exception as error:
            messagebox.showerror("No se pudo abrir la carpeta", str(error))


def main() -> None:
    root = tk.Tk()
    ViabilityApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
