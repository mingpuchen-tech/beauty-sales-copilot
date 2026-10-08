-- Execute on a NEW, EMPTY PostgreSQL database; mirrors SQLAlchemy models.
-- This is a sandbox schema, not production financial ledger infrastructure.
CREATE TABLE customers (id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL DEFAULT 1, name VARCHAR(120) NOT NULL, industry VARCHAR(30) NOT NULL DEFAULT 'BEAUTY', referrer_id INTEGER REFERENCES customers(id));
CREATE INDEX ix_customers_tenant_id ON customers(tenant_id);
CREATE TABLE wallets (customer_id INTEGER PRIMARY KEY REFERENCES customers(id), prepaid_cents INTEGER NOT NULL DEFAULT 0 CHECK(prepaid_cents>=0), points INTEGER NOT NULL DEFAULT 0 CHECK(points>=0));
CREATE TABLE rules (id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL, direct_reward_bps INTEGER NOT NULL DEFAULT 500 CHECK(direct_reward_bps BETWEEN 0 AND 1500), max_point_discount_bps INTEGER NOT NULL DEFAULT 5000 CHECK(max_point_discount_bps BETWEEN 0 AND 5000), active INTEGER NOT NULL DEFAULT 1, UNIQUE(tenant_id,version));
CREATE INDEX ix_rules_tenant_id ON rules(tenant_id);
CREATE TABLE purchases (id SERIAL PRIMARY KEY,tenant_id INTEGER NOT NULL DEFAULT 1,customer_id INTEGER NOT NULL REFERENCES customers(id),amount_cents INTEGER NOT NULL CHECK(amount_cents>0),points_used INTEGER NOT NULL DEFAULT 0 CHECK(points_used>=0),prepaid_used_cents INTEGER NOT NULL DEFAULT 0 CHECK(prepaid_used_cents>=0),external_paid_cents INTEGER NOT NULL DEFAULT 0 CHECK(external_paid_cents>=0),reward_basis_cents INTEGER NOT NULL, reward_points INTEGER NOT NULL DEFAULT 0,referrer_id INTEGER,rule_version INTEGER NOT NULL,status VARCHAR(30) NOT NULL DEFAULT 'PAID',created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE wallet_ledger (id SERIAL PRIMARY KEY,customer_id INTEGER NOT NULL REFERENCES customers(id),purchase_id INTEGER,kind VARCHAR(40) NOT NULL,prepaid_delta_cents INTEGER NOT NULL DEFAULT 0,points_delta INTEGER NOT NULL DEFAULT 0,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX ix_wallet_ledger_customer_id ON wallet_ledger(customer_id);
CREATE TABLE idempotency_keys (key VARCHAR(128) PRIMARY KEY,operation VARCHAR(40) NOT NULL,resource_id INTEGER NOT NULL);
INSERT INTO rules(tenant_id,version,direct_reward_bps,max_point_discount_bps) VALUES(1,1,500,5000);
