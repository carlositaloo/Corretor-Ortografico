"""Teclado e área de transferência: copiar a seleção, colar o resultado, atalhos."""

from __future__ import annotations

import ctypes
import logging
import time

import pyperclip
from pynput import keyboard

log = logging.getLogger(__name__)

user32 = ctypes.windll.user32
_tec = keyboard.Controller()

# Teclas modificadoras (códigos virtuais do Windows): Shift, Ctrl, Alt, Win esq./dir.
_VK_MODIFICADORES = (0x10, 0x11, 0x12, 0x5B, 0x5C)

_NOMES = {
    "ctrl": "<ctrl>", "control": "<ctrl>",
    "shift": "<shift>",
    "alt": "<alt>",
    "win": "<cmd>", "windows": "<cmd>", "cmd": "<cmd>",
    "espaco": "<space>", "espaço": "<space>", "space": "<space>",
    "enter": "<enter>", "tab": "<tab>", "esc": "<esc>",
}


def converter_atalho(texto: str) -> str:
    """'ctrl+shift+space' -> '<ctrl>+<shift>+<space>' (formato do pynput)."""
    partes = []
    for p in texto.lower().replace(" ", "").split("+"):
        if not p:
            continue
        if p in _NOMES:
            partes.append(_NOMES[p])
        elif len(p) == 1:
            partes.append(p)
        else:  # f1, f2, home, etc.
            partes.append(f"<{p}>")
    return "+".join(partes)


# ------------------------------------------------------------------ janela
def janela_ativa() -> int:
    return user32.GetForegroundWindow()


def focar_janela(hwnd: int) -> None:
    """Traz uma janela para frente.

    O Windows bloqueia SetForegroundWindow vindo de outro programa; ligar
    a nossa thread à thread da janela da frente (AttachThreadInput) libera.
    """
    if not hwnd:
        return
    kernel32 = ctypes.windll.kernel32
    frente = user32.GetForegroundWindow()
    t_frente = user32.GetWindowThreadProcessId(frente, None)
    t_nossa = kernel32.GetCurrentThreadId()
    ligou = t_frente != t_nossa and user32.AttachThreadInput(t_nossa, t_frente, True)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if ligou:
            user32.AttachThreadInput(t_nossa, t_frente, False)


# ------------------------------------------------------------------ teclas
def _esperar_soltar_modificadores(limite_s: float = 1.5) -> None:
    """Espera o usuário soltar Ctrl/Shift/Alt/Win do atalho.

    Sem isso, um Ctrl+C enviado com Shift ainda apertado vira Ctrl+Shift+C.
    """
    fim = time.time() + limite_s
    while time.time() < fim:
        if not any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in _VK_MODIFICADORES):
            return
        time.sleep(0.02)


def _ctrl_mais(tecla: str) -> None:
    with _tec.pressed(keyboard.Key.ctrl):
        _tec.press(tecla)
        _tec.release(tecla)


# ------------------------------------------------------------------ copiar / colar
def copiar_selecao(espera_s: float = 0.6) -> tuple[str, str]:
    """Copia o texto selecionado na janela ativa.

    Devolve (texto_selecionado, conteudo_antigo_da_area_de_transferencia).
    texto_selecionado vem vazio se nada estava selecionado.
    """
    try:
        antigo = pyperclip.paste()
    except Exception:
        antigo = ""

    _esperar_soltar_modificadores()
    seq = user32.GetClipboardSequenceNumber()
    _ctrl_mais("c")

    fim = time.time() + espera_s
    while time.time() < fim:
        if user32.GetClipboardSequenceNumber() != seq:
            time.sleep(0.03)  # deixa o programa terminar de escrever
            try:
                return pyperclip.paste(), antigo
            except Exception:
                break
        time.sleep(0.02)
    return "", antigo


def colar_texto(texto: str, restaurar: str | None = None) -> None:
    """Cola o texto no lugar da seleção e, se pedido, restaura a área de transferência."""
    pyperclip.copy(texto)
    time.sleep(0.05)
    _esperar_soltar_modificadores()
    _ctrl_mais("v")
    if restaurar is not None:
        time.sleep(0.4)  # dá tempo do programa ler antes de trocar
        try:
            pyperclip.copy(restaurar)
        except Exception:
            log.warning("Não deu para restaurar a área de transferência.")


# ------------------------------------------------------------------ atalhos globais
# Modificador -> códigos virtuais do Windows que contam como ele.
_MODS_VK = {"<ctrl>": (0x11,), "<shift>": (0x10,), "<alt>": (0x12,), "<cmd>": (0x5B, 0x5C)}


def _so_se_exato(atalho: str, func):
    """Só dispara se NÃO houver modificador a mais apertado.

    Sem isso, ctrl+shift+space também ativaria o ctrl+space.
    """
    usados = set(atalho.split("+"))
    sobrando = [vk for nome, vks in _MODS_VK.items() if nome not in usados for vk in vks]

    def chamar():
        if any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in sobrando):
            return
        func()

    return chamar


class Atalhos:
    """Escuta atalhos em qualquer programa. callbacks: {'ctrl+space': funcao}."""

    def __init__(self):
        self._ouvinte: keyboard.GlobalHotKeys | None = None

    def registrar(self, callbacks: dict[str, callable]) -> list[str]:
        self.parar()
        mapa, erros = {}, []
        for texto, func in callbacks.items():
            conv = converter_atalho(texto)
            try:
                keyboard.HotKey.parse(conv)  # valida
                mapa[conv] = _so_se_exato(conv, func)
            except Exception:
                erros.append(texto)
                log.error("Atalho inválido: %s", texto)
        if mapa:
            self._ouvinte = keyboard.GlobalHotKeys(mapa)
            self._ouvinte.daemon = True
            self._ouvinte.start()
            log.info("Atalhos ativos: %s", ", ".join(callbacks))
        return erros

    def parar(self) -> None:
        if self._ouvinte:
            self._ouvinte.stop()
            self._ouvinte = None
