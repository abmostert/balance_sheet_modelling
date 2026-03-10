CREATE TABLE IF NOT EXISTS canonical_balance_sheet (
  ticker            TEXT NOT NULL,
  statement         TEXT NOT NULL DEFAULT 'balance_sheet',
  period_type       TEXT NOT NULL,
  period_end        DATE NOT NULL,
  canonical_key     TEXT NOT NULL,
  category          TEXT,
  value             DOUBLE PRECISION,
  source            TEXT NOT NULL DEFAULT 'yfinance',
  retrieved_at_utc  TIMESTAMPTZ NOT NULL,

  PRIMARY KEY (ticker, statement, period_type, period_end, canonical_key)
);

CREATE INDEX IF NOT EXISTS idx_canonical_balance_sheet_ticker_period
  ON canonical_balance_sheet (ticker, period_end);

CREATE INDEX IF NOT EXISTS idx_canonical_balance_sheet_canonical_key
  ON canonical_balance_sheet (canonical_key);