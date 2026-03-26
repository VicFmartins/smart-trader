# Smart Trade

> Journal inteligente para day traders brasileiros: da nota de corretagem ao DARF, com IA.

## Descrição

Operar na B3 exige disciplina, organização e controle fiscal. Muitos traders ainda gerenciam operações em planilhas manuais, perdem tempo digitando dados de notas de corretagem e só descobrem o imposto a pagar no fechamento do mês ou na declaração.

O **Smart Trade** foi pensado para resolver esse fluxo de ponta a ponta:

1. Você faz o upload da nota de corretagem em PDF.
2. A IA extrai automaticamente os trades.
3. Você revisa e corrige os dados em uma tabela editável.
4. O sistema salva os trades confirmados.
5. O dashboard mostra métricas de performance.
6. O cálculo estimado do DARF 6015 é feito com compensação de prejuízos.

O projeto é **local-first**: os dados ficam na sua máquina, com SQLite, sem dependência obrigatória de nuvem.

## Principais Funcionalidades

### Importação com IA

- Upload de notas de corretagem em PDF
- Extração automática de trades com LLM
- Suporte a execução local com **Ollama**
- Detecção de corretora e normalização dos dados extraídos
- Fluxo de revisão antes da persistência

### Revisão Inteligente

- Tabela editável com os trades extraídos
- Indicadores de confiança por linha
- Avisos de validação por campo
- Edição inline de ticker, preço, quantidade, corretora e notas

### Dashboard de Performance

- Equity curve
- Drawdown
- Win rate
- Profit factor
- Expectancy
- PnL por ativo
- PnL por horário
- PnL por dia da semana
- PnL por setup

### Cálculo Automático de IR

- Apuração mensal de day trade
- Compensação de prejuízos acumulados
- Estimativa de DARF código `6015`
- Breakdown mensal de lucro, prejuízo, base tributável e imposto

### Segurança e Privacidade

- Autenticação com JWT
- Banco local com SQLite
- Configuração de inferência local com Ollama
- `.env` fora do versionamento

## Demonstração

Screenshots podem ser adicionados em:

| Tela | Descrição |
| --- | --- |
| `docs/screenshots/pdf_import.png` | Upload e revisão de nota de corretagem |
| `docs/screenshots/dashboard.png` | Equity curve e KPIs de performance |
| `docs/screenshots/tax_report.png` | Cálculo mensal de DARF |

## Arquitetura do Projeto

```text
smart-trader/
├── app/                        # Backend FastAPI
│   ├── api/                    # Rotas HTTP
│   ├── core/                   # Config, segurança, exceptions
│   ├── db/                     # Engine, session, base
│   ├── models/                 # Modelos SQLAlchemy
│   ├── repositories/           # Acesso a dados
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Regras de negócio
│   │   └── pdf_import/         # Extração, LLM, parsing e validação
│   └── main.py                 # Entrypoint FastAPI
├── streamlit_app/              # Frontend Streamlit
│   ├── app.py
│   ├── components/
│   └── pages/
├── alembic/                    # Migrações
├── data/                       # Dados locais
├── docs/                       # Documentação
├── tests/                      # Testes automatizados
├── .env.example                # Template de configuração
└── requirements.txt            # Dependências
```

### Fluxo de Importação de PDF

```text
PDF upload
→ extração de texto
→ detecção de corretora
→ prompt para LLM
→ JSON estruturado
→ validação e normalização
→ revisão manual
→ persistência no SQLite
```

## Tecnologias Utilizadas

| Camada | Tecnologia | Descrição |
| --- | --- | --- |
| Backend | FastAPI | API REST |
| Frontend | Streamlit | Interface local multi-página |
| Banco de dados | SQLite + SQLAlchemy | Persistência local-first |
| Migrações | Alembic | Controle de schema |
| IA local | Ollama | Inferência local |
| Validação | Pydantic v2 | Schemas e validação |
| PDF | pdfplumber / PyMuPDF | Extração de texto |
| Gráficos | Plotly | Visualização no dashboard |
| Testes | pytest | Testes automatizados |

## Como Rodar o Projeto Localmente

### Pré-requisitos

- Python 3.11+
- Ollama instalado localmente, se quiser usar importação com IA local

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd smart-trader
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Depois, edite o `.env` com seus próprios valores.

### 5. Inicie o backend

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

- API: `http://127.0.0.1:8010`
- Docs: `http://127.0.0.1:8010/docs`

### 6. Inicie o frontend

Em outro terminal:

```bash
python -m streamlit run streamlit_app/app.py --server.port 8501
```

- Streamlit: `http://127.0.0.1:8501`

### 7. Primeiro acesso

1. Informe a URL da API no Streamlit: `http://127.0.0.1:8010`
2. Faça login com as credenciais configuradas no `.env`
3. Acesse a tela de importação de PDF ou o dashboard

## Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste os valores. Exemplos importantes:

```env
JWT_SECRET_KEY=change-me-before-any-deployment
DEFAULT_ADMIN_EMAIL=admin@smarttrade.local
DEFAULT_ADMIN_PASSWORD=change-me-now
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
SMART_TRADE_API_URL=http://127.0.0.1:8010
```

Consulte o arquivo `.env.example` para a lista completa.

## Casos de Uso

| Perfil | Como o Smart Trade ajuda |
| --- | --- |
| Day trader ativo | Importa notas, acompanha equity curve e métricas |
| Trader no fechamento do IR | Obtém apuração mensal com compensação de prejuízos |
| Iniciante na B3 | Enxerga padrões por ativo, horário e setup |
| Desenvolvedor | Usa uma base FastAPI + Streamlit para expandir o produto |

## Roadmap

- [ ] Suporte a mais corretoras
- [ ] Importação de mais formatos de nota
- [ ] Gestão de setups
- [ ] Relatórios fiscais mais completos
- [ ] Melhorias visuais no dashboard
- [ ] Evolução da camada de parsing com LLM

## Contribuindo

Contribuições são bem-vindas. Abra uma issue para discutir melhorias ou envie um pull request com sua proposta.

## Licença

Este projeto está sob a licença **MIT**. Consulte o arquivo `LICENSE` para mais detalhes.

## Aviso

Os valores calculados pelo Smart Trade são estimativas baseadas nos dados importados. Para declaração oficial de Imposto de Renda, consulte um contador.
