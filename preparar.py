"""Baixa o motor (llama-server) e o modelo para dentro da pasta do projeto.

Uso:
  python preparar.py                 -> motor + Gemma 3 4B (padrão)
  python preparar.py --modelo qwen7b -> motor + Qwen 2.5 7B
  python preparar.py --so-modelo     -> não baixa o motor de novo
  python preparar.py --cuda          -> motor CUDA (mais pesado, ~630 MB)

Nada é instalado no Windows: tudo fica em motor/ e modelos/.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PASTA_MOTOR = RAIZ / "motor"
PASTA_MODELOS = RAIZ / "modelos"

MODELOS = {
    "gemma4b": ("bartowski/google_gemma-3-4b-it-GGUF", "google_gemma-3-4b-it-Q4_K_M.gguf"),
    "qwen1.5b": ("bartowski/Qwen2.5-1.5B-Instruct-GGUF", "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"),
    "qwen7b": ("bartowski/Qwen2.5-7B-Instruct-GGUF", "Qwen2.5-7B-Instruct-Q4_K_M.gguf"),
}


def baixar(url: str, destino: Path) -> None:
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    req = urllib.request.Request(url, headers={"User-Agent": "corretor-preparar"})
    with urllib.request.urlopen(req) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        feito = 0
        while bloco := r.read(1 << 20):
            f.write(bloco)
            feito += len(bloco)
            if total:
                print(f"\r  {feito / 2**20:,.0f} de {total / 2**20:,.0f} MB ({feito * 100 // total}%)",
                      end="", flush=True)
    print()
    tmp.replace(destino)


def baixar_motor(cuda: bool) -> None:
    print("Procurando a versão mais nova do llama.cpp...")
    req = urllib.request.Request(
        "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=10",
        headers={"User-Agent": "corretor-preparar"},
    )
    with urllib.request.urlopen(req) as r:
        versoes = json.load(r)

    padrao = r"^llama-b\d+-bin-win-cuda-12\.\d+-x64\.zip$" if cuda else r"^llama-b\d+-bin-win-vulkan-x64\.zip$"
    for v in versoes:
        nomes = {a["name"]: a["browser_download_url"] for a in v.get("assets", [])}
        principal = next((n for n in nomes if re.match(padrao, n)), None)
        if principal:
            break
    else:
        sys.exit("Não achei o arquivo do motor para Windows.")

    pacotes = [principal]
    if cuda:  # o CUDA precisa das DLLs de runtime à parte
        pacotes += [n for n in nomes if re.match(r"^cudart-llama-bin-win-cuda-12\.\d+-x64\.zip$", n)]

    if PASTA_MOTOR.exists():
        shutil.rmtree(PASTA_MOTOR)
    PASTA_MOTOR.mkdir()
    for nome in pacotes:
        print(f"Baixando {nome} ({v['tag_name']})")
        zip_ = PASTA_MOTOR / nome
        baixar(nomes[nome], zip_)
        with zipfile.ZipFile(zip_) as z:
            z.extractall(PASTA_MOTOR)
        zip_.unlink()

    # Alguns pacotes vêm com subpasta: traz tudo para motor/.
    exe = next(PASTA_MOTOR.rglob("llama-server.exe"), None)
    if not exe:
        sys.exit("llama-server.exe não veio no pacote.")
    if exe.parent != PASTA_MOTOR:
        for item in exe.parent.iterdir():
            shutil.move(str(item), PASTA_MOTOR / item.name)
    print("Motor pronto em", PASTA_MOTOR)


def baixar_modelo(chave: str) -> Path:
    repo, arquivo = MODELOS[chave]
    PASTA_MODELOS.mkdir(exist_ok=True)
    destino = PASTA_MODELOS / arquivo
    if destino.exists():
        print("Modelo já existe:", destino.name)
        return destino
    print(f"Baixando modelo {arquivo}")
    baixar(f"https://huggingface.co/{repo}/resolve/main/{arquivo}", destino)
    return destino


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--modelo", choices=MODELOS, default="gemma4b")
    p.add_argument("--so-modelo", action="store_true")
    p.add_argument("--cuda", action="store_true")
    a = p.parse_args()

    if not a.so_modelo:
        baixar_motor(a.cuda)
    modelo = baixar_modelo(a.modelo)

    # Aponta o configuracoes.json para o modelo baixado.
    arq = RAIZ / "configuracoes.json"
    cfg = json.loads(arq.read_text(encoding="utf-8"))
    cfg["local"]["modelo"] = f"modelos/{modelo.name}"
    arq.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Tudo pronto. Modelo ativo:", modelo.name)


if __name__ == "__main__":
    main()
