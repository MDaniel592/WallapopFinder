DROP TABLE IF EXISTS articles;
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY,
    wallapop_id INTEGER NOT NULL UNIQUE,
    url TEXT NOT NULL UNIQUE, 
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    price FLOAT DEFAULT -1,
    last_updated INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1
);

DROP TABLE IF EXISTS users_filters;
CREATE TABLE IF NOT EXISTS users_filters (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL, 
    search TEXT NOT NULL,
    filters JSON,
    notified_at INTEGER DEFAULT 0,
    UNIQUE(user_id, search)
);

DROP TABLE IF EXISTS users_articles;
CREATE TABLE IF NOT EXISTS users_articles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    notified TEXT DEFAULT FALSE,
    UNIQUE(user_id, product_id)
);