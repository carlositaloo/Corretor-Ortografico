"""Janela de Configurações: abas Geral, IA e Ações."""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QKeySequenceEdit, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from .config import Acao, Acoes, Exemplo, caminho


# =====================================================================
class CampoAtalho(QWidget):
    """Campo onde você aperta a combinação de teclas. Guarda no formato 'ctrl+space'."""

    mudou = Signal()

    def __init__(self, texto: str = ""):
        super().__init__()
        self._edit = QKeySequenceEdit()
        self._edit.setMaximumSequenceLength(1)
        dentro = self._edit.findChild(QLineEdit)
        if dentro:
            dentro.setPlaceholderText("Nenhum (clique e aperte as teclas)")
        self._edit.editingFinished.connect(self.mudou.emit)
        limpar = QPushButton("Limpar")
        limpar.clicked.connect(self.limpar)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._edit, 1)
        lay.addWidget(limpar)
        self.definir(texto)

    def definir(self, texto: str) -> None:
        # 'ctrl+shift+space' -> 'Ctrl+Shift+Space' (formato do Qt)
        partes = [("Meta" if p == "win" else p.capitalize()) for p in texto.split("+") if p]
        self._edit.setKeySequence(QKeySequence("+".join(partes)))

    def texto(self) -> str:
        bruto = self._edit.keySequence().toString(QKeySequence.PortableText)
        return bruto.lower().replace("meta", "win")

    def limpar(self) -> None:
        self._edit.clear()
        self.mudou.emit()


def _nota(texto: str) -> QLabel:
    r = QLabel(texto)
    r.setWordWrap(True)
    r.setStyleSheet("color: gray; font-size: 11px;")
    return r


# =====================================================================
class JanelaConfig(QDialog):
    def __init__(self, cfg: dict, acoes: Acoes, inicia_windows: bool, icone):
        super().__init__(None, Qt.Window)
        self.setWindowTitle("Corretor - Configurações")
        self.setWindowIcon(icone)
        self.resize(820, 600)

        self.cfg = copy.deepcopy(cfg)
        self.acoes = copy.deepcopy(acoes)
        self.inicia_windows = inicia_windows
        self._atual = -1  # ação aberta na aba Ações

        abas = QTabWidget()
        abas.addTab(self._aba_geral(), "Geral")
        abas.addTab(self._aba_ia(), "IA")
        abas.addTab(self._aba_acoes(), "Ações")

        botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botoes.button(QDialogButtonBox.Save).setText("Salvar")
        botoes.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botoes.accepted.connect(self._salvar)
        botoes.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(abas)
        lay.addWidget(botoes)

    # ------------------------------------------------------------- Geral
    def _aba_geral(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)

        self.c_atalho_menu = CampoAtalho(self.cfg.get("atalho_menu", "ctrl+space"))
        f.addRow("Atalho do menu:", self.c_atalho_menu)
        f.addRow("", _nota("Clique no campo e aperte a combinação. Evite Ctrl+Alt (é o AltGr no teclado ABNT2)."))

        self.c_tema = QComboBox()
        self.c_tema.addItem("Escuro", "escuro")
        self.c_tema.addItem("Claro", "claro")
        self.c_tema.setCurrentIndex(max(0, self.c_tema.findData(self.cfg.get("tema", "escuro"))))
        f.addRow("Tema:", self.c_tema)

        self.c_soltar = QSpinBox()
        self.c_soltar.setRange(0, 240)
        self.c_soltar.setSuffix(" min")
        self.c_soltar.setValue(int(self.cfg.get("soltar_ia_apos_minutos", 5)))
        f.addRow("Soltar a IA da placa depois de:", self.c_soltar)
        f.addRow("", _nota("Tempo sem uso. 0 = nunca soltar."))

        self.c_restaurar = QCheckBox("Devolver o que estava copiado antes (Ctrl+C)")
        self.c_restaurar.setChecked(bool(self.cfg.get("restaurar_area_de_transferencia", True)))
        f.addRow("", self.c_restaurar)

        self.c_iniciar = QCheckBox("Iniciar com o Windows")
        self.c_iniciar.setChecked(self.inicia_windows)
        f.addRow("", self.c_iniciar)
        return w

    # ------------------------------------------------------------- IA
    def _aba_ia(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        linha = QHBoxLayout()
        self.r_local = QRadioButton("Local (no seu PC)")
        self.r_online = QRadioButton("Online")
        (self.r_online if self.cfg.get("provedor") == "online" else self.r_local).setChecked(True)
        linha.addWidget(QLabel("Usar IA:"))
        linha.addWidget(self.r_local)
        linha.addWidget(self.r_online)
        linha.addStretch()
        lay.addLayout(linha)

        # --- local
        loc = self.cfg.setdefault("local", {})
        self.g_local = QGroupBox("IA local")
        fl = QFormLayout(self.g_local)
        self.c_modelo = QComboBox()
        pasta = caminho("modelos")
        modelos = sorted(p.name for p in pasta.glob("*.gguf")) if pasta.exists() else []
        for nome in modelos:
            self.c_modelo.addItem(nome, f"modelos/{nome}")
        atual = loc.get("modelo", "")
        if self.c_modelo.findData(atual) < 0 and atual:
            self.c_modelo.addItem(f"{atual} (não encontrado)", atual)
        self.c_modelo.setCurrentIndex(max(0, self.c_modelo.findData(atual)))
        fl.addRow("Modelo:", self.c_modelo)
        fl.addRow("", _nota("Para baixar outro modelo, use o baixar_modelo.bat (ou o preparar.py)."))

        self.c_camadas = QSpinBox()
        self.c_camadas.setRange(0, 999)
        self.c_camadas.setValue(int(loc.get("camadas_na_placa", 99)))
        fl.addRow("Camadas na placa de vídeo:", self.c_camadas)
        fl.addRow("", _nota("99 = tudo na placa (mais rápido). 0 = só o processador."))
        lay.addWidget(self.g_local)

        # --- online
        onl = self.cfg.setdefault("online", {})
        self.g_online = QGroupBox("IA online (formato OpenAI)")
        fo = QFormLayout(self.g_online)
        self.c_url = QLineEdit(onl.get("url", "https://api.openai.com/v1"))
        self.c_chave = QLineEdit(onl.get("chave", ""))
        self.c_chave.setEchoMode(QLineEdit.Password)
        self.c_modelo_online = QLineEdit(onl.get("modelo", ""))
        fo.addRow("Endereço:", self.c_url)
        fo.addRow("Chave:", self.c_chave)
        fo.addRow("Modelo:", self.c_modelo_online)
        fo.addRow("", _nota("A chave fica guardada no configuracoes.json, sem proteção. Online, o texto sai do seu PC."))
        lay.addWidget(self.g_online)

        # --- comum
        fc = QFormLayout()
        self.c_temp = QDoubleSpinBox()
        self.c_temp.setRange(0.0, 1.5)
        self.c_temp.setSingleStep(0.1)
        self.c_temp.setValue(float(self.cfg.get("temperatura", 0.2)))
        fc.addRow("Criatividade (temperatura):", self.c_temp)
        fc.addRow("", _nota("Baixo = mais fiel ao seu texto. Para correção, use 0.1 a 0.3."))
        lay.addLayout(fc)

        lay.addWidget(QLabel("Regras gerais (valem para todas as ações):"))
        self.c_regras = QPlainTextEdit(self.acoes.regras_gerais)
        lay.addWidget(self.c_regras, 1)

        self.r_local.toggled.connect(self._atualizar_provedor)
        self._atualizar_provedor()
        return w

    def _atualizar_provedor(self) -> None:
        local = self.r_local.isChecked()
        self.g_local.setEnabled(local)
        self.g_online.setEnabled(not local)

    # ------------------------------------------------------------- Ações
    def _aba_acoes(self) -> QWidget:
        w = QWidget()
        divisor = QSplitter(Qt.Horizontal)

        # esquerda: lista + botões
        esq = QWidget()
        le = QVBoxLayout(esq)
        le.setContentsMargins(0, 0, 0, 0)
        self.lista = QListWidget()
        self.lista.currentRowChanged.connect(self._abrir_acao)
        le.addWidget(self.lista, 1)
        linha = QHBoxLayout()
        for texto, func in (("Nova", self._nova), ("Apagar", self._apagar),
                            ("Subir", lambda: self._mover(-1)), ("Descer", lambda: self._mover(1))):
            b = QPushButton(texto)
            b.clicked.connect(func)
            linha.addWidget(b)
        le.addLayout(linha)

        # direita: edição
        dir_ = QWidget()
        ld = QVBoxLayout(dir_)
        ld.setContentsMargins(0, 0, 0, 0)
        f = QFormLayout()
        self.c_nome = QLineEdit()
        self.c_nome.textEdited.connect(self._nome_mudou)
        f.addRow("Nome do botão:", self.c_nome)
        self.c_atalho_acao = CampoAtalho()
        f.addRow("Atalho direto:", self.c_atalho_acao)
        ld.addLayout(f)
        self.l_sem_ia = _nota("Esta ação é feita sem IA. Não precisa de instrução.")
        ld.addWidget(self.l_sem_ia)
        ld.addWidget(QLabel("Instrução para a IA:"))
        self.c_instrucao = QPlainTextEdit()
        ld.addWidget(self.c_instrucao, 2)

        ld.addWidget(QLabel("Exemplos (antes e depois). Ajudam a IA a acertar:"))
        self.t_exemplos = QTableWidget(0, 2)
        self.t_exemplos.setHorizontalHeaderLabels(["Antes", "Depois"])
        self.t_exemplos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.t_exemplos.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.t_exemplos.setWordWrap(True)
        self.t_exemplos.setSelectionBehavior(QAbstractItemView.SelectRows)
        ld.addWidget(self.t_exemplos, 2)
        le2 = QHBoxLayout()
        b = QPushButton("Novo exemplo")
        b.clicked.connect(lambda: self._linha_exemplo("", ""))
        le2.addWidget(b)
        b = QPushButton("Apagar exemplo")
        b.clicked.connect(self._apagar_exemplo)
        le2.addWidget(b)
        le2.addStretch()
        ld.addLayout(le2)
        self._painel = dir_

        divisor.addWidget(esq)
        divisor.addWidget(dir_)
        divisor.setSizes([220, 600])
        QVBoxLayout(w).addWidget(divisor)

        for a in self.acoes.lista:
            self.lista.addItem(a.nome)
        if self.acoes.lista:
            self.lista.setCurrentRow(0)
        else:
            self._painel.setEnabled(False)
        return w

    def _guardar_acao(self) -> None:
        """Copia o que está na tela para a ação aberta."""
        if not (0 <= self._atual < len(self.acoes.lista)):
            return
        a = self.acoes.lista[self._atual]
        a.nome = self.c_nome.text().strip()
        a.atalho = self.c_atalho_acao.texto()
        a.instrucao = self.c_instrucao.toPlainText().strip()
        a.exemplos = []
        for r in range(self.t_exemplos.rowCount()):
            antes = (self.t_exemplos.item(r, 0) or QTableWidgetItem()).text().strip()
            depois = (self.t_exemplos.item(r, 1) or QTableWidgetItem()).text().strip()
            if antes and depois:
                a.exemplos.append(Exemplo(antes, depois))

    def _abrir_acao(self, i: int) -> None:
        self._guardar_acao()
        self._atual = i
        ok = 0 <= i < len(self.acoes.lista)
        self._painel.setEnabled(ok)
        if not ok:
            return
        a = self.acoes.lista[i]
        self.c_nome.setText(a.nome)
        self.c_atalho_acao.definir(a.atalho)
        self.c_instrucao.setPlainText(a.instrucao)
        sem_ia = a.tipo != "ia"
        self.l_sem_ia.setVisible(sem_ia)
        self.c_instrucao.setEnabled(not sem_ia)
        self.t_exemplos.setEnabled(not sem_ia)
        self.t_exemplos.setRowCount(0)
        for ex in a.exemplos:
            self._linha_exemplo(ex.antes, ex.depois)

    def _linha_exemplo(self, antes: str, depois: str) -> None:
        r = self.t_exemplos.rowCount()
        self.t_exemplos.insertRow(r)
        self.t_exemplos.setItem(r, 0, QTableWidgetItem(antes))
        self.t_exemplos.setItem(r, 1, QTableWidgetItem(depois))

    def _apagar_exemplo(self) -> None:
        r = self.t_exemplos.currentRow()
        if r >= 0:
            self.t_exemplos.removeRow(r)

    def _nome_mudou(self, texto: str) -> None:
        item = self.lista.currentItem()
        if item:
            item.setText(texto or "(sem nome)")

    def _nova(self) -> None:
        self._guardar_acao()
        self.acoes.lista.append(Acao(nome="Nova ação", instrucao="Corrija os erros e ..."))
        self.lista.addItem("Nova ação")
        self.lista.setCurrentRow(len(self.acoes.lista) - 1)
        self.c_nome.setFocus()
        self.c_nome.selectAll()

    def _apagar(self) -> None:
        i = self.lista.currentRow()
        if i < 0:
            return
        nome = self.acoes.lista[i].nome
        if QMessageBox.question(self, "Apagar", f"Apagar a ação \"{nome}\"?") != QMessageBox.Yes:
            return
        self._atual = -1  # não guarda a que vai sumir
        del self.acoes.lista[i]
        self.lista.takeItem(i)

    def _mover(self, passo: int) -> None:
        i = self.lista.currentRow()
        j = i + passo
        if i < 0 or not (0 <= j < len(self.acoes.lista)):
            return
        self._guardar_acao()
        lst = self.acoes.lista
        lst[i], lst[j] = lst[j], lst[i]
        self._atual = -1
        self.lista.blockSignals(True)
        self.lista.insertItem(j, self.lista.takeItem(i))
        self.lista.blockSignals(False)
        self.lista.setCurrentRow(j)
        self._abrir_acao(j)

    # ------------------------------------------------------------- salvar
    def _salvar(self) -> None:
        self._guardar_acao()

        menu = self.c_atalho_menu.texto()
        if not menu:
            return self._erro("O atalho do menu não pode ficar vazio.")
        usados = {menu: "o menu"}
        for a in self.acoes.lista:
            if not a.nome:
                return self._erro("Tem uma ação sem nome.")
            if a.tipo == "ia" and not a.instrucao:
                return self._erro(f"A ação \"{a.nome}\" está sem instrução.")
            if a.atalho:
                if a.atalho in usados:
                    return self._erro(f"O atalho {a.atalho} já é usado por {usados[a.atalho]}.")
                usados[a.atalho] = f"\"{a.nome}\""

        c = self.cfg
        c["atalho_menu"] = menu
        c["tema"] = self.c_tema.currentData()
        c["soltar_ia_apos_minutos"] = self.c_soltar.value()
        c["restaurar_area_de_transferencia"] = self.c_restaurar.isChecked()
        c["provedor"] = "local" if self.r_local.isChecked() else "online"
        c["temperatura"] = round(self.c_temp.value(), 2)
        if self.c_modelo.currentData():
            c["local"]["modelo"] = self.c_modelo.currentData()
        c["local"]["camadas_na_placa"] = self.c_camadas.value()
        c["online"]["url"] = self.c_url.text().strip()
        c["online"]["chave"] = self.c_chave.text().strip()
        c["online"]["modelo"] = self.c_modelo_online.text().strip()
        self.acoes.regras_gerais = self.c_regras.toPlainText().strip()
        self.inicia_windows = self.c_iniciar.isChecked()
        self.accept()

    def _erro(self, msg: str) -> None:
        QMessageBox.warning(self, "Não deu para salvar", msg)
