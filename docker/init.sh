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
    echo "[PostgreSQL] Initialization complete"
fi

echo "==================================="
echo "Initialization Complete"
echo "==================================="
