#!/bin/bash
# =============================================================================
# Minager Initialization Script
# This script runs on container startup to initialize databases and services
# =============================================================================

set -e  # Exit on error

echo "==================================="
echo "Minager Initialization Script"
echo "==================================="

# =============================================================================
# PostgreSQL Initialization
# =============================================================================
if [ -n "$POSTGRES_DB" ]; then
    echo "[PostgreSQL] Database '$POSTGRES_DB' is ready"
    echo "[PostgreSQL] Creating extensions if needed..."

    # Uncomment if you need specific PostgreSQL extensions
    # psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    #     CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    #     CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    # EOSQL

    echo "[PostgreSQL] Initialization complete"
fi

# =============================================================================
# Additional initialization can be added here
# =============================================================================
# - Create default users
# - Seed initial data
# - Run custom SQL scripts
# - Configure database parameters
# =============================================================================

echo "==================================="
echo "Initialization Complete"
echo "==================================="
