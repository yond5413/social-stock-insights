-- Enable pg_trgm extension for fuzzy search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create tickers table
CREATE TABLE IF NOT EXISTS tickers (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    logo_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for fast searching
CREATE INDEX IF NOT EXISTS idx_tickers_symbol_trgm ON tickers USING gin (symbol gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_tickers_name_trgm ON tickers USING gin (name gin_trgm_ops);

-- Create search function
CREATE OR REPLACE FUNCTION search_tickers(query_text TEXT)
RETURNS TABLE (
    symbol TEXT,
    name TEXT,
    logo_url TEXT,
    similarity REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.symbol,
        t.name,
        t.logo_url,
        GREATEST(
            similarity(t.symbol, query_text),
            similarity(t.name, query_text)
        )::REAL as similarity
    FROM
        tickers t
    WHERE
        t.symbol % query_text OR
        t.name % query_text OR
        t.symbol ILIKE query_text || '%' OR
        t.name ILIKE '%' || query_text || '%'
    ORDER BY
        similarity DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;
