"""Liga e desliga o motor local (llama-server.exe), escondido e só em 127.0.0.1."""

from __future__ import annotations

import logging
import subprocess
import time
import urllib.request

from .config import PASTA_LOGS, caminho

log = logging.getLogger(__name__)

# Flag do Windows para o processo não abrir janela de console.
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Motor:
    def __init__(self, cfg_local: dict):
        self.cfg = cfg_local
        self.porta = int(cfg_local.get("porta", 8089))
        self.url_base = f"http://127.0.0.1:{self.porta}"
        self.processo: subprocess.Popen | None = None
        self._arq_log = None

    # ---------------------------------------------------------------
    def saudavel(self) -> bool:
        """True quando o motor responde e o modelo já está carregado."""
        try:
            with urllib.request.urlopen(f"{self.url_base}/health", timeout=1.5) as r:
                return r.status == 200
        except Exception:
            return False

    def ligar(self) -> None:
        """Inicia o motor (se já não estiver rodando)."""
        if self.saudavel():
            log.info("Motor já estava rodando na porta %s.", self.porta)
            return
        if self.processo and self.processo.poll() is None:
            return  # já está carregando

        exe = caminho(self.cfg["motor"])
        modelo = caminho(self.cfg["modelo"])
        if not exe.exists():
            raise FileNotFoundError(f"Motor não encontrado: {exe}\nRode: python preparar.py")
        if not modelo.exists():
            raise FileNotFoundError(f"Modelo não encontrado: {modelo}\nRode: python preparar.py")

        args = [
            str(exe),
            "-m", str(modelo),
            "--host", "127.0.0.1",          # só a própria máquina
            "--port", str(self.porta),
            "-ngl", str(self.cfg.get("camadas_na_placa", 99)),
            "-c", str(self.cfg.get("tamanho_contexto", 4096)),
            "--parallel", "1",              # um pedido por vez (economiza memória)
        ]
        PASTA_LOGS.mkdir(exist_ok=True)
        self._arq_log = open(PASTA_LOGS / "motor.log", "w", encoding="utf-8", errors="replace")
        log.info("Ligando motor: %s", " ".join(args))
        self.processo = subprocess.Popen(
            args,
            cwd=str(exe.parent),
            stdout=self._arq_log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=SEM_JANELA,
        )

    def esperar_pronto(self, limite_s: float = 120) -> bool:
        """Espera o modelo terminar de carregar."""
        fim = time.time() + limite_s
        while time.time() < fim:
            if self.processo and self.processo.poll() is not None:
                log.error("Motor fechou sozinho (código %s). Veja logs/motor.log", self.processo.returncode)
                return False
            if self.saudavel():
                return True
            time.sleep(0.5)
        return False

    def desligar(self) -> None:
        if self.processo and self.processo.poll() is None:
            log.info("Desligando motor.")
            self.processo.terminate()
            try:
                self.processo.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.processo.kill()
        self.processo = None
        if self._arq_log:
            self._arq_log.close()
            self._arq_log = None
