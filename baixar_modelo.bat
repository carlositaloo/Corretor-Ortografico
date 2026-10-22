@echo off
rem Baixa o modelo de IA para a pasta modelos\ e liga ele no configuracoes.json.
rem Usado pela versao .exe, que nao tem Python. Precisa do Windows 10 ou mais novo.
cd /d "%~dp0"

echo.
echo  Qual IA voce quer baixar?
echo.
echo   1) Gemma 3 4B      (~2,5 GB)  RECOMENDADO - escreve melhor em portugues
echo   2) Qwen 2.5 1.5B   (~1 GB)    mais leve, para PC fraco - erra mais
echo.
choice /c 12 /n /m " Digite 1 ou 2: "
if errorlevel 2 (
  set "REPO=bartowski/Qwen2.5-1.5B-Instruct-GGUF"
  set "ARQ=Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
) else (
  set "REPO=bartowski/google_gemma-3-4b-it-GGUF"
  set "ARQ=google_gemma-3-4b-it-Q4_K_M.gguf"
)

if not exist modelos mkdir modelos
if exist "modelos\%ARQ%" (
  echo O modelo ja esta baixado.
  goto ativar
)

echo.
echo Baixando %ARQ%. Isso pode demorar...
curl.exe -L --fail -o "modelos\%ARQ%.parcial" "https://huggingface.co/%REPO%/resolve/main/%ARQ%"
if errorlevel 1 (
  echo Deu erro no download. Confira a internet e rode de novo.
  del "modelos\%ARQ%.parcial" 2>nul
  pause
  exit /b 1
)
ren "modelos\%ARQ%.parcial" "%ARQ%"

:ativar
rem Aponta o configuracoes.json para o modelo escolhido.
powershell -NoProfile -Command "$f='configuracoes.json'; $c=Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json; $c.local.modelo='modelos/%ARQ%'; [IO.File]::WriteAllText((Resolve-Path $f), ($c | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))"
echo.
echo Pronto! Modelo ativo: %ARQ%
echo Agora abra o Corretor.exe. Se ele ja estiver aberto, feche e abra de novo.
pause
