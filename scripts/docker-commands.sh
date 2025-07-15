#!/bin/bash
# 🐳 Docker Commands for Budget Bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 🏗️ Build commands
build() {
    print_status "Building Budget Bot Docker image..."
    docker build -t budget-bot:latest .
    print_success "Build completed!"
}

build_dev() {
    print_status "Building development image..."
    docker-compose -f docker-compose.dev.yml build
    print_success "Development build completed!"
}

# 🚀 Run commands
run() {
    print_status "Starting Budget Bot in production mode..."
    docker-compose up -d
    print_success "Budget Bot started! Check logs with: $0 logs"
}

run_dev() {
    print_status "Starting Budget Bot in development mode..."
    docker-compose -f docker-compose.dev.yml up
}

run_with_monitoring() {
    print_status "Starting Budget Bot with monitoring..."
    docker-compose --profile monitoring up -d
    print_success "Budget Bot with monitoring started!"
    print_status "Grafana: http://localhost:3000 (admin/admin)"
    print_status "Prometheus: http://localhost:9090"
}

# 🔧 Management commands
stop() {
    print_status "Stopping Budget Bot..."
    docker-compose down
    print_success "Budget Bot stopped!"
}

restart() {
    print_status "Restarting Budget Bot..."
    docker-compose restart budget-bot
    print_success "Budget Bot restarted!"
}

# 📊 Monitoring commands
logs() {
    docker-compose logs -f budget-bot
}

status() {
    print_status "Budget Bot status:"
    docker-compose ps
}

health() {
    print_status "Checking Budget Bot health..."
    docker-compose exec budget-bot python -c "
from database import get_db_session
try:
    db = get_db_session()
    db.execute('SELECT 1')
    print('✅ Database connection: OK')
    db.close()
except Exception as e:
    print(f'❌ Database connection: {e}')
"
}

# 🧪 Testing commands
test() {
    print_status "Running tests in container..."
    docker-compose -f docker-compose.dev.yml run --rm test-runner
}

test_memory() {
    print_status "Testing memory system..."
    docker-compose -f docker-compose.dev.yml run --rm budget-bot-dev python tests/test_memory_system.py
}

# 🗄️ Database commands
migrate() {
    print_status "Running database migrations..."
    docker-compose exec budget-bot python scripts/migrate_memory_system.py
    print_success "Migrations completed!"
}

backup_db() {
    print_status "Creating database backup..."
    timestamp=$(date +%Y%m%d_%H%M%S)
    docker-compose exec budget-bot cp /app/data/budget_bot.db /app/data/backup_${timestamp}.db
    print_success "Backup created: backup_${timestamp}.db"
}

restore_db() {
    if [ -z "$1" ]; then
        print_error "Usage: $0 restore_db <backup_file>"
        exit 1
    fi
    print_warning "This will overwrite the current database!"
    read -p "Are you sure? (y/N): " confirm
    if [[ $confirm == [yY] ]]; then
        docker-compose exec budget-bot cp /app/data/$1 /app/data/budget_bot.db
        print_success "Database restored from $1"
    else
        print_status "Restore cancelled."
    fi
}

# 🧹 Cleanup commands
clean() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v
    docker system prune -f
    print_success "Cleanup completed!"
}

clean_all() {
    print_warning "This will remove ALL Docker data including volumes!"
    read -p "Are you sure? (y/N): " confirm
    if [[ $confirm == [yY] ]]; then
        docker-compose down -v
        docker system prune -a -f --volumes
        print_success "Complete cleanup done!"
    else
        print_status "Cleanup cancelled."
    fi
}

# 📦 Deployment commands
deploy() {
    print_status "Deploying to production..."
    
    # Build image
    build
    
    # Stop current instance
    stop
    
    # Start with new image
    run
    
    # Wait for healthcheck
    sleep 30
    health
    
    print_success "Deployment completed!"
}

# 🔍 Debug commands
shell() {
    print_status "Opening shell in Budget Bot container..."
    docker-compose exec budget-bot /bin/bash
}

debug() {
    print_status "Starting Budget Bot in debug mode..."
    docker-compose -f docker-compose.dev.yml run --rm -p 8080:8080 budget-bot-dev python -m pdb bot.py
}

# 📈 Performance commands
stats() {
    print_status "Container resource usage:"
    docker stats budget-bot --no-stream
}

# Help function
help() {
    echo "🤖 Budget Bot Docker Management"
    echo ""
    echo "🏗️  Build Commands:"
    echo "  build         Build production Docker image"
    echo "  build_dev     Build development Docker image"
    echo ""
    echo "🚀 Run Commands:"
    echo "  run           Start in production mode"
    echo "  run_dev       Start in development mode"
    echo "  run_with_monitoring  Start with Grafana/Prometheus"
    echo ""
    echo "🔧 Management:"
    echo "  stop          Stop all services"
    echo "  restart       Restart Budget Bot"
    echo "  logs          Show logs"
    echo "  status        Show container status"
    echo "  health        Check application health"
    echo ""
    echo "🧪 Testing:"
    echo "  test          Run all tests"
    echo "  test_memory   Test memory system"
    echo ""
    echo "🗄️  Database:"
    echo "  migrate       Run database migrations"
    echo "  backup_db     Create database backup"
    echo "  restore_db    Restore database from backup"
    echo ""
    echo "🧹 Cleanup:"
    echo "  clean         Clean up Docker resources"
    echo "  clean_all     Complete cleanup (destructive!)"
    echo ""
    echo "📦 Deployment:"
    echo "  deploy        Deploy to production"
    echo ""
    echo "🔍 Debug:"
    echo "  shell         Open shell in container"
    echo "  debug         Start in debug mode"
    echo "  stats         Show resource usage"
    echo ""
    echo "Usage: $0 <command>"
}

# Main script logic
case "$1" in
    build)          build ;;
    build_dev)      build_dev ;;
    run)            run ;;
    run_dev)        run_dev ;;
    run_with_monitoring) run_with_monitoring ;;
    stop)           stop ;;
    restart)        restart ;;
    logs)           logs ;;
    status)         status ;;
    health)         health ;;
    test)           test ;;
    test_memory)    test_memory ;;
    migrate)        migrate ;;
    backup_db)      backup_db ;;
    restore_db)     restore_db "$2" ;;
    clean)          clean ;;
    clean_all)      clean_all ;;
    deploy)         deploy ;;
    shell)          shell ;;
    debug)          debug ;;
    stats)          stats ;;
    help|*)         help ;;
esac