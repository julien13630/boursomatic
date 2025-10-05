#!/bin/bash

# Script to test database creation and recreation
# This script demonstrates how to use Alembic migrations

set -e

echo "=== Database Migration Test Script ==="
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not set. Using default: postgresql+psycopg://postgres:postgres@localhost:5432/boursomatic"
    export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/boursomatic"
fi

echo "Database URL: $DATABASE_URL"
echo ""

# Function to create database (requires PostgreSQL running)
create_db() {
    echo "Creating database..."
    # Extract database name from URL
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
    # Note: This requires psql client and appropriate permissions
    # psql -U postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
    # psql -U postgres -c "CREATE DATABASE $DB_NAME;"
    echo "Note: Manual database creation may be required"
}

# Function to run migrations
run_migrations() {
    echo "Running migrations..."
    cd "$(dirname "$0")/.."
    source venv/bin/activate 2>/dev/null || echo "Virtual environment not found, using system Python"
    alembic upgrade head
    echo "Migrations completed successfully!"
}

# Function to rollback migrations
rollback_migrations() {
    echo "Rolling back all migrations..."
    cd "$(dirname "$0")/.."
    source venv/bin/activate 2>/dev/null || echo "Virtual environment not found, using system Python"
    alembic downgrade base
    echo "Rollback completed!"
}

# Function to show current migration status
show_status() {
    echo "Current migration status:"
    cd "$(dirname "$0")/.."
    source venv/bin/activate 2>/dev/null || echo "Virtual environment not found, using system Python"
    alembic current
    echo ""
    echo "Available migrations:"
    alembic history
}

# Main menu
case "${1:-help}" in
    create)
        create_db
        ;;
    migrate)
        run_migrations
        ;;
    rollback)
        rollback_migrations
        ;;
    recreate)
        echo "Recreating database (rollback + migrate)..."
        rollback_migrations
        run_migrations
        ;;
    status)
        show_status
        ;;
    help|*)
        echo "Usage: $0 {create|migrate|rollback|recreate|status}"
        echo ""
        echo "Commands:"
        echo "  create    - Create the database (manual step, requires PostgreSQL)"
        echo "  migrate   - Run pending migrations"
        echo "  rollback  - Rollback all migrations"
        echo "  recreate  - Rollback and re-apply all migrations"
        echo "  status    - Show current migration status"
        echo ""
        echo "Prerequisites:"
        echo "  1. PostgreSQL must be running"
        echo "  2. DATABASE_URL environment variable should be set"
        echo "  3. Virtual environment should be activated or dependencies installed"
        exit 1
        ;;
esac

echo ""
echo "Done!"
