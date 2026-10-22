"""Janelas: o menu de ações e o aviso pequeno ("Corrigindo...")."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QKeyEvent
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from .config import Acao

TEMAS = {
    "escuro": {"fundo": "#1f2024", "borda": "#3a3c42", "texto": "#e8e8ea", "fraco": "#8a8d96",
               "realce": "#2f6fed", "erro": "#d9534f"},
    "claro": {"fundo": "#ffffff", "borda": "#d4d6db", "texto": "#1d1d1f", "fraco": "#6b6e76",
              "realce": "#2f6fed", "erro": "#c9302c"},
}


def _cores(tema: str) -> dict:
    return TEMAS.get(tema, TEMAS["escuro"])


def aplicar_tema(app, tema: str) -> None:
    """Cores das janelas comuns (Configurações, bandeja)."""
    from PySide6.QtGui import QColor, QPalette

    app.setStyle("Fusion")
    if tema != "escuro":
        app.setPalette(app.style().standardPalette())
        return
    c = _cores("escuro")
    p = QPalette()
    p.setColor(QPalette.Window, QColor(c["fundo"]))
    p.setColor(QPalette.WindowText, QColor(c["texto"]))
    p.setColor(QPalette.Base, QColor("#16171a"))
    p.setColor(QPalette.AlternateBase, QColor("#26282d"))
    p.setColor(QPalette.Text, QColor(c["texto"]))
    p.setColor(QPalette.Button, QColor("#2a2c31"))
    p.setColor(QPalette.ButtonText, QColor(c["texto"]))
    p.setColor(QPalette.Highlight, QColor(c["realce"]))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.ToolTipBase, QColor(c["fundo"]))
    p.setColor(QPalette.ToolTipText, QColor(c["texto"]))
    p.setColor(QPalette.PlaceholderText, QColor(c["fraco"]))
    for papel in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        p.setColor(QPalette.Disabled, papel, QColor("#6b6e76"))
    app.setPalette(p)


def _posicionar_no_cursor(w: QWidget) -> None:
    """Coloca a janela perto do mouse, sem sair da tela."""
    pos = QCursor.pos()
    tela = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
    area = tela.availableGeometry()
    w.adjustSize()
    x = min(max(pos.x() + 12, area.left()), area.right() - w.width())
    y = min(max(pos.y() + 12, area.top()), area.bottom() - w.height())
    w.move(QPoint(x, y))


# =====================================================================
class Menu(QWidget):
    """Lista de ações. Teclas 1-9 escolhem, setas andam, Enter confirma, Esc fecha."""

    escolhida = Signal(object)  # Acao
    cancelado = Signal()

    def __init__(self, acoes: list[Acao], tema: str):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._acoes = acoes
        self._fechando = False
        c = _cores(tema)

        caixa = QFrame(self)
        caixa.setObjectName("caixa")
        caixa.setStyleSheet(f"""
            #caixa {{ background:{c['fundo']}; border:1px solid {c['borda']}; border-radius:10px; }}
            QLabel {{ color:{c['fraco']}; font-size:11px; padding:2px 6px; }}
            QPushButton {{ color:{c['texto']}; background:transparent; border:none; text-align:left;
                           padding:7px 10px; border-radius:6px; font-size:13px; }}
            QPushButton:hover, QPushButton:focus {{ background:{c['realce']}; color:#ffffff; outline:none; }}
        """)
        lay = QVBoxLayout(caixa)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(1)
        lay.addWidget(QLabel("Corretor"))

        self._botoes: list[QPushButton] = []
        for i, acao in enumerate(acoes):
            num = f"{i + 1}" if i < 9 else "  "
            dica = f"     {acao.atalho}" if acao.atalho else ""
            b = QPushButton(f"{num}   {acao.nome}{dica}")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, a=acao: self._escolher(a))
            lay.addWidget(b)
            self._botoes.append(b)

        externo = QVBoxLayout(self)
        externo.setContentsMargins(0, 0, 0, 0)
        externo.addWidget(caixa)
        self.setMinimumWidth(240)

    def abrir(self) -> None:
        _posicionar_no_cursor(self)
        self.show()
        self.raise_()
        self.activateWindow()
        if self._botoes:
            self._botoes[0].setFocus()

    def _escolher(self, acao: Acao) -> None:
        self._fechando = True
        self.close()
        self.escolhida.emit(acao)

    def _cancelar(self) -> None:
        if not self._fechando:
            self._fechando = True
            self.close()
            self.cancelado.emit()

    # --- teclado
    def keyPressEvent(self, e: QKeyEvent) -> None:
        k = e.key()
        if k == Qt.Key_Escape:
            self._cancelar()
        elif Qt.Key_1 <= k <= Qt.Key_9:
            i = k - Qt.Key_1
            if i < len(self._acoes):
                self._escolher(self._acoes[i])
        elif k in (Qt.Key_Down, Qt.Key_Up) and self._botoes:
            atual = next((i for i, b in enumerate(self._botoes) if b.hasFocus()), 0)
            passo = 1 if k == Qt.Key_Down else -1
            self._botoes[(atual + passo) % len(self._botoes)].setFocus()
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            for b in self._botoes:
                if b.hasFocus():
                    b.click()
                    return
        else:
            super().keyPressEvent(e)

    # --- clicou fora: fecha
    def changeEvent(self, e) -> None:
        if e.type() == e.Type.ActivationChange and not self.isActiveWindow():
            QTimer.singleShot(0, self._cancelar)
        super().changeEvent(e)


# =====================================================================
class Aviso(QWidget):
    """Avisozinho perto do mouse. Não rouba o foco da janela onde você digita."""

    def __init__(self, tema: str):
        super().__init__(
            None,
            Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._c = _cores(tema)
        self._rotulo = QLabel(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._rotulo)
        self._timer = QTimer(self, singleShot=True, timeout=self.hide)

    def mostrar(self, texto: str, erro: bool = False, duracao_ms: int = 0) -> None:
        cor = self._c["erro"] if erro else self._c["fundo"]
        txt = "#ffffff" if erro else self._c["texto"]
        self._rotulo.setStyleSheet(
            f"background:{cor}; color:{txt}; border:1px solid {self._c['borda']};"
            "border-radius:8px; padding:6px 12px; font-size:12px;"
        )
        self._rotulo.setText(texto)
        _posicionar_no_cursor(self)
        self.show()
        self._timer.stop()
        if duracao_ms:
            self._timer.start(duracao_ms)
