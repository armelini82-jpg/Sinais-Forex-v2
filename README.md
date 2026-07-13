# Forex Radar AI

Scanner profissional de Day Trade em Forex. Monitora múltiplos pares em tempo
real, calcula um score de qualidade (**IQS — Intelligent Quality Score**) e
gera sinais de **BUY/SELL** com Entrada, Stop Loss, Take Profit, Relação
Risco/Retorno e Probabilidade — sempre com RR mínimo de 2:1.

> **Status deste repositório:** primeira versão funcional (v1.0), cobrindo a
> arquitetura completa, o motor de decisão, dashboard em tempo real, API,
> banco de dados, Telegram e testes dos módulos críticos. Fase 2 (Smart Money
> Concepts, backtest completo com relatórios e pipeline de Machine Learning)
> está com a arquitetura preparada — veja [Roadmap](#roadmap).

---

## Sumário

- [Arquitetura](#arquitetura)
- [Stack Tecnológica](#stack-tecnológica)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Como Funciona o IQS](#como-funciona-o-iqs)
- [Instalação e Execução (Docker)](#instalação-e-execução-docker)
- [Configuração](#configuração)
- [Executando os Testes](#executando-os-testes)
- [API](#api)
- [Conectando um Provedor de Dados Real](#conectando-um-provedor-de-dados-real)
- [Roadmap](#roadmap)

---

## Arquitetura

O backend segue **Clean Architecture** com separação estrita de
responsabilidades:

```
API (FastAPI endpoints)
   │
   ▼
Services (regras de negócio: IQSEngine, SignalEngine, RiskManagementService...)
   │
   ▼
Repositories (abstração de persistência — Repository Pattern)
   │
   ▼
Models (SQLAlchemy ORM)
```

Princípios aplicados:

- **SOLID** em todos os services (ex.: `SignalEngine` depende apenas das
  interfaces `IMarketDataProvider` e `ISignalRepository`, nunca de
  implementações concretas).
- **Dependency Injection** via `Depends()` do FastAPI (`app/api/deps.py`).
- **Repository Pattern** (`app/repositories/`) isolando o SQLAlchemy do
  restante do sistema.
- **Factory Pattern** (`app/factories/`) para trocar o provedor de dados de
  mercado sem alterar nenhum outro módulo (Open/Closed Principle).
- **DTOs** via Pydantic (`app/schemas/`) para nunca vazar models do ORM para
  a camada de API.

---

## Stack Tecnológica

| Camada       | Tecnologia                                   |
|--------------|-----------------------------------------------|
| Backend      | Python 3.12, FastAPI, Uvicorn                  |
| Banco        | PostgreSQL 16, SQLAlchemy 2 (async), Alembic   |
| Cache/Fila   | Redis                                          |
| Indicadores  | pandas, numpy, `ta`                            |
| Agendamento  | APScheduler                                    |
| Frontend     | HTML5, CSS3, JS ES6, Bootstrap 5, Chart.js      |
| Testes       | Pytest, pytest-asyncio, pytest-cov             |
| Infra        | Docker, Docker Compose, Nginx                  |

---

## Estrutura do Projeto

```
forex-radar-ai/
├── backend/
│   ├── app/
│   │   ├── core/            # config, logging, exceptions, security (JWT)
│   │   ├── db/               # engine/session assíncronos
│   │   ├── models/           # ORM: Candle, Signal, Operation, Statistics...
│   │   ├── schemas/          # DTOs Pydantic
│   │   ├── interfaces/       # contratos (DIP): repositórios, market data
│   │   ├── repositories/     # implementações concretas (Repository Pattern)
│   │   ├── services/         # IQSEngine, SignalEngine, RiskManagement...
│   │   ├── factories/        # MarketDataProviderFactory
│   │   ├── api/v1/endpoints/ # signals, operations, statistics, pairs, auth, ws
│   │   ├── scheduler/        # jobs de scan contínuo (APScheduler)
│   │   └── main.py
│   ├── alembic/               # migrações do banco
│   └── tests/                 # testes unitários (IQS, indicadores, risco...)
├── frontend/
│   ├── index.html
│   └── static/{css,js}
├── docker/nginx/
├── docker-compose.yml
└── .env.example
```

---

## Como Funciona o IQS

O **Intelligent Quality Score** combina 7 dimensões de análise (não apenas
indicadores isolados) em um score de 0 a 100:

| Componente     | Peso | O que avalia                                             |
|----------------|------|------------------------------------------------------------|
| Trend          | 25   | Alinhamento das EMAs 9/21/200 + inclinação do MACD          |
| Pullback       | 20   | Proximidade e retomada de tendência na EMA 21               |
| Momentum       | 15   | RSI fora da zona neutra + momentum bruto na direção certa   |
| Volatilidade   | 15   | ATR relativo dentro de faixa saudável                       |
| ADX            | 10   | Força da tendência (evita mercado lateral)                  |
| Liquidez       | 10   | Volume relativo e amplitude do candle (proxy de spread)     |
| Sessão         | 5    | Horário de maior liquidez para o par                        |

Classificação:

- **IQS ≥ 90** → sinal `CONFIRMADO` (notificado via WebSocket + Telegram)
- **80 ≤ IQS < 90** → sinal `PREPARANDO`
- **IQS < 80** → descartado

Todo sinal confirmado passa ainda pela `RiskManagementService`, que calcula
Stop Loss (baseado em ATR e no último fundo/topo, o que for mais
conservador), Take Profit (garantindo RR ≥ 2:1) e o tamanho de posição
compatível com 1% de risco por operação.

### Estatísticas (Win Rate, Profit Factor, Drawdown...)

Essas métricas **só existem para operações que você confirmou** — o sistema
nunca assume sozinho que um sinal foi operado. No dashboard, cada sinal tem
um botão **"Marcar como Operado"**: você informa o lote (e, se quiser, o
preço de entrada real que conseguiu na sua corretora). A partir daí, um job
do scheduler monitora o preço real do par a cada minuto e fecha a operação
sozinho quando o preço atinge o Take Profit ou o Stop Loss — sem precisar de
acesso à sua conta/corretora.

Isso evita duas armadilhas: (1) fingir que toda oportunidade gerada foi
operada, o que infla as estatísticas com sinais que você nunca seguiu de
verdade; e (2) exigir uma integração complexa e sensível com a API da sua
corretora só para fechar o loop.

---

## Instalação e Execução (Docker)

### Pré-requisitos

- Docker e Docker Compose instalados

### Passos

```bash
git clone <seu-repositório>
cd forex-radar-ai

cp .env.example .env
# edite o .env se quiser trocar credenciais, pares monitorados, Telegram, etc.

docker compose up --build
```

Serviços disponíveis após o start:

| Serviço    | URL                              |
|------------|-----------------------------------|
| Dashboard  | http://localhost:8080             |
| API        | http://localhost:8000             |
| Swagger    | http://localhost:8000/docs        |
| Redoc      | http://localhost:8000/redoc       |
| Postgres   | localhost:5432                    |
| Redis      | localhost:6379                    |

O container `api` roda `alembic upgrade head` automaticamente antes de subir
o Uvicorn, garantindo que o schema do banco esteja sempre atualizado.

O scheduler interno começa a varrer os pares configurados assim que a API
sobe, gerando sinais em `M1`, `M5`, `M15` e `H1` de forma independente.

---

## Configuração

Toda a configuração do sistema é centralizada em **um único arquivo**: `.env`
(lido por `app/core/config.py`). Principais parâmetros:

```env
SYMBOLS=EURUSD,GBPUSD,USDJPY,...
TIMEFRAMES=M1,M5,M15,H1
RISK_PER_TRADE_PERCENT=1.0
MIN_RISK_REWARD=2.0
MAX_OPERATIONS_PER_SYMBOL_PER_DAY=3
IQS_MIN_SIGNAL=90
IQS_MIN_PREPARING=80
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_ENABLED=false
DATA_PROVIDER=simulated
```

Para habilitar o Telegram, crie um bot com o [@BotFather](https://t.me/BotFather),
obtenha o `chat_id` do destino e defina `TELEGRAM_ENABLED=true`.

---

## Executando os Testes

```bash
cd backend
pip install -r requirements.txt
pytest
```

ou, a partir da raiz do projeto:

```bash
./scripts/run_tests.sh
```

Os testes cobrem os módulos críticos do motor de decisão: `IndicatorService`,
`IQSEngine`, `RiskManagementService`, `StatisticsService` e o provider de
dados simulado. Expandir a cobertura para os endpoints de API e repositórios
(com banco de teste via `testcontainers` ou SQLite) é o próximo passo
indicado no roadmap para atingir a meta de 90% de cobertura.

---

## API

Principais endpoints (documentação completa e interativa em `/docs`):

| Método | Rota                              | Descrição                                  |
|--------|------------------------------------|---------------------------------------------|
| GET    | `/api/v1/signals`                  | Lista sinais ativos                          |
| GET    | `/api/v1/signals/latest-scan`      | Última leitura de IQS de cada par, inclusive descartados |
| GET    | `/api/v1/signals/{id}`             | Detalhe de um sinal                          |
| POST   | `/api/v1/signals/scan?timeframe=`  | Dispara scan manual                          |
| GET    | `/api/v1/operations`               | Lista operações recentes                     |
| GET    | `/api/v1/statistics?days=30`       | Win Rate, Profit Factor, Drawdown, etc.      |
| GET    | `/api/v1/pairs`                    | Pares e timeframes monitorados               |
| GET    | `/api/v1/pairs/{symbol}/status`    | Preço atual e status do mercado              |
| POST   | `/api/v1/backtest/run`             | Roda o IQS sobre candles históricas reais    |
| POST   | `/api/v1/auth/register`            | Cria usuário                                 |
| POST   | `/api/v1/auth/login`               | Retorna token JWT                            |
| WS     | `/ws/dashboard`                    | Canal de eventos em tempo real               |

### Backtest

O painel **Backtest** no dashboard roda o mesmo motor de decisão (IQS +
gestão de risco) usado em produção sobre candles históricas reais — sem
lookahead bias: a cada ponto no tempo, o motor só enxerga dados até aquele
momento. Você escolhe par, timeframe, período e capital inicial; o resultado
mostra Win Rate, Profit Factor, Drawdown, Curva de Capital e a lista de
trades que teriam sido gerados.

Com `DATA_PROVIDER=twelvedata`, o backtest busca o histórico real da API
(pagina automaticamente em blocos de até 5.000 candles). Períodos longos em
timeframes curtos (M1/M5) consomem mais requisições — o rate limiter interno
já protege a cota do plano gratuito, mas backtests muito longos podem
demorar alguns segundos a mais por causa disso.

---

## Conectando um Provedor de Dados Real

Por padrão (`DATA_PROVIDER=simulated`), o sistema roda com um provedor de
dados simulado — útil para validar o pipeline sem depender de terceiros.

### TwelveData (dados reais, plano gratuito disponível)

Já vem implementado (`TwelveDataMarketDataProvider`). Para ativar:

1. Crie uma conta gratuita em [twelvedata.com](https://twelvedata.com/pricing)
   e gere sua API key.
2. No `.env`:
   ```env
   DATA_PROVIDER=twelvedata
   MARKET_DATA_API_KEY=sua_chave_aqui
   ```
3. `docker compose up --build` (ou `docker compose restart api` se já estiver rodando).

**Sobre o plano gratuito:** 8 requisições/min e 800/dia. O provider já tem
cache interno alinhado ao fechamento de cada candle (ex.: um H1 só é buscado
de novo depois de 1h) e um rate limiter que espaça as chamadas — mas isso não
substitui uma cota maior. Com os 10 pares padrão × 4 timeframes você estoura
o limite rápido. Recomendado no free tier:

```env
SYMBOLS=EURUSD,GBPUSD,USDJPY,XAUUSD
TIMEFRAMES=M15,H1
```

**Limitação conhecida:** a TwelveData não fornece volume real para pares de
Forex/XAU (mercado de balcão, sem fita centralizada). O componente
"Liquidez" do IQS, que usa volume relativo, fica com menos informação nessa
fonte — o restante do score (Trend, Pullback, Momentum, ADX, Volatilidade,
Sessão) não é afetado.

### Outras corretoras (OANDA, MT5)

Implemente a interface `IMarketDataProvider`
(`app/interfaces/market_data_interface.py`) e registre o novo provider em
`app/factories/market_data_factory.py`. Nenhum outro módulo do sistema
precisa ser alterado — é exatamente para isso que a interface existe.

---

## Roadmap

- [ ] **Fase 2 — Smart Money Concepts**: Break of Structure, CHOCH, Order
      Blocks, Liquidity Sweep, Fair Value Gap, Volume Profile / Market
      Profile (arquitetura de indicadores já preparada para extensão).
- [x] **Backtest engine**: seleção de par/timeframe/período/capital inicial,
      rodando o IQS sobre candles históricas reais sem lookahead bias.
- [ ] **Machine Learning**: a tabela `indicators` já funciona como feature
      store; próximo passo é o pipeline de treinamento de um classificador de
      probabilidade de sucesso do sinal, substituindo a heurística atual em
      `SignalEngine._estimate_probability`.
- [ ] Cobertura de testes ampliada para 90%+ (endpoints, repositórios,
      scheduler).
- [ ] Autenticação com refresh tokens e RBAC completo.

---

## Aviso

Este software é uma ferramenta de análise técnica. Nenhum sinal gerado
constitui recomendação de investimento. Trading envolve risco real de perda
de capital.
