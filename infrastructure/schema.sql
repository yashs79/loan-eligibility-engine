-- Database schema for Loan Eligibility Engine

-- Users table to store user information from CSV uploads
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    monthly_income NUMERIC(12, 2) NOT NULL,
    credit_score INTEGER NOT NULL,
    employment_status VARCHAR(50) NOT NULL,
    age INTEGER NOT NULL,
    debt_to_income_ratio NUMERIC(5, 2),
    existing_loans INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id VARCHAR(36) -- To track which CSV batch this user came from
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Loan products table to store information scraped from websites
CREATE TABLE IF NOT EXISTS loan_products (
    product_id SERIAL PRIMARY KEY,
    provider_name VARCHAR(255) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    interest_rate NUMERIC(5, 2) NOT NULL,
    min_loan_amount NUMERIC(12, 2) NOT NULL,
    max_loan_amount NUMERIC(12, 2) NOT NULL,
    loan_term_months INTEGER NOT NULL,
    min_credit_score INTEGER,
    min_monthly_income NUMERIC(12, 2),
    max_debt_to_income NUMERIC(5, 2),
    min_employment_years NUMERIC(3, 1),
    min_age INTEGER,
    max_age INTEGER,
    other_criteria JSONB,
    source_url TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on provider and product name
CREATE INDEX IF NOT EXISTS idx_loan_products_name ON loan_products(provider_name, product_name);

-- Matches table to link users with eligible loan products
CREATE TABLE IF NOT EXISTS matches (
    match_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    product_id INTEGER REFERENCES loan_products(product_id),
    match_score NUMERIC(5, 2), -- Confidence score for the match (0-100)
    match_reason TEXT, -- Explanation of why this match was made
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN DEFAULT FALSE, -- Whether user has been notified about this match
    UNIQUE(user_id, product_id) -- Prevent duplicate matches
);

-- Create index for faster lookups by user_id
CREATE INDEX IF NOT EXISTS idx_matches_user_id ON matches(user_id);

-- Notifications table to track emails sent to users
CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    email_subject VARCHAR(255),
    email_body TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) -- 'sent', 'failed', etc.
);

-- Create function to update timestamp on record update
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Create trigger to automatically update timestamp on users table
CREATE TRIGGER update_users_modtime
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();
