# Events Analyzer

Mini sistema em Python para coletar oportunidades do mundo tech, classificar por tipo e gerar um resumo diario.

## O que ele faz

- Coleta fontes RSS e paginas HTML com seletores.
- Salva os itens em SQLite para evitar duplicados.
- Classifica itens em `evento`, `vaga`, `programa` ou `outro`.
- Filtra por regioes como `nacional` e `internacional`.
- Gera um resumo em Markdown.
- Pode enviar o resumo por e-mail via SMTP.
- Le variaveis de ambiente de um arquivo `.env`.

## Estrutura

- `events_analyzer/collector.py`: busca e parser das fontes.
- `events_analyzer/classifier.py`: regra simples de classificacao.
- `events_analyzer/store.py`: persistencia em SQLite.
- `events_analyzer/summarizer.py`: cria o resumo diario.
- `events_analyzer/notifier.py`: envio por e-mail.
- `events_analyzer/main.py`: interface de terminal.

## Instalacao

```bash
pip install -r requirements.txt
```

## Configuracao

1. Copie `sources.example.json` para `sources.json`.
2. Ajuste as fontes e a `region` de cada uma.
3. Copie `.env.example` para `.env` e ajuste as variaveis, se quiser:

```bash
copy .env.example .env
```

## Uso

Coletar e salvar os itens:

```bash
python -m events_analyzer.main scan
```

Gerar o resumo do periodo recente:

```bash
python -m events_analyzer.main digest
```

Gerar e enviar o resumo:

```bash
python -m events_analyzer.main send
```

Filtrar por regioes:

```bash
python -m events_analyzer.main digest --regions nacional
python -m events_analyzer.main send --regions internacional --hours 48
```

Rodar continuamente e enviar todo dia no horario configurado:

```bash
python -m events_analyzer.main loop --once
```

## Como expandir

- Adicione fontes HTML com `item_selector`, `title_selector`, `link_selector` e `summary_selector`.
- Troque o resumidor local por um modelo de IA.
- Adicione filtros por pais, idioma ou nivel de senioridade.
- Salve os resumos em e-mail, Telegram ou Slack.
