"""Teste da IA sem abrir o aplicativo.

Uso: .venv\\Scripts\\python.exe testar_ia.py
Liga o motor, roda frases de teste em cada ação e mostra o tempo.
"""

import sys
import time

from corretor.config import carregar_acoes, carregar_config
from corretor.ia import ClienteIA, ErroIA
from corretor.motor import Motor

FRASES = [
    "bom dia, vou verificar o chamdo e ja te retorno, provavlemnte e problema na vpn",
    "nao consigoa acessar o sistema desdeontem, aparece erro de senha invalida mas a senha ta certa",
    "pessoal a reuniao foi remarcada pra quinta as 14h, quem nao puder me avisa por favor",
    "vc pode me mandar o arquivo q o cliente enviou?",
    "o computadro do setor finaceiro ta muito lento acho q e falta de memoria",
]

ACOES_TESTE = ["Corrigir", "Profissional", "E-mail"]


def main() -> None:
    cfg = carregar_config()
    acoes = carregar_acoes()
    motor = Motor(cfg["local"])
    t = time.time()
    motor.ligar()
    if not motor.esperar_pronto():
        sys.exit("Motor não ligou. Veja logs/motor.log")
    print(f"Motor pronto em {time.time() - t:.1f}s\n")

    cliente = ClienteIA(motor.url_base + "/v1", local=True)
    try:
        for nome in ACOES_TESTE:
            acao = next(a for a in acoes.lista if a.nome == nome)
            frases = FRASES if nome == "Corrigir" else FRASES[:2]
            print(f"===== {nome} =====")
            for f in frases:
                t = time.time()
                try:
                    r = cliente.executar(acao, acoes.regras_gerais, f, cfg.get("temperatura", 0.2))
                except ErroIA as e:
                    r = f"[ERRO] {e}"
                print(f"ANTES : {f}\nDEPOIS: {r}\n({time.time() - t:.2f}s)\n")
    finally:
        motor.desligar()


if __name__ == "__main__":
    main()
