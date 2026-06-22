#!/usr/bin/env bash
# Provision Neon PostgreSQL for Migration Utility + wire into Vercel.
#
# Usage:
#   ./scripts/setup_production_db.sh
#   ./scripts/setup_production_db.sh "postgresql://user:pass@host/db?sslmode=require"
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERCEL_SCOPE="${VERCEL_SCOPE:-dashsanat2024-9148s-projects}"
VERCEL_PROJECT="${VERCEL_PROJECT:-migration-utility}"
NEON_PROJECT="${NEON_PROJECT:-migration-utility}"

echo "=== Migration Utility — production database setup ==="
echo ""

# --- Step 1: obtain DATABASE_URL ---
if [[ -n "${1:-}" ]]; then
  DATABASE_URL="$1"
elif [[ -n "${DATABASE_URL:-}" ]]; then
  echo "Using DATABASE_URL from environment."
else
  echo "Step 1 — Create a Neon database (one-time)"
  echo "  1. Open https://console.neon.tech and sign in"
  echo "  2. New Project → name: ${NEON_PROJECT}"
  echo "  3. Copy the connection string (use 'Pooled connection' for serverless)"
  echo "     Must include: ?sslmode=require"
  echo ""
  read -r -p "Paste DATABASE_URL: " DATABASE_URL
fi

if [[ -z "$DATABASE_URL" ]]; then
  echo "ERROR: DATABASE_URL is required." >&2
  exit 1
fi

if [[ "$DATABASE_URL" != *"sslmode="* ]]; then
  if [[ "$DATABASE_URL" == *"?"* ]]; then
    DATABASE_URL="${DATABASE_URL}&sslmode=require"
  else
    DATABASE_URL="${DATABASE_URL}?sslmode=require"
  fi
  echo "Appended sslmode=require to connection string."
fi

# --- Step 2: run migrations ---
echo ""
echo "Step 2 — Running Alembic migrations..."
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
export DATABASE_URL
alembic upgrade head
echo "Migrations complete."

# --- Step 3: push to Vercel ---
echo ""
echo "Step 3 — Setting Vercel environment variables..."
if ! command -v vercel >/dev/null 2>&1; then
  VC="npx vercel@latest"
else
  VC="vercel"
fi

for TARGET in production preview development; do
  echo "$DATABASE_URL" | $VC env add DATABASE_URL "$TARGET" --force --scope "$VERCEL_SCOPE" --yes 2>/dev/null \
    || echo "$DATABASE_URL" | $VC env add DATABASE_URL "$TARGET" --scope "$VERCEL_SCOPE" --yes
done

# CORS for production UI
CORS="https://migration-utility.vercel.app,http://localhost:5174,http://localhost:3000"
echo "$CORS" | $VC env add CORS_ORIGINS production --force --scope "$VERCEL_SCOPE" --yes 2>/dev/null \
  || echo "$CORS" | $VC env add CORS_ORIGINS production --scope "$VERCEL_SCOPE" --yes

echo ""
echo "Step 4 — Redeploying Vercel production..."
$VC deploy --prod --yes --scope "$VERCEL_SCOPE"

echo ""
echo "=== Done ==="
echo "  UI:  https://migration-utility.vercel.app"
echo "  API: https://migration-utility.vercel.app/api/health"
echo ""
echo "Verify: curl -s https://migration-utility.vercel.app/api/health"
echo "        curl -s https://migration-utility.vercel.app/api/projects"
