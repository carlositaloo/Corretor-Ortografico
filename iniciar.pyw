"""Abre o Corretor escondido (sem janela de console).

Rodar:  .venv\\Scripts\\pythonw.exe iniciar.pyw
Ver erros na tela: .venv\\Scripts\\python.exe iniciar.pyw
"""

import ctypes
import logging
import sys

from PySide6.QtWidgets import QApplication

from corretor.app import Corretor
from corretor.config import PASTA_LOGS


def main() -> int:
    PASTA_LOGS.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(PASTA_LOGS / "corretor.log", "w", encoding="utf-8")]
        + ([logging.StreamHandler()] if sys.stdout else []),
    )

    # Só uma cópia aberta por vez.
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\CorretorOrtografico")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        logging.info("Já existe um Corretor aberto.")
        return 0

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    corretor = Corretor(app)
    app.aboutToQuit.connect(lambda: corretor.motor and corretor.motor.desligar())
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
