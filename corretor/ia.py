"""Monta o pedido para a IA e limpa a resposta.

Funciona igual para o motor local e para uma IA online, porque os dois
usam o mesmo formato (/v1/chat/completions, padrão OpenAI).
Cada pedido é independente: nenhuma conversa anterior é enviada.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request

from .config import Acao

log = logging.getLogger(__name__)

ERRO_INVALIDO = "ERRO_TEXTO_INVALIDO"
_RE_TEXTO = re.compile(r"<texto>\s*(.*?)\s*(?:</texto>|$)", re.DOTALL | re.IGNORECASE)


class ErroIA(Exception):
    """Erro com mensagem amigável para mostrar ao usuário."""


def _embrulhar(t: str) -> str:
    return f"<texto>\n{t}\n</texto>"


def montar_mensagens(acao: Acao, regras_gerais: str, texto: str) -> list[dict]:
    sistema = f"{regras_gerais}\n\nTarefa:\n{acao.instrucao}"
    msgs = [{"role": "system", "content": sistema}]
    # Exemplos de antes/depois: ensinam o formato ao modelo pequeno.
    for ex in acao.exemplos:
        msgs.append({"role": "user", "content": _embrulhar(ex.antes)})
        msgs.append({"role": "assistant", "content": _embrulhar(ex.depois)})
    msgs.append({"role": "user", "content": _embrulhar(texto)})
    return msgs


def limpar_resposta(bruto: str) -> str:
    """Pega só o que está entre <texto> e </texto>."""
    m = _RE_TEXTO.search(bruto)
    limpo = m.group(1) if m else bruto
    # Rede de segurança: tira marcas soltas e cercas de código que o modelo inventar.
    limpo = re.sub(r"</?texto>", "", limpo, flags=re.IGNORECASE).strip()
    if limpo.startswith("```") and limpo.endswith("```"):
        limpo = limpo.strip("`").split("\n", 1)[-1].strip()
    return limpo


def _manter_espacos(original: str, novo: str) -> str:
    """Devolve os espaços/quebras do começo e do fim que o usuário selecionou."""
    ini = original[: len(original) - len(original.lstrip())]
    fim = original[len(original.rstrip()):]
    return f"{ini}{novo}{fim}"


class ClienteIA:
    def __init__(self, url_base: str, modelo: str = "", chave: str = "", local: bool = True):
        self.url = url_base.rstrip("/") + "/chat/completions"
        self.modelo = modelo
        self.chave = chave
        self.local = local

    def executar(self, acao: Acao, regras_gerais: str, texto: str, temperatura: float) -> str:
        nucleo = texto.strip()
        corpo = {
            "messages": montar_mensagens(acao, regras_gerais, nucleo),
            "temperature": temperatura,
            # Resposta nunca precisa ser muito maior que o texto (e-mail cresce um pouco).
            "max_tokens": max(256, len(nucleo) // 2 + 300),
            "stream": False,
        }
        if self.modelo:
            corpo["model"] = self.modelo
        if self.local:
            corpo["cache_prompt"] = True  # reaproveita as instruções já lidas (mais rápido)

        cab = {"Content-Type": "application/json"}
        if self.chave:
            cab["Authorization"] = f"Bearer {self.chave}"

        req = urllib.request.Request(self.url, data=json.dumps(corpo).encode("utf-8"), headers=cab)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                dados = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode("utf-8", "replace")[:300]
            log.error("IA respondeu %s: %s", e.code, detalhe)
            raise ErroIA(f"A IA recusou o pedido ({e.code}).") from e
        except (urllib.error.URLError, TimeoutError) as e:
            log.error("Sem conexão com a IA: %s", e)
            raise ErroIA("A IA não respondeu. O motor está ligado?") from e

        bruto = dados["choices"][0]["message"]["content"] or ""
        log.debug("Resposta bruta: %r", bruto)
        limpo = limpar_resposta(bruto)
        if not limpo or ERRO_INVALIDO in limpo:
            raise ErroIA("A IA não entendeu esse texto.")
        return _manter_espacos(texto, limpo)


def alternar_maiusculas(texto: str) -> str:
    """Ação sem IA: maiúsculas, ou minúsculas se já estiver tudo maiúsculo."""
    return texto.lower() if texto.isupper() else texto.upper()
