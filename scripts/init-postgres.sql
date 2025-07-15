-- 🗄️ PostgreSQL initialization script for Budget Bot
-- This script runs when PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'Europe/Amsterdam';

-- Create additional indexes for better performance
-- (These will be created after tables are created by SQLAlchemy)

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE budget_bot TO budget_user;

-- Create schema for future migrations
CREATE SCHEMA IF NOT EXISTS migrations;
GRANT ALL PRIVILEGES ON SCHEMA migrations TO budget_user;

-- Log initialization
\echo 'Budget Bot PostgreSQL database initialized successfully!'