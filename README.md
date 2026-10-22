# Corretor Ortográfico

### **Corrija e melhore qualquer texto do seu PC com IA local, em português do Brasil:**

> Selecione o texto em qualquer programa, aperte `ctrl+space`, escolha a ação, e o texto corrigido já aparece no lugar.

## ✨ O que é o Corretor Ortográfico?

O Corretor Ortográfico é um app para Windows que **corrige, reescreve e melhora o seu texto com uma IA que roda no seu próprio computador**.
Com um atalho, ele funciona em qualquer lugar: e-mail, WhatsApp Web, Teams, ticket, Word, navegador...

Ele foi feito para quem digita rápido e erra muito. A IA entende a frase toda, então conserta letra trocada, palavra colada, acento e crase de uma vez só.

Este projeto foi **inspirado no [Writing Tools](https://github.com/theJayTea/WritingTools)**, de [Jesai (theJayTea)](https://github.com/theJayTea) e colaboradores.
O Writing Tools é um ótimo app, multiplataforma e para qualquer idioma. O Corretor Ortográfico é uma versão menor e escrita do zero, focada em **português do Brasil** e em **IA 100% local**, sem nada para instalar. Se você quer mais recursos (resumos, chat, macOS e Linux), conheça o Writing Tools! ❤️

---

## ⚡ O que dá para fazer?

### 1️⃣ Corrigir e reescrever em qualquer programa
- Selecione _qualquer_ texto no PC e aperte `ctrl+space`.
- Escolha **Corrigir**, **Melhorar**, **Profissional**, **Amigável**, **Encurtar**, **E-mail**, **Traduzir**, **Prompt** ou **MAIÚSCULAS**.
- O texto é trocado na hora pela versão corrigida. Use `ctrl+z` para desfazer.
- No menu, as teclas `1` a `9` escolhem a ação, sem precisar do mouse.

### 2️⃣ Crie os seus próprios botões
- Na janela de **Configurações**, crie, apague, edite e mude a ordem das ações.
- Cada ação tem nome, instrução, exemplos de "antes e depois" e um **atalho direto** (por exemplo, `ctrl+j` para corrigir sem abrir o menu).

### 3️⃣ Sem memória entre textos
- Cada correção começa do zero. Um e-mail nunca se mistura com um ticket ou uma mensagem do WhatsApp.
- Isso também deixa tudo mais rápido e leve.

## 🌟 Por que usar?

- **Privado de verdade:** a IA roda no seu PC e escuta só em `127.0.0.1`. Seu texto não sai do computador e funciona sem internet.
- **Rápido:** cerca de 1 segundo por frase numa placa de vídeo comum (testado numa GTX 1660).
- **Roda em qualquer PC:** placa NVIDIA, AMD, vídeo integrado ou só o processador (pelo Vulkan).
- **Sem instalar nada:** sem Ollama, sem Python (na versão `.exe`), sem instalador. Tudo fica dentro da pasta.
- **Só o texto:** as instruções foram ajustadas para a IA devolver apenas o texto corrigido, sem comentários.
- **Não atrapalha seus jogos:** a IA sai da placa de vídeo sozinha depois de alguns minutos parada, ou quando você clica em **Pausar IA**.
- **Ícone que mostra o estado:**

| Cor do ícone "Aa" | Quando |
|---|---|
| 🔵 Azul | Pronto para usar |
| 🟡 Amarelo | Corrigindo ou ligando a IA |
| 🔴 Vermelho | IA fora da placa (pausada, ociosa ou com erro) |

## ✅ Instalação em 1 minuto

### 🪟 Windows

1. Vá na página de [Releases](../../releases) e baixe o `Corretor.zip` mais novo.
2. **Antes de extrair:** clique com o botão direito no `Corretor.zip` > **Propriedades** > marque **Desbloquear** > **OK**. (Veja "O Windows bloqueou?" mais abaixo.)
3. Extraia numa pasta sua (recomendado: `Documentos`).
4. Dê dois cliques em `baixar_modelo.bat` e escolha a IA (só na primeira vez):

| Opção | Tamanho | Para quem |
|---|---|---|
| **1) Gemma 3 4B** ⭐ recomendado | ~2,5 GB | Escreve melhor em português |
| 2) Qwen 2.5 1.5B | ~1 GB | PC fraco ou com pouca memória. Erra mais |

5. Abra o `Corretor.exe`. O ícone "Aa" aparece perto do relógio.

_Obs.: o app é portátil e guarda as configurações na própria pasta. Não extraia em `Arquivos de Programas`, senão ele não consegue salvar._

_O antivírus pode estranhar um `.exe` novo. É alarme falso, mas talvez peça para liberar._

**Dica:** clique com o botão direito no ícone "Aa" e marque **Iniciar com o Windows**.

### 🛡️ O Windows bloqueou?

No Windows 11, o **Controle Inteligente de Aplicativos** (Smart App Control) bloqueia arquivos baixados da internet que não têm assinatura digital paga. A mensagem só tem "OK" ou "Procurar um aplicativo na Microsoft Store". Não é vírus: o Corretor só não é assinado.

Para liberar:
1. Apague a pasta que você extraiu.
2. Clique com o botão direito no `Corretor.zip` > **Propriedades**.
3. Embaixo, marque **Desbloquear** e clique em **OK**.
4. Extraia de novo e rode o `baixar_modelo.bat`.

Se o seu Windows não mostrar a caixa **Desbloquear**, abra o PowerShell na pasta extraída e rode:

```
Get-ChildItem -Recurse | Unblock-File
```

Não precisa desligar o Controle Inteligente de Aplicativos.

## 💻 Rodar pelo código-fonte (Python 3.12 ou mais novo)

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python preparar.py
.venv\Scripts\pythonw iniciar.pyw
```

O `preparar.py` baixa o motor ([llama.cpp](https://github.com/ggml-org/llama.cpp)) e o modelo para dentro da pasta.

| Opção | O que faz |
|---|---|
| `--modelo gemma4b` | Gemma 3 4B (padrão, recomendado) |
| `--modelo qwen1.5b` | Qwen 2.5 1.5B, mais leve |
| `--modelo qwen7b` | Qwen 2.5 7B, maior (~4,7 GB) |
| `--cuda` | Motor CUDA para placas NVIDIA (~630 MB). O padrão (Vulkan) já usa a placa |
| `--so-modelo` | Baixa só o modelo |

Para gerar o `.exe`: `.venv\Scripts\pip install pyinstaller` e depois `.venv\Scripts\python gerar_exe.py`.

## 🗂️ Arquivos

| Arquivo | Função |
|---|---|
| `acoes.toml` | As ações: nome, instrução, atalho e exemplos |
| `configuracoes.json` | Atalho do menu, tema, IA local ou online |
| `corretor/` | O código do app (Python + PySide6) |
| `preparar.py` | Baixa o motor e o modelo |
| `baixar_modelo.bat` | Baixa o modelo na versão `.exe` |
| `gerar_exe.py` | Gera o `Corretor.exe` |
| `testar_ia.py` | Testa a IA sem abrir o app |

## 🌐 Modo online (opcional)

Na aba **IA** das Configurações dá para usar uma IA online compatível com a API da OpenAI.
Atenção: nesse modo o texto sai do seu PC, e a chave fica salva sem proteção no `configuracoes.json`.

## 🙏 Créditos

- [Writing Tools](https://github.com/theJayTea/WritingTools), de [theJayTea](https://github.com/theJayTea) e colaboradores: a inspiração para a ideia, o menu com atalho e os botões.
- [llama.cpp](https://github.com/ggml-org/llama.cpp): o motor que roda a IA.
- [Gemma 3](https://ai.google.dev/gemma) (Google) e [Qwen 2.5](https://github.com/QwenLM/Qwen2.5) (Alibaba): os modelos. Arquivos GGUF por [bartowski](https://huggingface.co/bartowski).
- [PySide6](https://doc.qt.io/qtforpython-6/), [pynput](https://github.com/moses-palmer/pynput) e [pyperclip](https://github.com/asweigart/pyperclip).

## 📄 Licença

Distribuído sob a licença [MIT](LICENSE). Livre para usar, mudar e compartilhar.
Os modelos de IA têm licenças próprias ([Gemma](https://ai.google.dev/gemma/terms), [Qwen](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)).
