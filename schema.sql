-- Finance Tracker Database Schema

-- Kategori pengeluaran/pemasukan
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transaksi utama
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    category_id INTEGER,
    account_id INTEGER,
    description TEXT,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

-- Pemasukan (dengan sumber)
CREATE TABLE IF NOT EXISTS income_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL UNIQUE,
    source TEXT NOT NULL,
    FOREIGN KEY(transaction_id) REFERENCES transactions(id)
);

-- Hutang-piutang antar teman
CREATE TABLE IF NOT EXISTS debts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    friend_name TEXT NOT NULL,
    amount INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('owe', 'owed')), -- owe = saya hutang ke teman, owed = teman hutang ke saya
    description TEXT,
    date DATE NOT NULL,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'settled')),
    settled_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pembayaran hutang
CREATE TABLE IF NOT EXISTS debt_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debt_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(debt_id) REFERENCES debts(id)
);

-- Default categories
INSERT OR IGNORE INTO categories (name, type) VALUES
('Makanan', 'expense'),
('Transport', 'expense'),
('Tagihan', 'expense'),
('Hiburan', 'expense'),
('Belanja', 'expense'),
('Kesehatan', 'expense'),
('Gaji', 'income'),
('Freelance', 'income'),
('Bonus', 'income'),
('Lainnya', 'expense'),
('Lainnya (Pemasukan)', 'income');

-- Index untuk performa query
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_debts_friend ON debts(friend_name);
CREATE INDEX IF NOT EXISTS idx_debts_status ON debts(status);

-- Rekening / Dompet
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('bank', 'ewallet', 'cash')),
    icon TEXT DEFAULT '',
    color TEXT DEFAULT '#3b82f6',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default accounts
INSERT OR IGNORE INTO accounts (name, type, icon, color) VALUES
('Cash', 'cash', '💵', '#22c55e'),
('BRI', 'bank', '🏦', '#1d4ed8'),
('ShopeePay', 'ewallet', '🟠', '#f97316'),
('GoPay', 'ewallet', '🟢', '#22d3ee'),
('SeaBank', 'bank', '🌊', '#0ea5e9');

CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
