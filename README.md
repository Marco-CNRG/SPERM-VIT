# Instalador Windows

Esta tercera variante genera un instalador `.exe` para Windows. Al ejecutarlo, copia la aplicación y el modelo a `%LOCALAPPDATA%\Programs\ViabilidadEspermatica`, registra un desinstalador y crea un acceso en el menú Inicio. Al terminar ofrece iniciar la aplicación. También permite elegir un acceso directo en el escritorio.

La app instalada usa formato **onedir**: las bibliotecas de Python y YOLO se instalan una sola vez en la carpeta permanente de la aplicación, y el modelo `detect_290926.pt` queda como archivo independiente junto al EXE. Las ejecuciones posteriores no extraen el contenido del instalador ni del EXE temporal a una carpeta nueva.

## Crear el instalador

La compilación debe hacerse en una computadora Windows de 64 bits. Esta carpeta conserva una copia independiente del código, las librerías requeridas y el modelo. En Anaconda Prompt, activa el entorno `yolo` y prepara las dependencias del compilador de la app:

```bat
conda activate yolo
python -m pip install -r requirements.txt -r requirements-build.txt
```

Instala también **Inno Setup 6** en la computadora que compila. Luego haz doble clic en `crear_instalador_windows.bat`. El instalador resultante estará en `Output\Instalador_ViabilidadEspermatica.exe`.

Las descargas de PyInstaller, PyTorch/YOLO y de Inno Setup son necesarias solo para preparar la compilación. La persona que reciba el instalador no necesitará instalar Python, Conda, YOLO ni conectarse a Internet.

El entorno de compilación debe contener las dependencias de la aplicación y PyInstaller. Para mantener el instalador independiente de CUDA, se recomienda usar PyTorch CPU en el entorno de compilación. El instalador final será grande porque incluye PyTorch, Ultralytics y el modelo.
