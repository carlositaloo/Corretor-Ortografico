"""Gera a pasta  dist\\Corretor  com o Corretor.exe (não precisa de Python no PC).

Rodar:  .venv\\Scripts\\python.exe gerar_exe.py

O motor e o modelo NÃO vão para dentro do .exe: ficam como pastas ao lado
dele (motor\\ e modelos\\), igual ao projeto. O modelo é ligado por "hard link"
quando possível, para não gastar mais 2,5 GB no disco.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DIST = RAIZ / "dist" / "Corretor"
BUILD = RAIZ / "build"
ICONE = BUILD / "corretor.ico"


def gerar_icone() -> None:
    """Salva o ícone azul "Aa" do app como .ico para o Corretor.exe."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    from corretor.app import _icone

    BUILD.mkdir(exist_ok=True)
    pix = _icone("azul").pixmap(256, 256)
    if not pix.save(str(ICONE), "ICO"):
        print("Aviso: não consegui criar o ícone, o .exe fica com o ícone padrão.")
    del app


def copiar_pasta(origem: Path, destino: Path) -> None:
    """Copia a pasta; arquivos grandes viram hard link (mesmo disco, zero espaço extra)."""
    destino.mkdir(parents=True, exist_ok=True)
    for arq in origem.rglob("*"):
        alvo = destino / arq.relative_to(origem)
        if arq.is_dir():
            alvo.mkdir(parents=True, exist_ok=True)
            continue
        if alvo.exists():
            alvo.unlink()
        try:
            if arq.stat().st_size > 100 * 1024 * 1024:
                os.link(arq, alvo)
                continue
        except OSError:
            pass  # outro disco ou sem permissão: copia normal
        shutil.copy2(arq, alvo)


def main() -> int:
    gerar_icone()
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--windowed",
        "--name", "Corretor",
        "--distpath", str(RAIZ / "dist"),
        "--workpath", str(BUILD),
        "--specpath", str(BUILD),
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pynput.mouse._win32",
    ]
    if ICONE.exists():
        cmd += ["--icon", str(ICONE)]
    cmd.append(str(RAIZ / "iniciar.pyw"))
    print("Rodando PyInstaller...")
    if subprocess.call(cmd, cwd=RAIZ) != 0:
        print("PyInstaller falhou.")
        return 1

    print("Copiando configurações, motor e modelo...")
    for nome in ("acoes.toml", "configuracoes.json", "baixar_modelo.bat", "LICENSE", "README.md"):
        shutil.copy2(RAIZ / nome, DIST / nome)
    copiar_pasta(RAIZ / "motor", DIST / "motor")
    copiar_pasta(RAIZ / "modelos", DIST / "modelos")
    print(f"Pronto: {DIST / 'Corretor.exe'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
