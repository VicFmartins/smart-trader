# Smart Trade 📊

> **Journal inteligente para day traders brasileiros — da nota de corretagem ao DARF, com IA.**

---

## Descrição

Operar na B3 exige disciplina, organização e controle fiscal. A maioria dos traders ainda gerencia seus trades em planilhas manuais, perde tempo digitando dados de notas de corretagem e descobre o imposto a pagar apenas na hora da declaração.

**Smart Trade** resolve esse problema de ponta a ponta:

1. Você faz o upload da nota de corretagem em PDF.
2. A IA (Gemini ou Ollama local) extrai automaticamente os trades — ticker, preço de entrada, saída, quantidade, resultado.
3. Você revisa e corrige o que quiser em uma tabela editável.
4. O sistema salva os dados e gera análises de performance em tempo real.
5. O cálculo do DARF 6015 (Day Trade B3, alíquota 20%) é feito automaticamente, com compensação de perdas acumuladas mês a mês.

Projeto **local-first**: seus dados ficam em SQLite na sua máquina. Sem nuvem, sem assinatura, sem compartilhamento de dados.

---

## Principais Funcionalidades

### 🤖 Importação com IA
- Upload de notas de corretagem em PDF (CLEAR, XP, Rico e outras)
- Extração automática de trades via **Gemini API** (Google) ou **Ollama** (inferência local)
- Detecção inteligente de corretora, data da operação e tipo de ativo (WIN, WDO)
- Revisão do resultado antes de salvar — nenhum dado é persistido sem confirmação

### 📝 Revisão Inteligente
- Tabela editável com todos os trades extraídos
- Indicadores de confiança por linha (score 0–1)
- Alertas de campos obrigatórios ausentes
- Edição inline: ticker, preço, quantidade, corretora, notas

### 📊 Dashboard de Performance
- **Equity curve** acumulada
- **Drawdown** máximo
- **Win rate**, **Profit Factor**, **Expectancy**
- PnL por ativo, por horário do dia e por dia da semana
- Filtros por período, ativo e corretora

### 🧾 Cálculo Automático de IR (DARF)
- Apuração mensal de lucros e prejuízos em day trade
- Compensação automática de perdas acumuladas entre meses
- Estimativa de DARF código 6015 (alíquota 20%)
- Breakdown mensal completo: lucro bruto, prejuízo, base de cálculo, DARF devido

### 🔒 Segurança e Privacidade
- Autenticação JWT com login por e-mail e senha
- Banco de dados local (SQLite) — nenhum dado sai da sua máquina
- Configuração de LLM flexível: use a API do Google ou rode um modelo 100% offline com Ollama

---

## Demonstração

> 📸 *Screenshots serão adicionados em breve.*

| Tela | Descrição |
|------|-----------|
| `docs/screenshots/pdf_import.png` | Upload e revisão de nota de corretagem |
| `docs/screenshots/dashboard.png` | Equity curve e KPIs de performance |
| `docs/screenshots/tax_report.png` | Cálculo mensal de DARF |

---

## Arquitetura do Projeto

```
smart-trader/
├── app/                        # Backend FastAPI
│   ├── api/                    # Rotas HTTP (trades, PDF import, analytics, taxes, auth)
│   ├── models/                 # Modelos SQLAlchemy (Trade, ImportJob, TaxSummary...)
│   ├── schemas/                # Pydantic schemas (request/response)
│   ├── services/               # Lógica de negócio
│   │   ├── pdf_import/         # Pipeline: extração de texto → LLM → validação
│   │   ├── analytics.py        # Equity curve, drawdown, win rate, PnL breakdowns
│   │   └── taxes.py            # Apuração mensal de IR, compensação de perdas
│   └── main.py                 # Inicialização FastAPI
├── streamlit_app/              # Frontend Streamlit
│   ├── app.py                  # Página inicial
│   ├── pages/
│   │   ├── 1_PDF_Import_Review.py
│   │   ├── 2_Trade_Dashboard.py
│   │   └── 3_Tax_Report.py
│   ├── components/             # Componentes reutilizáveis (tabela, gráficos, KPIs)
│   ├── style.py                # Design system (tokens CSS, helpers visuais)
│   └── api_client.py           # Cliente HTTP para o backend
├── data/                       # Banco de dados local (ignorado pelo git)
├── tests/                      # Testes automatizados (pytest)
├── alembic/                    # Migrações de banco de dados
├── .env.example                # Template de variáveis de ambiente
└── requirements.txt            # Dependências Python
```

**Fluxo de extração de PDF:**
```
PDF upload → Extração de texto (pdfminer) → Prompt LLM → JSON parse
          → Validação de campos → Tela de revisão → Persistência no SQLite
```

---

## Tecnologias Utilizadas

| Camada | Tecnologia | Descrição |
|--------|-----------|-----------|
| Backend | **FastAPI** | API REST com autenticação JWT |
| Frontend | **Streamlit** | Interface web multi-página |
| Banco de dados | **SQLite + SQLAlchemy** | Local-first, zero configuração |
| Migrações | **Alembic** | Controle de schema do banco |
| IA — Cloud | **Google Gemini API** | Extração com `gemini-2.5-flash` |
| IA — Local | **Ollama** | Inferência offline (ex: `qwen2.5:3b`) |
| Validação | **Pydantic v2** | Schemas e validação de dados |
| Extração de PDF | **pdfminer.six** | Parsing de texto de PDFs |
| Gráficos | **Plotly** | Charts interativos no dashboard |
| Testes | **pytest** | Testes unitários e de integração |

---

## Como Rodar o Projeto Localmente

### Pré-requisitos

- Python 3.11+
- Uma chave de API do [Google AI Studio](https://aistudio.google.com/) **ou** [Ollama](https://ollama.ai/) instalado localmente

### 1. Clone o repositório

```bash
git clone https://github.com/VicFmartins/smart-trader.git
cd smart-trader
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite .env com seu editor preferido
# Preencha GEMINI_API_KEY (ou configure Ollama) e JWT_SECRET_KEY
```

### 5. Inicie o backend (FastAPI)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

- API disponível em: `http://localhost:8010`
- Swagger (docs interativos): `http://localhost:8010/docs`

### 6. Inicie o frontend (Streamlit)

Em um segundo terminal (mesmo `.venv` ativado):

```bash
streamlit run streamlit_app/app.py --server.port 8501
```

Acesse em: `http://localhost:8501`

### 7. Primeiro acesso

1. Na barra lateral do Streamlit, informe a URL da API (`http://127.0.0.1:8010`)
2. Faça login com as credenciais definidas em `DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD` no seu `.env`
3. Navegue até **PDF Import Review** e faça upload da primeira nota de corretagem

---

## Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha os valores:

```env
# Provedor de IA: "gemini" ou "ollama"
LLM_PROVIDER=gemini

# Chave da API Gemini (Google AI Studio)
GEMINI_API_KEY=sua-chave-aqui

# Segredo JWT — use uma string aleatória longa em produção
JWT_SECRET_KEY=mude-antes-de-usar

# Credenciais do admin inicial
DEFAULT_ADMIN_EMAIL=admin@smarttrade.local
DEFAULT_ADMIN_PASSWORD=mude-esta-senha
```

Consulte `.env.example` para a lista completa de variáveis disponíveis.

---

## Casos de Uso

| Perfil | Como o Smart Trade ajuda |
|--------|--------------------------|
| **Day trader ativo** | Importa notas diárias, acompanha equity curve e win rate em tempo real |
| **Trader na declaração do IR** | Obtém a apuração mensal pronta para preencher o DARF sem precisar de planilha |
| **Iniciante na B3** | Entende seus padrões de operação (horário, ativo, setup) com visualizações claras |
| **Desenvolvedor** | Base sólida de FastAPI + Streamlit para construir ferramentas financeiras próprias |

---

## Roadmap

- [ ] Suporte a mais corretoras (XP, Rico, BTG, Modal)
- [ ] Importação via e-mail (leitura automática de notas)
- [ ] Gestão de setups — vincular trades a estratégias e comparar resultados
- [ ] Versão SaaS com autenticação multi-usuário e deploy em nuvem
- [ ] App mobile para visualização de KPIs e alertas
- [ ] Integração direta com corretoras via Open Finance B3
- [ ] Exportação do relatório completo para declaração no GCAP

---

## Contribuindo

Contribuições são bem-vindas! Abra uma _issue_ para discutir melhorias ou envie um _pull request_ com sua proposta.

---

## Licença

Este projeto está sob a licença **MIT**. Consulte o arquivo `LICENSE` para mais detalhes.

---

> ⚠️ **Aviso:** Os valores calculados pelo Smart Trade são estimativas baseadas nos dados importados. Consulte sempre um contador para a declaração oficial do Imposto de Renda.
