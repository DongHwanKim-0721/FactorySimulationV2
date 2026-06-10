# FactorySimulation V2

Tkinter-based factory process simulation tool.

## Run after cloning

On Windows, the checked-in executable is the fastest way to run the same app:

```powershell
.\dist\FactorySimulation.exe
```

To run from source instead, install Python 3.13 or newer with `tkinter` enabled,
then run:

```powershell
python .\main.py
```

The application currently uses only Python standard-library modules at runtime.

## Rebuild the executable

Install PyInstaller, then rebuild from the repository root:

```powershell
python -m pip install pyinstaller
pyinstaller .\FactorySimulation.spec --noconfirm
```

The rebuilt executable will be written to `dist\FactorySimulation.exe`.

## Tests

Tests use `pytest`:

```powershell
python -m pip install pytest
python -m pytest
```

## Project notes

Current product and implementation context lives in `docs/`.
