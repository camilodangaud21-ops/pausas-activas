"""Registra (o quita) Pausa Activa para que arranque junto con Windows.

Uso:
    python scripts/add_to_startup.py            # instala
    python scripts/add_to_startup.py --remove   # desinstala

Cómo funciona: agrega (o elimina) una entrada en la clave de registro
`HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run`, que Windows lee
al iniciar sesión del usuario actual (no requiere permisos de
administrador, a diferencia de la clave equivalente en HKLM).

Se usa `pythonw.exe` (si existe junto al intérprete actual) en vez de
`python.exe` para que el programa arranque sin abrir una consola visible.

Este script es intencionalmente independiente del resto del proyecto (no
importa nada de agents/ ni core/) para poder ejecutarse aun si algo en el
programa principal está roto.
"""

import argparse
import os
import sys

APP_NAME = "PausaActiva"


def _run_key():
    import winreg  # solo existe en Windows; se importa acá para no romper
    # en Linux/Mac al simplemente importar este módulo (ej. en CI).
    return winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"


def _command_to_register() -> str:
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    interpreter = pythonw if os.path.exists(pythonw) else sys.executable
    main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    return f'"{interpreter}" "{main_py}"'


def install() -> None:
    import winreg
    hive, subkey = _run_key()
    command = _command_to_register()
    with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
    print(f"Instalado. Se ejecutará al iniciar sesión:\n  {command}")


def remove() -> None:
    import winreg
    hive, subkey = _run_key()
    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        print("Entrada de autoarranque eliminada.")
    except FileNotFoundError:
        print("No había ninguna entrada de autoarranque que quitar.")


def main() -> None:
    if not sys.platform.startswith("win"):
        print("Este script solo aplica a Windows (usa el Registro de Windows).")
        sys.exit(1)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remove", action="store_true",
                         help="quita la entrada de autoarranque en vez de instalarla")
    args = parser.parse_args()

    if args.remove:
        remove()
    else:
        install()


if __name__ == "__main__":
    main()
