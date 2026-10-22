"""O aplicativo: ícone na bandeja, atalhos, menu e o caminho copiar -> IA -> colar."""

from __future__ import annotations

import copy
import logging
import os
import sys
import threading
import time
import winreg

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from . import teclado
from .config import COMO_BAIXAR, RAIZ, Acao, carregar_acoes, carregar_config, salvar_acoes, salvar_config
from .ia import ClienteIA, ErroIA, alternar_maiusculas
from .janela_config import JanelaConfig
from .janelas import Aviso, Menu, aplicar_tema
from .motor import Motor

log = logging.getLogger(__name__)

NOME_APP = "Corretor Ortografico"
CHAVE_INICIAR = r"Software\Microsoft\Windows\CurrentVersion\Run"


#                cor do fundo, cor do "Aa"
CORES_ICONE = {
    "azul": ("#2f6fed", "#ffffff"),      # pronto
    "amarelo": ("#f0b400", "#1d1d1f"),   # corrigindo ou carregando
    "vermelho": ("#d9534f", "#ffffff"),  # IA fora da placa (solta, pausada ou com erro)
}
_cache_icones: dict[str, QIcon] = {}


def _icone(cor: str = "azul") -> QIcon:
    """Desenha o ícone da bandeja: um quadrado colorido com 'Aa'."""
    if cor in _cache_icones:
        return _cache_icones[cor]
    fundo, letra = CORES_ICONE.get(cor, CORES_ICONE["azul"])
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(fundo))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    p.setPen(QColor(letra))
    p.setFont(QFont("Segoe UI", 26, QFont.Bold))
    p.drawText(pix.rect(), Qt.AlignCenter, "Aa")
    p.end()
    _cache_icones[cor] = QIcon(pix)
    return _cache_icones[cor]


class Sinais(QObject):
    """Ponte entre as threads de fundo e a tela (Qt só mexe na tela pela thread principal)."""

    icone = Signal(str)                            # "azul", "amarelo" ou "vermelho"
    texto_copiado = Signal(int, str, str, object)  # hwnd, texto, antigo, acao (ou None)
    aviso = Signal(str, bool, int)                 # texto, erro?, duração ms
    esconder_aviso = Signal()
    status = Signal(str)


class Corretor:
    def __init__(self, app: QApplication):
        self.app = app
        self.cfg = carregar_config()
        self.acoes = carregar_acoes()
        self.tema = self.cfg.get("tema", "escuro")
        self.ocupado = threading.Lock()
        self.menu: Menu | None = None
        self._lock_motor = threading.Lock()  # um liga/desliga por vez
        self.pausado = False                  # "Pausar IA" marcado na bandeja
        self.ia_pronta = False                # modelo carregado e respondendo
        self.ultimo_uso = time.time()

        self.sinais = Sinais()
        aplicar_tema(self.app, self.tema)
        self.aviso = Aviso(self.tema)
        self.sinais.texto_copiado.connect(self._ao_copiar)
        self.sinais.aviso.connect(lambda t, e, d: self.aviso.mostrar(t, e, d))
        self.sinais.esconder_aviso.connect(lambda: self.aviso.hide())
        self.sinais.icone.connect(lambda cor: self.bandeja.setIcon(_icone(cor)))
        self.sinais.status.connect(lambda t: self.bandeja.setToolTip(f"{NOME_APP}\n{t}"))

        self.motor: Motor | None = None
        self.cliente = self._criar_cliente()
        self.atalhos = teclado.Atalhos()

        self._criar_bandeja()
        self._registrar_atalhos()
        self._janela_cfg = None
        if self.motor:
            self.bandeja.setIcon(_icone("amarelo"))  # carregando
            threading.Thread(target=self._garantir_motor, daemon=True).start()
        else:
            self.ia_pronta = True
        # Confere a cada 30 s se a IA ficou parada tempo demais.
        self._relogio = QTimer(self.app, interval=30_000, timeout=self._checar_ocioso)
        self._relogio.start()

    # ------------------------------------------------------------- IA
    def _criar_cliente(self) -> ClienteIA:
        if self.cfg.get("provedor", "local") == "online":
            self.motor = None
            o = self.cfg["online"]
            return ClienteIA(o["url"], o.get("modelo", ""), o.get("chave", ""), local=False)
        self.motor = Motor(self.cfg["local"])
        return ClienteIA(self.motor.url_base + "/v1", local=True)

    def _trocar_ia(self) -> None:
        """Depois de mudar a IA nas configurações: desliga a velha e liga a nova."""
        velho = self.motor
        if velho:
            with self._lock_motor:
                velho.desligar()
        self.cliente = self._criar_cliente()
        if self.motor and not self.pausado:
            self._garantir_motor()
        elif not self.motor:
            self.ia_pronta = True
            self.sinais.icone.emit("azul")
            self.sinais.status.emit(f"IA online. Atalho: {self.cfg['atalho_menu']}")

    def _garantir_motor(self, avisar: bool = False) -> bool:
        """Liga a IA se ela não estiver pronta. Devolve True quando dá para usar."""
        with self._lock_motor:
            if self.motor.saudavel():
                self.ia_pronta = True
                return True
            if avisar:
                self.sinais.aviso.emit("Ligando a IA (uns segundos)...", False, 0)
            self.sinais.icone.emit("amarelo")
            self.sinais.status.emit("Carregando a IA...")
            try:
                self.motor.ligar()
            except FileNotFoundError as e:
                log.error("%s", e)
                self._ia_caiu("Motor ou modelo faltando")
                self.sinais.aviso.emit(f"Motor ou modelo faltando. {COMO_BAIXAR}", True, 6000)
                return False
            if not self.motor.esperar_pronto():
                self._ia_caiu("A IA não ligou. Veja logs/motor.log")
                self.sinais.aviso.emit("A IA não ligou. Veja logs/motor.log", True, 6000)
                return False
            self._aquecer()
            self.ultimo_uso = time.time()
            self.ia_pronta = True
            self.sinais.icone.emit("azul")
            self.sinais.status.emit(f"Pronto. Atalho: {self.cfg['atalho_menu']}")
            log.info("Motor pronto.")
            return True

    def _ia_caiu(self, motivo: str) -> None:
        self.ia_pronta = False
        self.sinais.icone.emit("vermelho")
        self.sinais.status.emit(motivo)

    def _soltar_motor(self, motivo: str) -> None:
        """Tira o modelo da placa de vídeo."""
        with self._lock_motor:
            if not self.motor or self.motor.processo is None:
                return
            self.motor.desligar()
        log.info("IA solta da memória: %s", motivo)
        self._ia_caiu(motivo)

    def _checar_ocioso(self) -> None:
        minutos = float(self.cfg.get("soltar_ia_apos_minutos", 5) or 0)
        if (
            minutos > 0
            and self.motor
            and not self.pausado
            and self.motor.processo is not None
            and not self.ocupado.locked()
            and time.time() - self.ultimo_uso > minutos * 60
        ):
            threading.Thread(
                target=self._soltar_motor,
                args=("IA dormindo (liga sozinha no próximo uso)",),
                daemon=True,
            ).start()

    def _pausar(self, ligado: bool) -> None:
        self.pausado = ligado
        if not self.motor:
            return
        if ligado:
            threading.Thread(target=self._soltar_motor, args=("IA pausada",), daemon=True).start()
            self.aviso.mostrar("IA pausada. A placa de vídeo está livre.", duracao_ms=2500)
        else:
            threading.Thread(target=self._garantir_motor, args=(True,), daemon=True).start()

    def _aquecer(self) -> None:
        """Primeiro pedido é lento (a placa prepara tudo). Faz um de mentira no começo."""
        if not self.acoes.lista:
            return
        try:
            self.cliente.executar(self.acoes.lista[0], self.acoes.regras_gerais, "teste", 0.0)
        except Exception:
            pass

    # ------------------------------------------------------------- bandeja
    def _criar_bandeja(self) -> None:
        self.bandeja = QSystemTrayIcon(_icone(), self.app)
        self.bandeja.setToolTip(NOME_APP)
        m = QMenu()

        a = QAction("Configurações...", m)
        a.triggered.connect(self.abrir_config)
        m.addAction(a)
        self.bandeja.activated.connect(
            lambda motivo: motivo == QSystemTrayIcon.DoubleClick and self.abrir_config()
        )

        a = QAction("Recarregar arquivos", m)
        a.triggered.connect(self.recarregar)
        m.addAction(a)

        a = QAction("Abrir pasta do projeto", m)
        a.triggered.connect(lambda: os.startfile(RAIZ))
        m.addAction(a)

        m.addSeparator()
        self.acao_pausar = QAction("Pausar IA (libera a placa de vídeo)", m, checkable=True)
        self.acao_pausar.toggled.connect(self._pausar)
        m.addAction(self.acao_pausar)

        self.acao_iniciar = QAction("Iniciar com o Windows", m, checkable=True)
        self.acao_iniciar.setChecked(self._inicia_com_windows())
        self.acao_iniciar.toggled.connect(self._definir_inicio_windows)
        m.addAction(self.acao_iniciar)

        m.addSeparator()
        a = QAction("Sair", m)
        a.triggered.connect(self.sair)
        m.addAction(a)

        self.bandeja.setContextMenu(m)
        self._menu_bandeja = m  # mantém referência viva
        self.bandeja.show()

    # ------------------------------------------------------------- atalhos
    def _registrar_atalhos(self) -> None:
        mapa = {self.cfg.get("atalho_menu", "ctrl+space"): lambda: self._disparar(None)}
        for acao in self.acoes.lista:
            if acao.atalho:
                mapa[acao.atalho] = lambda a=acao: self._disparar(a)
        erros = self.atalhos.registrar(mapa)
        if erros:
            self.sinais.aviso.emit(f"Atalho inválido: {', '.join(erros)}", True, 5000)

    def _disparar(self, acao: Acao | None) -> None:
        """Chamado pelo atalho (thread do teclado). Copia numa thread nova."""
        if not self.ocupado.acquire(blocking=False):
            return  # já tem uma correção rodando
        threading.Thread(target=self._copiar, args=(acao,), daemon=True).start()

    def _copiar(self, acao: Acao | None) -> None:
        try:
            hwnd = teclado.janela_ativa()
            texto, antigo = teclado.copiar_selecao()
        except Exception:
            log.exception("Falha ao copiar")
            self.ocupado.release()
            return
        self.sinais.texto_copiado.emit(hwnd, texto, antigo, acao)

    # ------------------------------------------------------------- fluxo principal
    def _ao_copiar(self, hwnd: int, texto: str, antigo: str, acao: Acao | None) -> None:
        if not texto.strip():
            self.ocupado.release()
            self.aviso.mostrar("Selecione um texto primeiro.", erro=True, duracao_ms=2000)
            return
        if acao is not None:
            self._executar(hwnd, texto, antigo, acao)
            return

        self.menu = Menu(self.acoes.lista, self.tema)
        self.menu.escolhida.connect(lambda a: self._executar(hwnd, texto, antigo, a))
        self.menu.cancelado.connect(lambda: self._cancelar(hwnd))
        self.menu.abrir()
        teclado.focar_janela(int(self.menu.winId()))

    def _cancelar(self, hwnd: int) -> None:
        self.ocupado.release()
        teclado.focar_janela(hwnd)

    def _executar(self, hwnd: int, texto: str, antigo: str, acao: Acao) -> None:
        teclado.focar_janela(hwnd)
        if acao.tipo != "maiusculas":
            self.aviso.mostrar(f"{acao.nome}...")
        threading.Thread(target=self._trabalhar, args=(hwnd, texto, antigo, acao), daemon=True).start()

    def _trabalhar(self, hwnd: int, texto: str, antigo: str, acao: Acao) -> None:
        restaurar = antigo if self.cfg.get("restaurar_area_de_transferencia", True) else None
        try:
            if acao.tipo == "maiusculas":
                novo = alternar_maiusculas(texto)
            else:
                if self.motor:
                    if self.pausado:
                        self.sinais.aviso.emit("IA pausada. Desmarque no ícone \"Aa\".", True, 3000)
                        return
                    self.ultimo_uso = time.time()
                    if not self._garantir_motor(avisar=True):
                        return
                    self.sinais.aviso.emit(f"{acao.nome}...", False, 0)
                self.sinais.icone.emit("amarelo")
                novo = self.cliente.executar(
                    acao, self.acoes.regras_gerais, texto, float(self.cfg.get("temperatura", 0.2))
                )
                self.ultimo_uso = time.time()
            teclado.focar_janela(hwnd)
            teclado.colar_texto(novo, restaurar)
            self.sinais.esconder_aviso.emit()
        except ErroIA as e:
            self.sinais.aviso.emit(str(e), True, 3500)
        except Exception:
            log.exception("Erro inesperado")
            self.sinais.aviso.emit("Erro inesperado. Veja logs/corretor.log", True, 3500)
        finally:
            self.sinais.icone.emit("azul" if self.ia_pronta or not self.motor else "vermelho")
            self.ocupado.release()

    # ------------------------------------------------------------- outros
    def abrir_config(self) -> None:
        if self._janela_cfg:  # já aberta: só traz para frente
            self._janela_cfg.raise_()
            self._janela_cfg.activateWindow()
            return
        # Desliga os atalhos enquanto a janela está aberta,
        # para dar para gravar ctrl+space sem abrir o menu.
        self.atalhos.parar()
        j = JanelaConfig(self.cfg, self.acoes, self._inicia_com_windows(), _icone())
        self._janela_cfg = j
        j.show()
        teclado.focar_janela(int(j.winId()))
        aceitou = j.exec()
        self._janela_cfg = None

        if aceitou:
            antigo = copy.deepcopy(self.cfg)
            try:
                salvar_config(j.cfg)
                salvar_acoes(j.acoes)
            except Exception as e:
                log.exception("Erro ao salvar")
                QMessageBox.critical(None, "Erro", f"Não deu para salvar:\n{e}")
            else:
                if j.inicia_windows != self.acao_iniciar.isChecked():
                    self.acao_iniciar.setChecked(j.inicia_windows)
                self._aplicar(antigo)
        self._registrar_atalhos()

    def _aplicar(self, antigo: dict) -> None:
        """Faz as configurações novas valerem sem fechar o app."""
        self.cfg = carregar_config()
        self.acoes = carregar_acoes()
        if self.cfg.get("tema") != self.tema:
            self.tema = self.cfg.get("tema", "escuro")
            aplicar_tema(self.app, self.tema)
            self.aviso.hide()
            self.aviso = Aviso(self.tema)
        chaves_ia = ("provedor", "local", "online")
        if any(antigo.get(k) != self.cfg.get(k) for k in chaves_ia):
            threading.Thread(target=self._trocar_ia, daemon=True).start()
        self.aviso.mostrar("Configurações salvas.", duracao_ms=1500)

    def recarregar(self) -> None:
        try:
            self.cfg = carregar_config()
            self.acoes = carregar_acoes()
        except Exception as e:
            log.exception("Erro ao recarregar")
            self.aviso.mostrar(f"Erro no arquivo: {e}", erro=True, duracao_ms=6000)
            return
        if self.cfg.get("provedor", "local") == "online":
            self.cliente = self._criar_cliente()
        self._registrar_atalhos()
        self.aviso.mostrar("Ações recarregadas.", duracao_ms=1500)

    @staticmethod
    def _comando_iniciar() -> str:
        if getattr(sys, "frozen", False):  # rodando como Corretor.exe
            return f'"{sys.executable}"'
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        return f'"{pythonw}" "{RAIZ / "iniciar.pyw"}"'

    def _inicia_com_windows(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_INICIAR) as k:
                winreg.QueryValueEx(k, NOME_APP)
                return True
        except OSError:
            return False

    def _definir_inicio_windows(self, ligar: bool) -> None:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_INICIAR, 0, winreg.KEY_SET_VALUE) as k:
            if ligar:
                winreg.SetValueEx(k, NOME_APP, 0, winreg.REG_SZ, self._comando_iniciar())
            else:
                try:
                    winreg.DeleteValue(k, NOME_APP)
                except OSError:
                    pass

    def sair(self) -> None:
        self.atalhos.parar()
        if self.motor:
            self.motor.desligar()
        self.bandeja.hide()
        self.app.quit()
