#!/usr/bin/env bash
#
# CVGen Health Check Script
# Verifies that all services in the Docker Compose stack are healthy and responsive
#
# Usage:
#   bash scripts/health_check.sh
#
# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CVGEN_URL="${CVGEN_URL:-http://localhost:8000}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
TIMEOUT=5

# Counters
PASSED=0
FAILED=0

# Helper function to print colored output
print_status() {
    local status=$1
    local message=$2

    if [ "$status" == "PASS" ]; then
        echo -e "${GREEN}✓${NC} $message"
        PASSED=$((PASSED + 1))
    elif [ "$status" == "FAIL" ]; then
        echo -e "${RED}✗${NC} $message"
        FAILED=$((FAILED + 1))
    elif [ "$status" == "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
    else
        echo -e "${BLUE}ℹ${NC} $message"
    fi
}

print_section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
}

# Main health check function
check_service() {
    local service_name=$1
    local url=$2
    local endpoint=$3

    echo -e "\n${BLUE}Testing $service_name...${NC}"

    # Test basic connectivity
    if timeout $TIMEOUT curl -sf "$url$endpoint" > /dev/null 2>&1; then
        print_status "PASS" "$service_name is responding"
        return 0
    else
        print_status "FAIL" "$service_name is not responding or unhealthy"
        return 1
    fi
}

# Start of script
clear
print_section "CVGen Health Check"

echo -e "\n${BLUE}Checking service connectivity...${NC}"
echo "  CVGen:   $CVGEN_URL"
echo "  Ollama:  $OLLAMA_URL"
echo "  Qdrant:  $QDRANT_URL"

# Check CVGen API
print_section "CVGen API Health"
if check_service "CVGen API" "$CVGEN_URL" "/api/v1/health"; then
    # Try to get version info
    if timeout $TIMEOUT curl -sf "$CVGEN_URL/docs" > /dev/null 2>&1; then
        print_status "PASS" "API documentation available at $CVGEN_URL/docs"
    fi
else
    print_status "WARN" "CVGen may still be starting up. Check with: docker logs cvgen-api"
fi

# Check Ollama
print_section "Ollama LLM Runtime"
if check_service "Ollama" "$OLLAMA_URL" "/api/tags"; then
    # Get list of loaded models
    if timeout $TIMEOUT command -v jq > /dev/null 2>&1; then
        models=$(timeout $TIMEOUT curl -sf "$OLLAMA_URL/api/tags" 2>/dev/null | jq -r '.models[].name // empty' | head -5)
        if [ -n "$models" ]; then
            print_status "PASS" "Loaded models:"
            echo "$models" | sed 's/^/    • /'
        else
            print_status "WARN" "No models currently loaded. Run: docker exec cvgen-ollama ollama pull qwen2.5:7b"
        fi
    else
        print_status "INFO" "jq not found. Run: apt-get install jq (on Linux) or brew install jq (on macOS)"
    fi
else
    print_status "WARN" "Ollama may still be starting. Check with: docker logs cvgen-ollama"
fi

# Check Qdrant
print_section "Qdrant Vector Database"
if timeout $TIMEOUT curl -sf "$QDRANT_URL/health" > /dev/null 2>&1; then
    print_status "PASS" "Qdrant is responding"

    # Try to get collections
    if timeout $TIMEOUT command -v jq > /dev/null 2>&1; then
        collections=$(timeout $TIMEOUT curl -sf "$QDRANT_URL/collections" 2>/dev/null | jq -r '.result.collections[].name // empty')
        if [ -n "$collections" ]; then
            print_status "PASS" "Available collections:"
            echo "$collections" | sed 's/^/    • /'
        else
            print_status "INFO" "No collections yet. RAG initialization may be pending."
        fi
    fi
else
    print_status "WARN" "Qdrant may still be starting. Check with: docker logs cvgen-qdrant"
fi

# Summary
print_section "Health Check Summary"

total=$((PASSED + FAILED))
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed! ($PASSED/$total)${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Open http://localhost:8000 in your browser"
    echo "  2. Check API docs at http://localhost:8000/docs"
    echo "  3. View logs: docker logs -f cvgen-api"
    echo ""
    exit 0
else
    echo -e "${YELLOW}Some services are not ready ($PASSED passed, $FAILED failed)${NC}"
    echo ""
    echo -e "${BLUE}Troubleshooting:${NC}"
    echo "  • Check Docker is running: docker ps"
    echo "  • View container logs: docker logs <container-name>"
    echo "  • Verify compose file: docker-compose -f docker-compose.full.yml config"
    echo "  • Restart services: docker-compose -f docker-compose.full.yml restart"
    echo ""
    exit 1
fi
