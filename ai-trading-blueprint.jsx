import { useState } from "react";

const SECTIONS = [
  { id: "overview", label: "System Overview", icon: "⬡" },
  { id: "architecture", label: "Architecture", icon: "◈" },
  { id: "database", label: "Database Schema", icon: "◫" },
  { id: "api", label: "API Design", icon: "⟁" },
  { id: "ai_engine", label: "AI Engine", icon: "◉" },
  { id: "risk", label: "Risk Framework", icon: "⚠" },
  { id: "security", label: "Security", icon: "⊛" },
  { id: "deployment", label: "Deployment", icon: "▲" },
  { id: "roadmap", label: "Roadmap", icon: "◐" },
];

const Tag = ({ children, color = "blue" }) => {
  const colors = {
    blue: "bg-cyan-950 text-cyan-300 border-cyan-800",
    green: "bg-emerald-950 text-emerald-300 border-emerald-800",
    amber: "bg-amber-950 text-amber-300 border-amber-800",
    red: "bg-red-950 text-red-300 border-red-800",
    purple: "bg-violet-950 text-violet-300 border-violet-800",
    gray: "bg-slate-800 text-slate-300 border-slate-700",
  };
  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded border ${colors[color]}`}>
      {children}
    </span>
  );
};

const SectionCard = ({ title, children, accent = "cyan" }) => {
  const accents = {
    cyan: "border-cyan-800/60 before:bg-cyan-400",
    emerald: "border-emerald-800/60 before:bg-emerald-400",
    amber: "border-amber-800/60 before:bg-amber-400",
    violet: "border-violet-800/60 before:bg-violet-400",
    red: "border-red-800/60 before:bg-red-400",
  };
  return (
    <div className={`relative border ${accents[accent]} bg-slate-950/80 rounded-lg overflow-hidden mb-6`}>
      <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-3">
        <div className={`w-1.5 h-4 rounded-sm ${accents[accent].split(" ")[1]}`} />
        <h3 className="font-mono text-sm font-semibold text-slate-200 tracking-wider uppercase">{title}</h3>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
};

const CodeBlock = ({ code, lang = "python" }) => (
  <pre className="bg-slate-900 border border-slate-800 rounded-lg p-4 overflow-x-auto text-xs font-mono text-emerald-300 leading-relaxed">
    <code>{code}</code>
  </pre>
);

const Grid2 = ({ children }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{children}</div>
);

const Grid3 = ({ children }) => (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">{children}</div>
);

const InfoCard = ({ label, value, sub, color = "cyan" }) => {
  const colors = {
    cyan: "text-cyan-400",
    emerald: "text-emerald-400",
    amber: "text-amber-400",
    violet: "text-violet-400",
  };
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
      <div className="text-xs text-slate-500 font-mono uppercase tracking-widest mb-1">{label}</div>
      <div className={`text-lg font-bold font-mono ${colors[color]}`}>{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  );
};

const LayerBox = ({ title, items, color }) => {
  const border = { cyan: "border-cyan-800", emerald: "border-emerald-800", amber: "border-amber-800", violet: "border-violet-800", red: "border-red-800" };
  const text = { cyan: "text-cyan-400", emerald: "text-emerald-400", amber: "text-amber-400", violet: "text-violet-400", red: "text-red-400" };
  return (
    <div className={`border ${border[color]} rounded-lg p-4 bg-slate-950`}>
      <div className={`text-xs font-mono font-bold uppercase tracking-widest mb-3 ${text[color]}`}>{title}</div>
      <div className="flex flex-wrap gap-2">
        {items.map((item, i) => (
          <span key={i} className="text-xs bg-slate-800 text-slate-300 border border-slate-700 rounded px-2 py-1 font-mono">{item}</span>
        ))}
      </div>
    </div>
  );
};

// ─── SECTION RENDERERS ────────────────────────────────────────────────────────

function OverviewSection() {
  return (
    <div>
      <div className="mb-8 p-6 border border-cyan-900/50 rounded-xl bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 relative overflow-hidden">
        <div className="absolute inset-0 opacity-5" style={{backgroundImage:"repeating-linear-gradient(0deg,transparent,transparent 30px,#00d4ff 30px,#00d4ff 31px),repeating-linear-gradient(90deg,transparent,transparent 30px,#00d4ff 30px,#00d4ff 31px)"}} />
        <div className="relative">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-cyan-400 text-2xl font-mono">◉</span>
            <span className="text-xs font-mono text-cyan-600 tracking-widest uppercase">Autonomous AI Trading Platform</span>
          </div>
          <h1 className="text-3xl font-bold text-white mb-3" style={{fontFamily:"'Georgia', serif", letterSpacing:"-0.02em"}}>
            QuantumEdge <span className="text-cyan-400">AI</span>
          </h1>
          <p className="text-slate-400 text-sm max-w-2xl leading-relaxed">
            A production-grade, enterprise-scale autonomous trading platform combining LLM market intelligence, 
            quantitative signal processing, and institutional-grade risk management. Every trade decision is 
            explainable, auditable, and constrained by multi-layer risk controls.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <InfoCard label="Supported Brokers" value="7+" sub="Zerodha · Alpaca · IBKR · Binance" color="cyan" />
        <InfoCard label="Strategy Types" value="9" sub="Momentum · Mean Reversion · RL" color="emerald" />
        <InfoCard label="Risk Layers" value="6" sub="Position · Portfolio · System" color="amber" />
        <InfoCard label="MVP Timeline" value="16 wk" sub="Phase 1 Production Target" color="violet" />
      </div>

      <SectionCard title="Platform Pillars" accent="cyan">
        <Grid3>
          {[
            { icon: "◈", title: "AI-First Analysis", desc: "LLMs + ML models analyze technical, fundamental, sentiment, and macro signals simultaneously to generate ranked trade signals with confidence scores and natural-language reasoning." },
            { icon: "⚠", title: "Capital Preservation", desc: "Every trade passes 6-layer risk validation: position sizing, portfolio exposure, drawdown limits, volatility-adjusted stops, sector concentration, and liquidity checks." },
            { icon: "⊛", title: "Zero-Trust Security", desc: "API keys stored in HashiCorp Vault. E2E encryption, MFA enforced, OAuth 2.0 broker flows, immutable audit logs, and anomaly detection on all trading operations." },
            { icon: "◫", title: "Full Auditability", desc: "Every AI decision is logged with signal weights, model versions, market context, risk scores, and execution details. SEC/SEBI compliance-ready audit trail." },
            { icon: "⟁", title: "Multi-Mode Trading", desc: "Fully autonomous, semi-automatic (AI suggests, human confirms), or manual override. Emergency kill switch halts all positions within 200ms." },
            { icon: "◐", title: "Backtesting Engine", desc: "Walk-forward analysis, Monte Carlo simulations (10,000 paths), realistic slippage/commission modeling, and performance attribution vs. benchmark." },
          ].map((p, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <div className="text-cyan-400 text-xl mb-2 font-mono">{p.icon}</div>
              <div className="text-sm font-semibold text-white mb-1">{p.title}</div>
              <div className="text-xs text-slate-400 leading-relaxed">{p.desc}</div>
            </div>
          ))}
        </Grid3>
      </SectionCard>

      <SectionCard title="Team Roles & Responsibilities" accent="violet">
        <div className="space-y-3">
          {[
            { role: "Senior Quantitative Trader", owns: "Strategy design, signal generation logic, backtesting validation, alpha research", color: "cyan" },
            { role: "AI/ML Engineer", owns: "LLM integration, model training pipelines, feature engineering, reinforcement learning agent", color: "emerald" },
            { role: "Financial Risk Manager", owns: "Risk framework design, position sizing rules, drawdown limits, compliance requirements", color: "amber" },
            { role: "Full-Stack Architect", owns: "API design, database schema, microservices topology, frontend architecture", color: "violet" },
            { role: "Cybersecurity Expert", owns: "Vault integration, encryption design, OAuth flows, audit logging, penetration testing", color: "red" },
            { role: "DevOps Engineer", owns: "Docker/K8s infrastructure, CI/CD pipelines, observability stack, DR planning", color: "gray" },
          ].map((r, i) => (
            <div key={i} className="flex items-start gap-3 bg-slate-900 border border-slate-800 rounded p-3">
              <Tag color={r.color}>{r.role}</Tag>
              <span className="text-xs text-slate-400">{r.owns}</span>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

function ArchitectureSection() {
  return (
    <div>
      <SectionCard title="System Architecture — Layered Microservices" accent="cyan">
        <div className="space-y-3">
          <LayerBox title="Layer 0 · Client Layer" color="cyan"
            items={["Next.js 14 App Router", "React 18", "TailwindCSS", "TanStack Query", "Recharts / TradingView Widgets", "WebSocket Client", "Mobile PWA"]} />
          <div className="flex justify-center"><div className="w-px h-4 bg-slate-700" /></div>
          <LayerBox title="Layer 1 · API Gateway" color="emerald"
            items={["Kong / AWS API Gateway", "JWT Validation", "Rate Limiting (Redis)", "Request Routing", "WebSocket Upgrade", "TLS Termination", "WAF (ModSecurity)"]} />
          <div className="flex justify-center"><div className="w-px h-4 bg-slate-700" /></div>
          <Grid2>
            <LayerBox title="Layer 2A · Core Services" color="violet"
              items={["auth-service (FastAPI)", "user-service (FastAPI)", "portfolio-service (FastAPI)", "notification-service (FastAPI)", "audit-service (FastAPI)"]} />
            <LayerBox title="Layer 2B · Trading Services" color="amber"
              items={["market-data-service", "signal-service", "execution-service", "risk-service", "broker-connector-service", "backtest-service"]} />
          </Grid2>
          <div className="flex justify-center"><div className="w-px h-4 bg-slate-700" /></div>
          <LayerBox title="Layer 3 · AI / ML Engine" color="red"
            items={["LLM Orchestrator (Claude/GPT-4)", "Technical Analysis Engine", "Sentiment Analyzer", "Reinforcement Learning Agent", "XGBoost Signal Ranker", "Feature Store", "Model Registry (MLflow)"]} />
          <div className="flex justify-center"><div className="w-px h-4 bg-slate-700" /></div>
          <Grid2>
            <LayerBox title="Layer 4A · Data Layer" color="cyan"
              items={["PostgreSQL 15 (primary)", "Redis Cluster (cache/pub-sub)", "InfluxDB (time-series)", "S3 / GCS (model artifacts)", "Elasticsearch (audit logs)"]} />
            <LayerBox title="Layer 4B · Messaging" color="emerald"
              items={["Apache Kafka (event bus)", "Celery + Redis (task queue)", "WebSocket Hub", "Telegram Bot API", "SendGrid (email)", "Firebase (push)"]} />
          </Grid2>
          <div className="flex justify-center"><div className="w-px h-4 bg-slate-700" /></div>
          <LayerBox title="Layer 5 · Infrastructure" color="gray"
            items={["Kubernetes (EKS/GKE)", "Docker", "HashiCorp Vault", "Prometheus + Grafana", "Jaeger (tracing)", "ArgoCD (GitOps)", "Terraform (IaC)"]} />
        </div>
      </SectionCard>

      <SectionCard title="Broker Connector Architecture" accent="emerald">
        <Grid2>
          <div>
            <div className="text-xs text-slate-400 mb-3">Each broker runs as an isolated connector pod implementing a unified abstract interface:</div>
            <CodeBlock lang="python" code={`# Abstract Broker Interface
class BrokerConnector(ABC):
    @abstractmethod
    async def authenticate(self, credentials: Credentials) -> Session
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote
    
    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool
    
    @abstractmethod
    async def get_positions(self) -> List[Position]
    
    @abstractmethod
    async def get_account(self) -> Account
    
    @abstractmethod
    async def stream_ticks(self, symbols: List[str]) -> AsyncIterator[Tick]

# Concrete implementations:
# ZerodhaConnector(BrokerConnector)
# AlpacaConnector(BrokerConnector)
# InteractiveBrokersConnector(BrokerConnector)
# BinanceConnector(BrokerConnector)
# CoinbaseConnector(BrokerConnector)
# UpstoxConnector(BrokerConnector)`} />
          </div>
          <div className="space-y-2">
            {[
              { broker: "Zerodha Kite", protocol: "REST + WebSocket", auth: "API Key + TOTP", market: "NSE/BSE/MCX" },
              { broker: "Upstox", protocol: "REST + WebSocket", auth: "OAuth 2.0", market: "NSE/BSE" },
              { broker: "Interactive Brokers", protocol: "TWS API / REST", auth: "OAuth 2.0 / TWS", market: "Global" },
              { broker: "Alpaca", protocol: "REST + WebSocket", auth: "API Key", market: "US Equities" },
              { broker: "Binance", protocol: "REST + WebSocket", auth: "API Key + HMAC", market: "Crypto" },
              { broker: "Coinbase Advanced", protocol: "REST + WebSocket", auth: "OAuth 2.0", market: "Crypto" },
              { broker: "Angel One", protocol: "SmartAPI REST", auth: "API Key + TOTP", market: "NSE/BSE" },
            ].map((b, i) => (
              <div key={i} className="bg-slate-900 border border-slate-800 rounded p-3 flex flex-wrap gap-2 items-center">
                <span className="text-sm font-semibold text-white w-40">{b.broker}</span>
                <Tag color="cyan">{b.protocol}</Tag>
                <Tag color="amber">{b.auth}</Tag>
                <Tag color="emerald">{b.market}</Tag>
              </div>
            ))}
          </div>
        </Grid2>
      </SectionCard>

      <SectionCard title="Event-Driven Data Flow" accent="amber">
        <CodeBlock code={`MARKET TICK RECEIVED
    │
    ▼
[Kafka Topic: market.ticks]
    │
    ├──▶ Feature Store Updater  → Redis (real-time features)
    │
    ├──▶ Technical Engine       → Calculates indicators (RSI, MACD, BB, ATR...)
    │
    ├──▶ AI Signal Engine       → LLM + ML ensemble → Signal (BUY/SELL/HOLD + confidence)
    │        │
    │        ▼
    │    [Kafka Topic: signals.raw]
    │        │
    │        ▼
    │    Risk Validation Engine
    │        │  ├─ Position size check       PASS/FAIL
    │        │  ├─ Portfolio exposure check  PASS/FAIL
    │        │  ├─ Drawdown limit check      PASS/FAIL
    │        │  ├─ Volatility regime check   PASS/FAIL
    │        │  └─ Liquidity check           PASS/FAIL
    │        │
    │        ▼ (ALL PASS)
    │    [Kafka Topic: signals.approved]
    │        │
    │        ▼
    │    Execution Engine
    │        │  ├─ Mode: AUTO   → Place order immediately
    │        │  ├─ Mode: SEMI   → Push to approval queue
    │        │  └─ Mode: MANUAL → Notify only
    │        ▼
    │    Broker Connector → Exchange
    │        │
    │        ▼
    │    [Kafka Topic: orders.executed]
    │        │
    │        ├──▶ Portfolio Service   (update positions)
    │        ├──▶ Audit Service       (immutable log)
    │        └──▶ Notification Service (push/email/telegram)
    │
    └──▶ Sentiment Engine      → News + social → Sentiment score`} />
      </SectionCard>
    </div>
  );
}

function DatabaseSection() {
  return (
    <div>
      <SectionCard title="PostgreSQL Schema Design" accent="cyan">
        <div className="space-y-4">
          <CodeBlock code={`-- ─────────────────────────────────────────────────
-- USERS & AUTH
-- ─────────────────────────────────────────────────
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,     -- bcrypt, cost=12
    mfa_secret      BYTEA,                     -- encrypted TOTP secret
    mfa_enabled     BOOLEAN DEFAULT false,
    role            VARCHAR(20) DEFAULT 'trader', -- trader|analyst|admin
    status          VARCHAR(20) DEFAULT 'active',
    tier            VARCHAR(20) DEFAULT 'basic',  -- basic|pro|enterprise
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login      TIMESTAMPTZ,
    failed_attempts INT DEFAULT 0,
    locked_until    TIMESTAMPTZ
);

CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token   VARCHAR(512) NOT NULL,
    ip_address      INET,
    user_agent      TEXT,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    revoked         BOOLEAN DEFAULT false
);

-- ─────────────────────────────────────────────────
-- BROKER CONNECTIONS
-- ─────────────────────────────────────────────────
CREATE TABLE broker_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker          VARCHAR(50) NOT NULL,      -- zerodha|alpaca|ibkr|binance...
    display_name    VARCHAR(100),
    vault_path      VARCHAR(255) NOT NULL,     -- HashiCorp Vault path for keys
    status          VARCHAR(20) DEFAULT 'active',
    scopes          JSONB,                     -- granted permissions
    account_id      VARCHAR(100),
    last_synced     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, broker, account_id)
);

-- ─────────────────────────────────────────────────
-- RISK PROFILES
-- ─────────────────────────────────────────────────
CREATE TABLE risk_profiles (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connection_id           UUID REFERENCES broker_connections(id),
    max_position_pct        DECIMAL(5,2) DEFAULT 5.0,    -- % of portfolio per trade
    max_portfolio_exposure  DECIMAL(5,2) DEFAULT 80.0,   -- total invested %
    daily_loss_limit_pct    DECIMAL(5,2) DEFAULT 3.0,
    max_drawdown_pct        DECIMAL(5,2) DEFAULT 15.0,
    max_trades_per_day      INT DEFAULT 20,
    stop_loss_pct           DECIMAL(5,2) DEFAULT 2.0,
    trailing_stop_pct       DECIMAL(5,2) DEFAULT 1.5,
    allowed_asset_classes   TEXT[] DEFAULT ARRAY['equity'],
    allowed_sectors         TEXT[],
    min_confidence_score    DECIMAL(3,2) DEFAULT 0.70,
    trading_mode            VARCHAR(20) DEFAULT 'semi',  -- auto|semi|manual
    kill_switch_active      BOOLEAN DEFAULT false,
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────
-- MARKET DATA (InfluxDB handles OHLCV time-series;
-- PostgreSQL tracks metadata & references)
-- ─────────────────────────────────────────────────
CREATE TABLE instruments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol          VARCHAR(30) NOT NULL,
    exchange        VARCHAR(20) NOT NULL,
    asset_class     VARCHAR(20) NOT NULL,   -- equity|crypto|fx|commodity
    sector          VARCHAR(50),
    isin            VARCHAR(20),
    lot_size        INT DEFAULT 1,
    tick_size       DECIMAL(12,6),
    is_active       BOOLEAN DEFAULT true,
    UNIQUE(symbol, exchange)
);

-- ─────────────────────────────────────────────────
-- SIGNALS
-- ─────────────────────────────────────────────────
CREATE TABLE trade_signals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id),
    instrument_id       UUID NOT NULL REFERENCES instruments(id),
    signal_type         VARCHAR(10) NOT NULL,    -- BUY|SELL|HOLD
    direction           VARCHAR(10),             -- LONG|SHORT
    confidence_score    DECIMAL(5,4) NOT NULL,   -- 0.0000 - 1.0000
    strategy_name       VARCHAR(50),
    model_version       VARCHAR(30),
    entry_price         DECIMAL(18,6),
    target_price        DECIMAL(18,6),
    stop_loss_price     DECIMAL(18,6),
    timeframe           VARCHAR(10),             -- 1m|5m|15m|1h|1d
    technical_score     DECIMAL(5,4),
    fundamental_score   DECIMAL(5,4),
    sentiment_score     DECIMAL(5,4),
    quant_score         DECIMAL(5,4),
    reasoning_text      TEXT,                    -- LLM-generated explanation
    raw_features        JSONB,                   -- full feature snapshot
    risk_validated      BOOLEAN DEFAULT false,
    risk_checks         JSONB,                   -- pass/fail per check
    status              VARCHAR(20) DEFAULT 'pending',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    expires_at          TIMESTAMPTZ
);

-- ─────────────────────────────────────────────────
-- ORDERS & EXECUTIONS
-- ─────────────────────────────────────────────────
CREATE TABLE orders (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id           UUID REFERENCES trade_signals(id),
    user_id             UUID NOT NULL REFERENCES users(id),
    connection_id       UUID NOT NULL REFERENCES broker_connections(id),
    broker_order_id     VARCHAR(100),
    instrument_id       UUID NOT NULL REFERENCES instruments(id),
    order_type          VARCHAR(20),             -- MARKET|LIMIT|SL|SL-M
    side                VARCHAR(10),             -- BUY|SELL
    quantity            DECIMAL(18,6) NOT NULL,
    price               DECIMAL(18,6),
    trigger_price       DECIMAL(18,6),
    status              VARCHAR(20) DEFAULT 'pending',
    filled_quantity     DECIMAL(18,6) DEFAULT 0,
    avg_fill_price      DECIMAL(18,6),
    commission          DECIMAL(18,6),
    slippage_bps        DECIMAL(8,2),
    placed_at           TIMESTAMPTZ,
    filled_at           TIMESTAMPTZ,
    cancelled_at        TIMESTAMPTZ,
    metadata            JSONB
);

CREATE TABLE positions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id),
    connection_id       UUID NOT NULL REFERENCES broker_connections(id),
    instrument_id       UUID NOT NULL REFERENCES instruments(id),
    quantity            DECIMAL(18,6) NOT NULL,
    avg_cost            DECIMAL(18,6) NOT NULL,
    current_price       DECIMAL(18,6),
    unrealized_pnl      DECIMAL(18,6),
    realized_pnl        DECIMAL(18,6) DEFAULT 0,
    stop_loss_price     DECIMAL(18,6),
    trailing_stop_pct   DECIMAL(5,2),
    opened_at           TIMESTAMPTZ DEFAULT NOW(),
    last_updated        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, connection_id, instrument_id)
);

-- ─────────────────────────────────────────────────
-- AUDIT LOG (append-only, no UPDATE/DELETE)
-- ─────────────────────────────────────────────────
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    event_type      VARCHAR(50) NOT NULL,
    entity_type     VARCHAR(50),
    entity_id       UUID,
    ip_address      INET,
    user_agent      TEXT,
    payload         JSONB,
    checksum        VARCHAR(64),    -- SHA-256 of row content for tamper detection
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
-- Prevent modification
REVOKE UPDATE, DELETE ON audit_logs FROM PUBLIC;`} />
        </div>
      </SectionCard>

      <SectionCard title="Redis Key Patterns & InfluxDB Schema" accent="emerald">
        <Grid2>
          <CodeBlock code={`# Redis Key Patterns
# ─────────────────────────────────────
# Rate limiting
rate:{user_id}:{endpoint}       → counter (TTL: 60s)

# Real-time features (for AI engine)
feat:{symbol}:{timeframe}       → Hash (RSI, MACD, ATR, etc.)

# Live quotes
quote:{symbol}                  → Hash (bid, ask, last, volume)
                                  (TTL: 5s)

# Kill switch flags
kill:{user_id}                  → "1" (instant halt)
kill:global                     → "1" (system-wide halt)

# Signal approval queue (semi-auto mode)
approval:{user_id}              → Sorted Set (signal_id by score)

# Daily P&L tracking (for loss limit)
pnl:{user_id}:{date}            → Float (TTL: 86400s)

# Session store
session:{jti}                   → JSON (TTL: 3600s)

# WebSocket connections
ws:connections:{user_id}        → Set of socket_ids`} />
          <CodeBlock code={`// InfluxDB Schema — OHLCV Time-Series
// ─────────────────────────────────────
measurement: ohlcv
tags:
  symbol      (NIFTY, AAPL, BTCUSDT...)
  exchange    (NSE, NASDAQ, BINANCE)
  timeframe   (1m, 5m, 15m, 1h, 1d)
fields:
  open        float64
  high        float64
  low         float64
  close       float64
  volume      float64
  vwap        float64
  oi          float64   // open interest (futures)
timestamp:    nanosecond precision

measurement: tick
tags:
  symbol, exchange
fields:
  price       float64
  size        float64
  side        string    // buy|sell
timestamp:    nanosecond precision

// Retention Policies:
// tick     → 7 days
// 1m OHLCV → 90 days
// 5m OHLCV → 1 year
// 1h OHLCV → 5 years
// 1d OHLCV → 20 years (full history)`} />
        </Grid2>
      </SectionCard>
    </div>
  );
}

function APISection() {
  const endpoints = [
    { method: "POST", path: "/auth/register", desc: "User registration with email verification", auth: "Public" },
    { method: "POST", path: "/auth/login", desc: "Login → returns access + refresh token", auth: "Public" },
    { method: "POST", path: "/auth/mfa/verify", desc: "Verify TOTP code, upgrade token", auth: "Partial" },
    { method: "POST", path: "/auth/refresh", desc: "Rotate access token via refresh token", auth: "Partial" },
    { method: "GET",  path: "/users/me", desc: "Fetch current user profile", auth: "JWT" },
    { method: "PUT",  path: "/users/me/risk-profile", desc: "Update risk parameters", auth: "JWT" },
    { method: "POST", path: "/brokers/connect", desc: "Initiate OAuth or API key connection", auth: "JWT" },
    { method: "GET",  path: "/brokers/{id}/positions", desc: "Sync and return live positions", auth: "JWT" },
    { method: "GET",  path: "/brokers/{id}/balance", desc: "Real-time account balance", auth: "JWT" },
    { method: "DELETE", path: "/brokers/{id}", desc: "Revoke connection, delete vault keys", auth: "JWT+MFA" },
    { method: "GET",  path: "/market/{symbol}/quote", desc: "Real-time quote", auth: "JWT" },
    { method: "GET",  path: "/market/{symbol}/ohlcv", desc: "Historical OHLCV with timeframe", auth: "JWT" },
    { method: "GET",  path: "/market/{symbol}/sentiment", desc: "Aggregated sentiment score + news", auth: "JWT" },
    { method: "POST", path: "/signals/generate", desc: "Trigger on-demand signal for symbol", auth: "JWT" },
    { method: "GET",  path: "/signals", desc: "List pending/active signals", auth: "JWT" },
    { method: "POST", path: "/signals/{id}/approve", desc: "Manual approval (semi-auto mode)", auth: "JWT" },
    { method: "POST", path: "/signals/{id}/reject", desc: "Reject signal", auth: "JWT" },
    { method: "GET",  path: "/orders", desc: "Order history with filters", auth: "JWT" },
    { method: "POST", path: "/orders/{id}/cancel", desc: "Cancel open order", auth: "JWT" },
    { method: "POST", path: "/trading/kill-switch", desc: "Halt all trading instantly", auth: "JWT+MFA" },
    { method: "POST", path: "/backtest/run", desc: "Submit backtest job (async)", auth: "JWT" },
    { method: "GET",  path: "/backtest/{job_id}/results", desc: "Fetch completed backtest report", auth: "JWT" },
    { method: "GET",  path: "/portfolio/summary", desc: "Portfolio metrics + attribution", auth: "JWT" },
    { method: "GET",  path: "/portfolio/optimization", desc: "AI-powered allocation recommendations", auth: "JWT" },
    { method: "GET",  path: "/admin/audit-logs", desc: "Paginated audit log query", auth: "Admin" },
  ];

  const methodColor = { GET: "emerald", POST: "cyan", PUT: "amber", DELETE: "red" };

  return (
    <div>
      <SectionCard title="REST API — Endpoint Reference" accent="cyan">
        <div className="space-y-1 max-h-96 overflow-y-auto pr-1">
          {endpoints.map((e, i) => (
            <div key={i} className="flex items-center gap-3 bg-slate-900 border border-slate-800/60 rounded px-3 py-2 text-xs font-mono hover:border-slate-700 transition-colors">
              <Tag color={methodColor[e.method] || "gray"}>{e.method}</Tag>
              <span className="text-cyan-300 w-64 truncate">{e.path}</span>
              <span className="text-slate-400 flex-1">{e.desc}</span>
              <Tag color={e.auth === "JWT+MFA" ? "red" : e.auth === "Admin" ? "amber" : e.auth === "Public" ? "gray" : "violet"}>{e.auth}</Tag>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="WebSocket API" accent="emerald">
        <Grid2>
          <CodeBlock code={`// Client → Server (subscribe)
{
  "action": "subscribe",
  "channels": [
    "quotes:NIFTY50",
    "quotes:AAPL",
    "signals:{user_id}",
    "orders:{user_id}",
    "portfolio:{user_id}"
  ]
}

// Server → Client (tick)
{
  "channel": "quotes:NIFTY50",
  "type": "tick",
  "data": {
    "symbol": "NIFTY50",
    "ltp": 22450.30,
    "bid": 22449.95,
    "ask": 22450.65,
    "volume": 1284930,
    "change_pct": 0.42,
    "ts": "2025-03-15T09:15:02.342Z"
  }
}`} />
          <CodeBlock code={`// Server → Client (new signal)
{
  "channel": "signals:{user_id}",
  "type": "signal",
  "data": {
    "id": "sig_abc123",
    "symbol": "RELIANCE",
    "signal_type": "BUY",
    "confidence": 0.847,
    "entry_price": 2845.50,
    "target": 2920.00,
    "stop_loss": 2800.00,
    "reasoning": "Momentum breakout above 50-day EMA with bullish MACD crossover. Strong Q3 earnings catalyst. Sentiment score +0.72.",
    "risk_validated": true,
    "mode": "semi",
    "expires_in": 300
  }
}

// Server → Client (kill switch ack)
{
  "channel": "portfolio:{user_id}",
  "type": "kill_switch_activated",
  "data": { "open_orders_cancelled": 3, "ts": "..." }
}`} />
        </Grid2>
      </SectionCard>

      <SectionCard title="API Security Patterns" accent="amber">
        <CodeBlock code={`# JWT Token Structure (access token, TTL: 15min)
{
  "sub": "user_uuid",
  "jti": "unique_token_id",      # stored in Redis for revocation
  "role": "trader",
  "tier": "pro",
  "mfa_verified": true,
  "broker_scope": ["alpaca:read", "alpaca:trade"],
  "exp": 1710500000,
  "iat": 1710499100
}

# Rate Limiting Config (per endpoint class)
endpoints:
  /auth/*:         5 req/min  (brute force protection)
  /signals/*:      60 req/min
  /market/*:       300 req/min
  /admin/*:        30 req/min
  websocket:       1 connection per user

# Request signing (broker API calls)
# All outgoing broker requests signed with HMAC-SHA256
# Nonce included to prevent replay attacks
# Credentials fetched from Vault at request time (never cached in memory > 60s)`} />
      </SectionCard>
    </div>
  );
}

function AIEngineSection() {
  return (
    <div>
      <SectionCard title="AI Signal Generation Pipeline" accent="cyan">
        <CodeBlock code={`┌─────────────────────────────────────────────────────────────────┐
│                    AI SIGNAL ENGINE                             │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  TECHNICAL   │  │ FUNDAMENTAL  │  │     SENTIMENT        │  │
│  │  ANALYSIS    │  │  ANALYSIS    │  │     ANALYSIS         │  │
│  │              │  │              │  │                      │  │
│  │ RSI/MACD/BB  │  │ P/E, EPS     │  │ News NLP (Claude)    │  │
│  │ ATR/ADX/OBV  │  │ Revenue YoY  │  │ Reddit/Twitter       │  │
│  │ Patterns     │  │ Debt/Equity  │  │ Analyst ratings      │  │
│  │ XGBoost      │  │ Sector flow  │  │ FinBERT scoring      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│         └────────────┬────┴──────────────────────┘              │
│                      ▼                                          │
│          ┌───────────────────────┐                              │
│          │   FEATURE AGGREGATOR  │                              │
│          │  (weighted ensemble)  │                              │
│          └──────────┬────────────┘                              │
│                     │                                           │
│         ┌───────────┴───────────┐                               │
│         ▼                       ▼                               │
│  ┌─────────────────┐   ┌─────────────────────────────────┐     │
│  │  ML RANKER      │   │  LLM REASONING ENGINE           │     │
│  │                 │   │                                 │     │
│  │ XGBoost         │   │ System: Senior quant trader     │     │
│  │ gradient boost  │   │ Context: feature vector +       │     │
│  │ → signal score  │   │   market regime + news          │     │
│  │                 │   │ Output: signal type, confidence │     │
│  │ LSTM time-series│   │   entry/target/stop, reasoning  │     │
│  │ → price predict │   │   in structured JSON            │     │
│  └────────┬────────┘   └────────────────┬────────────────┘     │
│           │                             │                       │
│           └────────────┬────────────────┘                       │
│                        ▼                                        │
│            ┌───────────────────────┐                            │
│            │  SIGNAL CONSENSUS     │                            │
│            │  ML score × 0.4       │                            │
│            │  LLM score × 0.35     │                            │
│            │  Sentiment × 0.15     │                            │
│            │  Fundamental × 0.10   │                            │
│            │  → Final confidence   │                            │
│            └───────────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘`} />
      </SectionCard>

      <SectionCard title="LLM Integration — Market Analysis Prompt" accent="emerald">
        <CodeBlock code={`# LLM Signal Generation (Claude Sonnet via API)

SYSTEM_PROMPT = """
You are a senior quantitative trader with 20 years experience. 
Analyze the provided market data and generate a precise trade signal.
CRITICAL RULES:
- Never guarantee profits. Assess risk first.
- If market conditions are ambiguous, output HOLD.
- Consider current market regime: {regime}
- All outputs must be JSON. No markdown.
"""

USER_PROMPT = """
Symbol: {symbol} | Exchange: {exchange} | Timeframe: {timeframe}

TECHNICAL SNAPSHOT:
  Price: {current_price} | 1D Change: {change_pct}%
  RSI(14): {rsi} | MACD Signal: {macd_signal}
  ATR(14): {atr} | ADX: {adx}
  50 EMA: {ema_50} | 200 EMA: {ema_200}
  Bollinger: Upper={bb_upper} Lower={bb_lower}
  Volume vs 20D avg: {volume_ratio}x
  
PATTERN DETECTED: {detected_pattern}

SENTIMENT:
  News score: {news_sentiment} | Social score: {social_sentiment}
  Recent headlines: {headlines}
  
FUNDAMENTAL (if equity):
  Sector trend: {sector_trend}
  Earnings date: {next_earnings}
  
ML MODEL OUTPUT:
  XGBoost score: {xgb_score}
  LSTM 5-day forecast: {lstm_forecast}

Return ONLY this JSON:
{
  "signal_type": "BUY|SELL|HOLD",
  "confidence": 0.0-1.0,
  "entry_price": float,
  "target_price": float,
  "stop_loss": float,
  "timeframe_horizon": "intraday|swing|position",
  "reasoning": "2-3 sentence professional explanation",
  "key_risks": ["risk1", "risk2"],
  "invalidation_condition": "string"
}
"""`} />
      </SectionCard>

      <SectionCard title="ML Model Architecture" accent="violet">
        <Grid2>
          <div>
            <div className="text-xs text-amber-400 font-mono uppercase tracking-widest mb-3">XGBoost Signal Classifier</div>
            <CodeBlock code={`# Features (150+)
technical_features = [
    'rsi_14', 'rsi_7', 'rsi_21',
    'macd_line', 'macd_signal', 'macd_hist',
    'bb_width', 'bb_position',
    'atr_14', 'atr_ratio',
    'adx_14', 'di_plus', 'di_minus',
    'ema_cross_20_50', 'ema_cross_50_200',
    'obv_slope', 'cmf', 'mfi',
    'stoch_k', 'stoch_d',
    'volume_sma_ratio', 'volume_breakout',
    'price_vs_vwap', 'high_low_ratio',
    # Pattern features (one-hot)
    'is_doji', 'is_hammer', 'is_engulfing',
    'is_double_top', 'is_head_shoulders',
    # Multi-timeframe
    *[f'{f}_{tf}' for f in base for tf in 
      ['5m','15m','1h','4h','1d']]
]

model = xgb.XGBClassifier(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.01,
    subsample=0.8,
    colsample_bytree=0.8,
    objective='multi:softprob',
    num_class=3,  # BUY/HOLD/SELL
    use_label_encoder=False,
    eval_metric='mlogloss'
)`} />
          </div>
          <div>
            <div className="text-xs text-violet-400 font-mono uppercase tracking-widest mb-3">Reinforcement Learning Agent</div>
            <CodeBlock code={`# PPO Agent for Adaptive Strategy Selection
class TradingEnvironment(gym.Env):
    """
    State: 150-dim feature vector +
           portfolio state (positions, pnl, 
           drawdown, cash_ratio)
    
    Actions (discrete):
      0: HOLD
      1: BUY (small: 1% capital)
      2: BUY (medium: 3% capital)
      3: BUY (large: 5% capital)
      4: SELL_PARTIAL (50%)
      5: SELL_FULL
    
    Reward function:
      r = sharpe_increment 
        - 0.5 * max_drawdown_penalty
        - 0.1 * transaction_cost
        - 2.0 * risk_limit_breach  # heavy penalty
    
    Episode: 252 trading days
    Training: 10 years historical data
    Validation: walk-forward (no lookahead)
    """

# MLflow experiment tracking
mlflow.set_experiment("rl_trading_agent_v2")
with mlflow.start_run():
    mlflow.log_params(hyperparams)
    mlflow.log_metric("sharpe_ratio", sharpe)
    mlflow.log_metric("max_drawdown", mdd)
    mlflow.sklearn.log_model(model, "rl_agent")`} />
          </div>
        </Grid2>
      </SectionCard>

      <SectionCard title="Backtesting Engine" accent="amber">
        <CodeBlock code={`class BacktestEngine:
    """
    Walk-Forward Analysis + Monte Carlo Simulation
    
    Features:
    - Realistic slippage: uniform random [0, 2×ATR/price × 0.1%]
    - Commission modeling: per-broker fee schedule
    - Bid-ask spread simulation from historical tick data
    - Survivorship bias correction (delist tracking)
    - Dividend and split adjustment
    - Overnight gap risk modeling
    """

    def walk_forward(self, strategy, data, n_splits=10):
        """
        In-sample: 70% of window
        Out-of-sample: 30% → actual performance metric
        Retraining: every split
        """
        ...

    def monte_carlo(self, returns_series, n_paths=10000):
        """
        Bootstrapped resampling of daily returns
        Outputs: 5th/50th/95th percentile equity curves
        VaR(95%), CVaR(95%), probability of ruin
        """
        ...

    def performance_metrics(self, results) -> dict:
        return {
            "total_return_pct": ...,
            "annualized_return": ...,
            "sharpe_ratio": ...,        # target: > 1.5
            "sortino_ratio": ...,       # target: > 2.0
            "calmar_ratio": ...,
            "max_drawdown_pct": ...,
            "max_drawdown_duration_days": ...,
            "win_rate_pct": ...,
            "profit_factor": ...,       # gross_profit / gross_loss
            "avg_win_loss_ratio": ...,
            "expectancy": ...,
            "total_trades": ...,
            "avg_holding_period_days": ...,
            "var_95": ...,
            "cvar_95": ...,
        }`} />
      </SectionCard>
    </div>
  );
}

function RiskSection() {
  return (
    <div>
      <SectionCard title="6-Layer Risk Validation Pipeline" accent="red">
        <div className="space-y-3">
          {[
            { layer: "L1", name: "Position Sizing", desc: "Kelly Criterion capped at max_position_pct. Volatility-adjusted (divide by ATR ratio). Min size: 0.5%, Max: 5% of portfolio. Fractional Kelly: 25% of full Kelly.", formula: "size = min(kelly_fraction × 0.25, max_pct) × portfolio_value / price" },
            { layer: "L2", name: "Portfolio Exposure", desc: "Total invested capital ≤ max_portfolio_exposure%. Per-sector concentration ≤ 25%. Per-instrument ≤ max_position_pct. Correlation check: no two correlated positions > 0.7.", formula: "total_exposure = Σ(position_value) / portfolio_value" },
            { layer: "L3", name: "Daily Loss Limit", desc: "Cumulative daily P&L tracked in Redis. Trading halted if daily_loss > daily_loss_limit_pct%. Resets at 00:00 UTC. Tracks realized + unrealized intraday.", formula: "if daily_pnl < -(daily_loss_limit_pct/100 × starting_capital): HALT" },
            { layer: "L4", name: "Maximum Drawdown", desc: "Portfolio drawdown from all-time high tracked continuously. If drawdown > max_drawdown_pct%, kill switch activates. Requires manual reset with MFA confirmation.", formula: "drawdown = (peak_value - current_value) / peak_value" },
            { layer: "L5", name: "Volatility Regime", desc: "VIX-equivalent (or realized vol for crypto) monitored. If current vol > 2× historical average: position sizes halved. If vol > 3×: new entries blocked.", formula: "vol_scalar = min(1.0, avg_20d_vol / current_vol)" },
            { layer: "L6", name: "Liquidity Check", desc: "Order size ≤ 1% of instrument's 20-day average daily volume. Market impact estimation using square-root model. Illiquid assets (ADV < threshold) blocked.", formula: "impact_bps = σ × sqrt(order_size / ADV)" },
          ].map((r, i) => (
            <div key={i} className="bg-slate-900 border border-red-900/40 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="text-xs font-mono font-bold text-red-400 bg-red-950 border border-red-900 rounded px-2 py-1 shrink-0">{r.layer}</span>
                <div className="flex-1">
                  <div className="text-sm font-semibold text-white mb-1">{r.name}</div>
                  <div className="text-xs text-slate-400 mb-2">{r.desc}</div>
                  <code className="text-xs text-amber-300 font-mono">{r.formula}</code>
                </div>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Stop-Loss & Position Management" accent="amber">
        <Grid2>
          <CodeBlock code={`class StopLossManager:
    
    def calculate_initial_stop(
        self, entry_price, atr, direction
    ) -> float:
        """
        ATR-based stop: 1.5× ATR below entry (long)
        Min stop: stop_loss_pct from risk profile
        """
        atr_stop = atr * 1.5
        pct_stop = entry_price * (stop_loss_pct / 100)
        stop_distance = max(atr_stop, pct_stop)
        
        if direction == "LONG":
            return entry_price - stop_distance
        return entry_price + stop_distance

    async def update_trailing_stop(
        self, position: Position
    ):
        """
        Activated when profit > 1× risk.
        Trail by max(trailing_stop_pct, 0.5×ATR/price).
        Never move stop against position.
        """
        highest_price = await get_high_since_entry(
            position.instrument_id, 
            position.opened_at
        )
        trail_distance = highest_price * (
            position.trailing_stop_pct / 100
        )
        new_stop = highest_price - trail_distance
        
        # Only move stop UP (for longs)
        if new_stop > position.stop_loss_price:
            await update_position_stop(
                position.id, new_stop
            )
            await place_sl_order(position, new_stop)`} />
          <CodeBlock code={`class EmergencyProtocol:
    
    async def activate_kill_switch(
        self, user_id: str, 
        reason: str,
        initiated_by: str
    ):
        """
        Execution sequence (target: < 200ms):
        1. Set Redis kill flag immediately
        2. Cancel all pending orders via broker APIs
        3. Close all open positions (market orders)
        4. Disconnect market data streams
        5. Lock trading until manual reset + MFA
        6. Send emergency notifications (all channels)
        7. Write tamper-proof audit log entry
        """
        
    async def auto_close_on_anomaly(
        self, instrument: str, 
        anomaly_type: str
    ):
        """
        Triggered by:
        - Circuit breaker / halt detection
        - Price move > 10% in 5 minutes
        - Volume spike > 20× normal
        - Broker API connection loss > 30s
        - Spread > 5× normal
        - System latency > 2000ms
        """
        
    async def check_market_conditions(self):
        """
        Runs every 1 second:
        - Monitor all open position symbols
        - Cross-check against circuit breaker feeds
        - Evaluate anomaly scores
        """`} />
        </Grid2>
      </SectionCard>
    </div>
  );
}

function SecuritySection() {
  return (
    <div>
      <SectionCard title="Security Architecture" accent="red">
        <Grid2>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-red-400 font-mono uppercase tracking-widest mb-2">API Key Vault Management</div>
              <CodeBlock code={`# HashiCorp Vault Integration
# Keys NEVER stored in database

class VaultManager:
    def __init__(self):
        self.client = hvac.Client(
            url=VAULT_ADDR,
            token=VAULT_TOKEN  # from K8s SA
        )
    
    async def store_credentials(
        self, user_id: str, 
        broker: str,
        credentials: dict
    ) -> str:
        # Encrypt before storage
        path = f"secret/trading/{user_id}/{broker}"
        
        # AES-256-GCM encryption 
        # using user-derived key + server key
        encrypted = encrypt_credentials(
            credentials, 
            user_key=derive_key(user_id),
            server_key=SERVER_MASTER_KEY
        )
        
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret={"data": encrypted}
        )
        return path  # only path stored in DB
    
    async def get_credentials(
        self, vault_path: str,
        user_id: str
    ) -> dict:
        secret = self.client.secrets.kv.v2\\
            .read_secret_version(path=vault_path)
        return decrypt_credentials(
            secret["data"]["data"],
            user_key=derive_key(user_id)
        )`} />
            </div>
          </div>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-red-400 font-mono uppercase tracking-widest mb-2">Audit Log Integrity</div>
              <CodeBlock code={`class AuditLogger:
    """
    Tamper-evident audit trail
    Uses hash-chaining (blockchain-style)
    """
    
    async def log(
        self, event_type: str,
        user_id: str,
        payload: dict
    ):
        # Get previous entry hash
        prev = await db.fetchrow(
            "SELECT checksum FROM audit_logs 
             ORDER BY id DESC LIMIT 1"
        )
        
        # Chain hash
        content = json.dumps({
            "event_type": event_type,
            "user_id": user_id,
            "payload": payload,
            "ts": datetime.utcnow().isoformat(),
            "prev_hash": prev["checksum"] 
                if prev else "GENESIS"
        }, sort_keys=True)
        
        checksum = hashlib.sha256(
            content.encode()
        ).hexdigest()
        
        # INSERT ONLY (no UPDATE/DELETE possible)
        await db.execute(
            "INSERT INTO audit_logs (...) VALUES (...)",
            event_type, user_id, payload, checksum
        )`} />
            </div>
          </div>
        </Grid2>
      </SectionCard>

      <SectionCard title="Security Checklist" accent="amber">
        <Grid3>
          {[
            {
              category: "Authentication",
              items: ["bcrypt password hashing (cost=12)", "TOTP MFA (RFC 6238)", "JWT with short TTL (15min access)", "Refresh token rotation", "Account lockout after 5 failures", "Secure session invalidation"],
              color: "cyan"
            },
            {
              category: "Transport",
              items: ["TLS 1.3 enforced", "HSTS headers", "Certificate pinning (mobile)", "WSS for WebSocket", "Mutual TLS for service-to-service", "CAA DNS records"],
              color: "emerald"
            },
            {
              category: "Data Protection",
              items: ["AES-256-GCM for credentials", "Vault for API keys (never in DB)", "PII encrypted at rest", "GDPR-compliant data handling", "Secure deletion on account close", "Backup encryption"],
              color: "amber"
            },
            {
              category: "API Security",
              items: ["Rate limiting (per-endpoint)", "IP allowlisting (optional)", "CORS strict policy", "Input validation + sanitization", "SQL injection prevention (ORM)", "XSS/CSRF protection"],
              color: "violet"
            },
            {
              category: "Infrastructure",
              items: ["Network policies (K8s)", "Pod security standards", "Secrets via K8s secrets + Vault", "Image scanning (Trivy)", "Runtime monitoring (Falco)", "No root containers"],
              color: "red"
            },
            {
              category: "Compliance",
              items: ["Immutable audit logs", "Data residency controls", "SEBI algo trading rules", "SEC Rule 15c3-5 awareness", "GDPR data subject rights", "SOC 2 Type II readiness"],
              color: "gray"
            },
          ].map((cat, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <div className="mb-3"><Tag color={cat.color}>{cat.category}</Tag></div>
              <ul className="space-y-1">
                {cat.items.map((item, j) => (
                  <li key={j} className="flex items-center gap-2 text-xs text-slate-300">
                    <span className="text-emerald-400">✓</span>{item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </Grid3>
      </SectionCard>
    </div>
  );
}

function DeploymentSection() {
  return (
    <div>
      <SectionCard title="Kubernetes Architecture" accent="cyan">
        <CodeBlock code={`# Namespace strategy
namespaces:
  trading-core      # Core trading services
  trading-ai        # AI/ML workloads (GPU nodes)
  trading-data      # Databases, Kafka
  trading-infra     # Vault, monitoring
  trading-ingress   # Kong, cert-manager

# Service topology (HPA + resource limits)
Deployment: auth-service          replicas: 2-5    cpu: 250m-1000m
Deployment: signal-service        replicas: 2-8    cpu: 500m-2000m
Deployment: execution-service     replicas: 3-6    cpu: 500m-1000m  # HA critical
Deployment: risk-service          replicas: 3-6    cpu: 250m-500m   # HA critical  
Deployment: market-data-service   replicas: 2-4    cpu: 500m-2000m
Deployment: ai-inference          replicas: 1-4    gpu: 1 (T4)
StatefulSet: postgresql           replicas: 3      (primary + 2 replicas)
StatefulSet: redis-cluster        replicas: 6      (3 primary + 3 replica)
StatefulSet: kafka                replicas: 3
StatefulSet: influxdb             replicas: 2

# Critical HA requirements
execution-service:    PodDisruptionBudget minAvailable: 2
risk-service:         PodDisruptionBudget minAvailable: 2
podAntiAffinity:      spread across AZs for execution + risk

# Liveness / Readiness probes
execution-service:
  livenessProbe:  GET /health         initialDelay: 10s  period: 5s
  readinessProbe: GET /ready          initialDelay: 5s   period: 3s
  # Custom: checks broker connections are alive
  startupProbe:   GET /startup        failureThreshold: 30`} />
      </SectionCard>

      <SectionCard title="CI/CD Pipeline (GitOps)" accent="emerald">
        <CodeBlock code={`# GitHub Actions → ArgoCD GitOps Pipeline

on: push to main / PR merge

PIPELINE STAGES:
┌──────────────────────────────────────────────────────────────┐
│ 1. CODE QUALITY (parallel)                                   │
│    ├─ pytest --cov=90%+ (unit + integration tests)           │
│    ├─ ruff linting + black formatting                        │
│    ├─ mypy type checking                                     │
│    ├─ bandit security scanning                               │
│    └─ semgrep SAST (security patterns)                       │
│                                                              │
│ 2. BUILD                                                     │
│    ├─ Docker multi-stage build (distroless final image)      │
│    ├─ Trivy image vulnerability scan (block on CRITICAL)     │
│    └─ Push to ECR/GCR with SHA digest tag                    │
│                                                              │
│ 3. STAGING DEPLOY (ArgoCD)                                   │
│    ├─ Auto-sync to staging namespace                         │
│    ├─ Smoke tests (Postman/Newman collection)                │
│    ├─ Load test (k6): 1000 concurrent users                  │
│    └─ Canary: 10% traffic for 15 minutes                     │
│                                                              │
│ 4. PRODUCTION DEPLOY                                         │
│    ├─ Manual approval gate (Risk Manager sign-off)           │
│    ├─ Blue/Green deployment                                  │
│    ├─ Health check validation                                │
│    ├─ Rollback trigger: error rate > 1% within 5min          │
│    └─ Post-deploy: Datadog synthetic monitoring              │
└──────────────────────────────────────────────────────────────┘

# Terraform IaC (AWS)
resources:
  - EKS cluster (multi-AZ)
  - RDS PostgreSQL (Multi-AZ, encrypted)
  - ElastiCache Redis (cluster mode)
  - MSK Kafka
  - S3 (model artifacts, logs)
  - Secrets Manager → Vault sync
  - CloudFront + WAF
  - VPC + private subnets
  - NAT Gateway (outbound only broker calls)`} />
      </SectionCard>

      <SectionCard title="Observability Stack" accent="violet">
        <Grid2>
          <div className="space-y-2">
            {[
              { tool: "Prometheus", role: "Metrics collection: trade latency, signal generation rate, error rates, broker API health" },
              { tool: "Grafana", role: "Dashboards: Trading P&L, system health, AI model performance, risk utilization" },
              { tool: "Jaeger", role: "Distributed tracing: full signal-to-order span with service-by-service latency" },
              { tool: "ELK Stack", role: "Log aggregation, audit log search, anomaly detection on trading patterns" },
              { tool: "PagerDuty", role: "Alerting: broker down, kill switch, daily loss limit breach, system errors" },
              { tool: "Falco", role: "Runtime security: unexpected syscalls, credential access anomalies" },
            ].map((o, i) => (
              <div key={i} className="bg-slate-900 border border-slate-800 rounded p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Tag color="violet">{o.tool}</Tag>
                </div>
                <div className="text-xs text-slate-400">{o.role}</div>
              </div>
            ))}
          </div>
          <div>
            <div className="text-xs text-violet-400 font-mono uppercase tracking-widest mb-3">Key Alerts</div>
            <CodeBlock code={`# Critical Alerts (PagerDuty P1)
- broker_api_down > 30s
- execution_latency > 500ms (p99)
- kill_switch_activated
- daily_loss_limit_breached
- drawdown > 80% of limit
- kafka_consumer_lag > 10000
- vault_unreachable

# Warning Alerts (Slack P2)
- signal_generation_delay > 5s
- model_confidence_avg < 0.60
- database_replication_lag > 2s
- redis_memory > 80%
- failed_order_rate > 5%

# SLO Targets
- Order execution: < 200ms (p95)
- Signal generation: < 3s (p95)
- API response time: < 100ms (p95)
- Uptime: 99.9% (during market hours)
- RTO: 5 minutes
- RPO: 30 seconds`} />
          </div>
        </Grid2>
      </SectionCard>
    </div>
  );
}

function RoadmapSection() {
  const mvp = [
    { phase: "Weeks 1–2", title: "Foundation", tasks: ["Project scaffolding, Docker Compose dev env", "Auth service (register/login/MFA/JWT)", "User + risk profile management", "PostgreSQL schema + migrations", "Redis setup", "CI pipeline (GitHub Actions)"] },
    { phase: "Weeks 3–4", title: "Broker Integration", tasks: ["Abstract broker interface", "Alpaca connector (simplest, sandbox)", "Zerodha Kite connector", "Position/balance sync", "Vault integration for API keys", "WebSocket tick streaming"] },
    { phase: "Weeks 5–6", title: "Market Data Engine", tasks: ["InfluxDB setup + OHLCV ingestion", "Technical indicator calculation engine", "Historical data backfill pipeline", "Real-time quote service", "Basic news aggregation (NewsAPI)"] },
    { phase: "Weeks 7–9", title: "AI Signal Engine", tasks: ["XGBoost signal classifier (v1)", "LLM integration (Claude API) for reasoning", "Feature aggregation pipeline", "Signal confidence scoring", "Kafka event bus integration", "Signal storage + API endpoints"] },
    { phase: "Weeks 10–11", title: "Risk & Execution", tasks: ["6-layer risk validation engine", "Order execution service", "Position management + stops", "Kill switch implementation", "Daily P&L tracking", "Semi-auto approval flow"] },
    { phase: "Weeks 12–13", title: "Frontend MVP", tasks: ["Next.js app with auth flows", "Portfolio dashboard", "Signal feed with approve/reject", "Position monitor with P&L", "Risk settings UI", "Kill switch control panel"] },
    { phase: "Weeks 14–15", title: "Backtesting + Notifications", tasks: ["Celery backtest workers", "Walk-forward analysis engine", "Performance metrics calculation", "Telegram + email notifications", "Trade execution alerts"] },
    { phase: "Week 16", title: "MVP Launch", tasks: ["End-to-end testing (paper trading)", "Security audit + pen test", "K8s staging deployment", "Load testing", "User acceptance testing", "Production release"] },
  ];

  const enterprise = [
    { phase: "Q3 2025", title: "Advanced AI", tasks: ["LSTM price forecasting", "RL trading agent (PPO)", "Sentiment analysis (FinBERT)", "Multi-model ensemble", "Model retraining pipeline", "MLflow experiment tracking"] },
    { phase: "Q4 2025", title: "Scale", tasks: ["5+ additional broker connectors", "Monte Carlo backtesting", "Portfolio optimization (PyPortfolioOpt)", "Multi-account management", "Team/firm accounts", "IBKR + Binance connectors"] },
    { phase: "Q1 2026", title: "Intelligence", tasks: ["Economic calendar integration", "Social sentiment (Reddit/Twitter)", "Options strategy support", "Crypto perpetuals", "Cross-asset correlation", "Macro regime detection"] },
    { phase: "Q2 2026", title: "Enterprise", tasks: ["SOC 2 Type II certification", "Multi-region deployment", "Institutional API access", "White-label offering", "Compliance reporting module", "FIX protocol support"] },
  ];

  return (
    <div>
      <SectionCard title="MVP Roadmap — 16 Weeks to Production" accent="cyan">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {mvp.map((p, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Tag color="cyan">{p.phase}</Tag>
                <span className="text-sm font-semibold text-white">{p.title}</span>
              </div>
              <ul className="space-y-1">
                {p.tasks.map((t, j) => (
                  <li key={j} className="text-xs text-slate-400 flex items-start gap-2">
                    <span className="text-slate-600 shrink-0">›</span>{t}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Enterprise Roadmap — Post-MVP" accent="violet">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {enterprise.map((p, i) => (
            <div key={i} className="bg-slate-900 border border-violet-900/40 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Tag color="violet">{p.phase}</Tag>
                <span className="text-sm font-semibold text-white">{p.title}</span>
              </div>
              <ul className="space-y-1">
                {p.tasks.map((t, j) => (
                  <li key={j} className="text-xs text-slate-400 flex items-start gap-2">
                    <span className="text-violet-600 shrink-0">›</span>{t}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Compliance & Legal Considerations" accent="amber">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="text-xs text-amber-400 font-mono uppercase tracking-widest mb-2">India (SEBI)</div>
            {["Algo trading registration required for broker-level automation", "Approved algos must be registered with exchanges", "Audit trail of all signals mandatory (5 years)", "Risk management system approval for HFT", "No guaranteed returns marketing", "User must provide explicit written consent"].map((c, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-slate-400 bg-slate-900 rounded p-2">
                <span className="text-amber-400 shrink-0">!</span>{c}
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <div className="text-xs text-cyan-400 font-mono uppercase tracking-widest mb-2">US / Global</div>
            {["SEC Rule 15c3-5: Market access controls required", "FINRA rules on automated systems + supervision", "MiFID II (EU): Algo trading authorization + testing", "GDPR: Data handling, right to erasure, DPA needed", "AML/KYC requirements for financial platforms", "Consult securities law attorney before launch"].map((c, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-slate-400 bg-slate-900 rounded p-2">
                <span className="text-cyan-400 shrink-0">!</span>{c}
              </div>
            ))}
          </div>
        </div>
        <div className="mt-4 p-4 border border-amber-800/50 rounded-lg bg-amber-950/30">
          <div className="text-amber-400 font-mono text-xs font-bold uppercase tracking-widest mb-2">⚠ Important Disclaimer</div>
          <p className="text-xs text-amber-200/70 leading-relaxed">
            This platform must never guarantee trading profits. All users must be clearly informed that algorithmic trading involves 
            substantial risk of capital loss. The system is a tool to assist — not replace — sound financial judgment. 
            Obtain legal counsel, register with relevant regulatory bodies, and implement robust user disclosure before 
            accepting client capital.
          </p>
        </div>
      </SectionCard>
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────

export default function App() {
  const [active, setActive] = useState("overview");

  const renderSection = () => {
    switch (active) {
      case "overview":     return <OverviewSection />;
      case "architecture": return <ArchitectureSection />;
      case "database":     return <DatabaseSection />;
      case "api":          return <APISection />;
      case "ai_engine":    return <AIEngineSection />;
      case "risk":         return <RiskSection />;
      case "security":     return <SecuritySection />;
      case "deployment":   return <DeploymentSection />;
      case "roadmap":      return <RoadmapSection />;
      default:             return null;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100" style={{fontFamily:"'Courier New', monospace"}}>
      {/* Top bar */}
      <div className="border-b border-slate-800 bg-slate-950/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-cyan-400 font-mono text-lg">◉</span>
            <span className="font-bold text-white tracking-tight" style={{fontFamily:"Georgia, serif"}}>
              QuantumEdge <span className="text-cyan-400">AI</span>
            </span>
            <span className="hidden md:block text-xs text-slate-600 font-mono">Technical Blueprint v1.0</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400 font-mono">BLUEPRINT LOADED</span>
          </div>
        </div>
        {/* Navigation */}
        <div className="max-w-7xl mx-auto px-4 pb-0 overflow-x-auto">
          <div className="flex gap-1 min-w-max">
            {SECTIONS.map((s) => (
              <button
                key={s.id}
                onClick={() => setActive(s.id)}
                className={`px-3 py-2 text-xs font-mono rounded-t transition-all flex items-center gap-1.5 border-b-2 ${
                  active === s.id
                    ? "text-cyan-300 border-cyan-400 bg-slate-900"
                    : "text-slate-500 border-transparent hover:text-slate-300 hover:border-slate-600"
                }`}
              >
                <span>{s.icon}</span>
                <span className="hidden sm:block">{s.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {renderSection()}
      </div>

      {/* Footer */}
      <div className="border-t border-slate-900 py-4 text-center">
        <p className="text-xs text-slate-700 font-mono">
          QUANTUMEDGE AI BLUEPRINT · CAPITAL PRESERVATION FIRST · ALL DECISIONS LOGGED & AUDITABLE · NO PROFIT GUARANTEES
        </p>
      </div>
    </div>
  );
}
