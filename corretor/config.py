"""Leitura das configurações (configuracoes.json) e das ações (acoes.toml)."""

from __future__ import annotations

import json
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# Pasta raiz do projeto (onde ficam os arquivos de configuração).
# No .exe (PyInstaller) é a pasta do Corretor.exe; no Python, a pasta do projeto.
if getattr(sys, "frozen", False):
    RAIZ = Path(sys.executable).resolve().parent
else:
    RAIZ = Path(__file__).resolve().parent.parent
ARQ_CONFIG = RAIZ / "configuracoes.json"
ARQ_ACOES = RAIZ / "acoes.toml"
PASTA_LOGS = RAIZ / "logs"


@dataclass
class Exemplo:
    antes: str
    depois: str


@dataclass
class Acao:
    nome: str
    instrucao: str
    atalho: str = ""
    tipo: str = "ia"  # "ia" ou "maiusculas"
    exemplos: list[Exemplo] = field(default_factory=list)


@dataclass
class Acoes:
    regras_gerais: str
    lista: list[Acao]


def carregar_config() -> dict:
    with open(ARQ_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def salvar_config(cfg: dict) -> None:
    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def caminho(rel: str) -> Path:
    """Converte um caminho do config (relativo à raiz) em absoluto."""
    p = Path(rel)
    return p if p.is_absolute() else RAIZ / p


def carregar_acoes() -> Acoes:
    with open(ARQ_ACOES, "rb") as f:
        dados = tomllib.load(f)

    lista: list[Acao] = []
    for bruto in dados.get("acao", []):
        nome = str(bruto.get("nome", "")).strip()
        if not nome:
            continue
        lista.append(
            Acao(
                nome=nome,
                instrucao=str(bruto.get("instrucao", "")).strip(),
                atalho=str(bruto.get("atalho", "")).strip(),
                tipo=str(bruto.get("tipo", "ia")).strip() or "ia",
                exemplos=[
                    Exemplo(str(e.get("antes", "")).strip(), str(e.get("depois", "")).strip())
                    for e in bruto.get("exemplo", [])
                    if e.get("antes") and e.get("depois")
                ],
            )
        )
    return Acoes(regras_gerais=str(dados.get("regras_gerais", "")).strip(), lista=lista)


# --------------------------------------------------------------------- salvar
_CABECALHO_ACOES = """\
# ============================================================
#  Ações do Corretor
#  Este arquivo é salvo pela janela de Configurações.
#  Pode editar à mão também; depois use "Recarregar" no ícone.
#
#  nome      -> texto do botão
#  atalho    -> atalho direto (opcional). Ex.: "ctrl+j". "" = nenhum
#  instrucao -> o que a IA deve fazer
#  [[acao.exemplo]] -> exemplos de antes e depois
#  tipo = "maiusculas" -> faz sem IA (instantâneo)
# ============================================================
"""


def _toml_linha(s: str) -> str:
    """Texto curto entre aspas, com escapes do TOML."""
    return json.dumps(s, ensure_ascii=False)  # o formato do JSON vale no TOML


def _toml_bloco(s: str) -> str:
    """Texto de várias linhas entre aspas triplas."""
    s = s.replace("\\", "\\\\").replace('"""', '""\\"')
    return f'"""\n{s}\n"""'  # a quebra antes do fim evita colar aspas no fechamento


def salvar_acoes(acoes: Acoes) -> None:
    partes = [_CABECALHO_ACOES, f"regras_gerais = {_toml_bloco(acoes.regras_gerais)}\n"]
    for a in acoes.lista:
        partes.append("[[acao]]")
        partes.append(f"nome = {_toml_linha(a.nome)}")
        partes.append(f"atalho = {_toml_linha(a.atalho)}")
        if a.tipo != "ia":
            partes.append(f"tipo = {_toml_linha(a.tipo)}")
        partes.append(f"instrucao = {_toml_bloco(a.instrucao)}")
        for ex in a.exemplos:
            partes.append("  [[acao.exemplo]]")
            antes = _toml_bloco(ex.antes) if "\n" in ex.antes else _toml_linha(ex.antes)
            depois = _toml_bloco(ex.depois) if "\n" in ex.depois else _toml_linha(ex.depois)
            partes.append(f"  antes = {antes}")
            partes.append(f"  depois = {depois}")
        partes.append("")
    texto = "\n".join(partes)
    tomllib.loads(texto)  # confere antes de gravar: nunca salva um arquivo quebrado
    tmp = ARQ_ACOES.with_suffix(".tmp")
    tmp.write_text(texto, encoding="utf-8")
    tmp.replace(ARQ_ACOES)
