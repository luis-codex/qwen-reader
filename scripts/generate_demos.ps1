#!/usr/bin/env pwsh
# ============================================================================
#  qwen-reader demo generator
#  Generates audio samples in 10 languages to showcase model capabilities.
#  Each sample uses the best native speaker for that language.
# ============================================================================

$ErrorActionPreference = "Continue"
$QR = "qwen-reader"
$OUT = Join-Path $PSScriptRoot "..\demos"
if (-not (Test-Path $OUT)) { New-Item -ItemType Directory -Force -Path $OUT | Out-Null }
$OUT = (Resolve-Path $OUT).Path

Write-Host "`n🎙️  qwen-reader demo generator" -ForegroundColor Cyan
Write-Host "   Output → $OUT`n" -ForegroundColor DarkGray

# ── Spanish  (Vivian — bright female, native Chinese but great Spanish) ──
& $QR speak "Buenos días. Bienvenidos a qwen-reader, su herramienta de texto a voz. Convierte artículos, documentos y cualquier texto en audio natural con un solo comando." `
    --lang Spanish --speaker Vivian -o $OUT -n "demo_spanish"

# ── English  (Ryan — dynamic male, native English) ──
& $QR speak "Welcome to qwen-reader. Transform any article, document, or piece of text into natural-sounding audio with a single command. It is that simple." `
    --lang English --speaker Ryan -o $OUT -n "demo_english"

# ── Chinese  (Serena — warm female, native Chinese) ──
& $QR speak "欢迎使用 qwen-reader。只需一条命令，即可将任何文章、文档或文本转换为自然流畅的语音。" `
    --lang Chinese --speaker Serena -o $OUT -n "demo_chinese"

# ── Japanese  (Ono_Anna — playful female, native Japanese) ──
& $QR speak "qwen-readerへようこそ。たった一つのコマンドで、記事やドキュメント、あらゆるテキストを自然な音声に変換できます。" `
    --lang Japanese --speaker Ono_Anna -o $OUT -n "demo_japanese"

# ── Korean  (Sohee — warm female, native Korean) ──
& $QR speak "qwen-reader에 오신 것을 환영합니다. 단 하나의 명령으로 기사, 문서, 모든 텍스트를 자연스러운 음성으로 변환하세요." `
    --lang Korean --speaker Sohee -o $OUT -n "demo_korean"

# ── French  (Aiden — sunny American male, good multilingual) ──
& $QR speak "Bienvenue sur qwen-reader. Transformez n'importe quel article, document ou texte en audio naturel avec une seule commande." `
    --lang French --speaker Aiden -o $OUT -n "demo_french"

# ── German  (Aiden) ──
& $QR speak "Willkommen bei qwen-reader. Verwandeln Sie jeden Artikel, jedes Dokument oder jeden Text mit einem einzigen Befehl in natürlich klingende Sprache." `
    --lang German --speaker Aiden -o $OUT -n "demo_german"

# ── Italian  (Vivian) ──
& $QR speak "Benvenuti in qwen-reader. Trasforma qualsiasi articolo, documento o testo in audio naturale con un solo comando." `
    --lang Italian --speaker Vivian -o $OUT -n "demo_italian"

# ── Portuguese  (Ryan — dynamic English male) ──
& $QR speak "Bem-vindos ao qwen-reader. Transforme qualquer artigo, documento ou texto em áudio natural com um único comando." `
    --lang Portuguese --speaker Ryan -o $OUT -n "demo_portuguese"

# ── Russian  (Aiden) ──
& $QR speak "Добро пожаловать в qwen-reader. Преобразуйте любую статью, документ или текст в естественную речь одной командой." `
    --lang Russian --speaker Aiden -o $OUT -n "demo_russian"

Write-Host "`n✅ All demos generated in: $OUT" -ForegroundColor Green
Write-Host "   Run 'qwen-reader list -o $OUT' to see them.`n"
