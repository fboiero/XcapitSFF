#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Production deployment script for XcapitSFF
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env"
MARKER_FILE="$PROJECT_DIR/.deploy_initialized"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# =============================================================================
# 1. Check prerequisites
# =============================================================================
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &>/dev/null; then
        log_error "docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
        log_error "docker-compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    if [[ ! -f "$ENV_FILE" ]]; then
        log_error ".env file not found at $ENV_FILE"
        log_error "Copy .env.example to .env and configure it before deploying."
        exit 1
    fi

    # Validate required environment variables
    source "$ENV_FILE"
    local required_vars=("POSTGRES_PASSWORD" "SECRET_KEY" "ANTHROPIC_API_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set in .env"
            exit 1
        fi
    done

    log_info "All prerequisites satisfied."
}

# =============================================================================
# 2. Determine compose command
# =============================================================================
compose_cmd() {
    if docker compose version &>/dev/null 2>&1; then
        docker compose -f "$COMPOSE_FILE" "$@"
    else
        docker-compose -f "$COMPOSE_FILE" "$@"
    fi
}

# =============================================================================
# 3. Build images
# =============================================================================
build_images() {
    log_info "Building production Docker images..."
    compose_cmd build --no-cache app
    log_info "Images built successfully."
}

# =============================================================================
# 4. Run database migrations
# =============================================================================
run_migrations() {
    log_info "Running database migrations..."

    # Start only postgres so migrations can run
    compose_cmd up -d postgres
    sleep 5

    # Run alembic migrations inside the app container
    compose_cmd run --rm app \
        python -m alembic upgrade head

    log_info "Migrations completed."
}

# =============================================================================
# 5. Seed database (first deploy only)
# =============================================================================
seed_database() {
    if [[ -f "$MARKER_FILE" ]]; then
        log_info "Database already seeded (marker file exists). Skipping seed."
        return
    fi

    log_info "First deploy detected. Seeding database..."

    compose_cmd run --rm app \
        python -m scripts.seed_all

    touch "$MARKER_FILE"
    log_info "Database seeded successfully."
}

# =============================================================================
# 6. Start all services
# =============================================================================
start_services() {
    log_info "Starting all services..."
    compose_cmd up -d
    log_info "Services started."
}

# =============================================================================
# 7. Health check
# =============================================================================
health_check() {
    log_info "Waiting for services to become healthy..."

    local max_retries=30
    local retry=0

    while [[ $retry -lt $max_retries ]]; do
        if curl -sf http://localhost/nginx-health &>/dev/null; then
            log_info "Nginx is healthy."
            break
        fi
        retry=$((retry + 1))
        log_warn "Health check attempt $retry/$max_retries failed. Retrying in 5s..."
        sleep 5
    done

    if [[ $retry -eq $max_retries ]]; then
        log_error "Services did not become healthy within the expected time."
        log_error "Check logs with: docker compose -f $COMPOSE_FILE logs"
        exit 1
    fi

    # Verify the app endpoint
    retry=0
    while [[ $retry -lt 10 ]]; do
        if curl -sf http://localhost/health &>/dev/null; then
            log_info "Application health check passed."
            break
        fi
        retry=$((retry + 1))
        sleep 3
    done

    if [[ $retry -eq 10 ]]; then
        log_warn "Application health endpoint not responding, but nginx is up."
        log_warn "Check app logs: docker compose -f $COMPOSE_FILE logs app"
    fi
}

# =============================================================================
# 8. Print status
# =============================================================================
print_status() {
    echo ""
    echo "============================================="
    echo "  XcapitSFF Deployment Status"
    echo "============================================="
    compose_cmd ps
    echo ""
    log_info "Deployment complete."
    echo ""
    echo "  Application:  http://localhost"
    echo "  Health check: http://localhost/health"
    echo "  Logs:         docker compose -f $COMPOSE_FILE logs -f"
    echo "  Stop:         docker compose -f $COMPOSE_FILE down"
    echo "============================================="
}

# =============================================================================
# Main
# =============================================================================
main() {
    log_info "Starting XcapitSFF production deployment..."
    echo ""

    check_prerequisites
    build_images
    run_migrations
    seed_database
    start_services
    health_check
    print_status
}

main "$@"
