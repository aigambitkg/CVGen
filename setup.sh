#!/usr/bin/env bash

###############################################################################
# CVGen - Quantum Computing for Every Device
# One-Command Docker Setup Script
#
# This script handles complete setup and initialization of CVGen with Docker
# Includes: OS detection, Docker/Docker Compose installation, GPU detection,
#           interactive configuration, and service startup
###############################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Global configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.full.yml"
CONTAINER_CHECK_TIMEOUT=120  # seconds

# ============================================================================
# Utility Functions
# ============================================================================

print_header() {
    echo -e "\n${BLUE}═════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═════════════════════════════════════════════════════${NC}\n"
}

print_status() {
    local status=$1
    local message=$2

    case $status in
        "SUCCESS")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        "INFO")
            echo -e "${CYAN}ℹ${NC} $message"
            ;;
        *)
            echo -e "${PURPLE}→${NC} $message"
            ;;
    esac
}

print_section() {
    echo -e "\n${CYAN}▶ $1${NC}\n"
}

print_divider() {
    echo -e "${BLUE}───────────────────────────────────────────────────${NC}\n"
}

ask_yes_no() {
    local prompt=$1
    local response

    while true; do
        echo -ne "${YELLOW}$prompt${NC} (y/n): "
        read -r response
        case "$response" in
            [yY][eE][sS] | [yY])
                return 0
                ;;
            [nN][oO] | [nN])
                return 1
                ;;
            *)
                echo -e "${RED}Please answer y or n${NC}"
                ;;
        esac
    done
}

ask_choice() {
    local prompt=$1
    shift
    local options=("$@")
    local choice

    echo -e "\n${YELLOW}$prompt${NC}"
    for i in "${!options[@]}"; do
        echo "  $((i + 1)). ${options[$i]}"
    done

    while true; do
        echo -ne "${YELLOW}Select option (1-${#options[@]}):${NC} "
        read -r choice

        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
            echo "${options[$((choice - 1))]}"
            return 0
        else
            echo -e "${RED}Invalid selection. Please try again.${NC}"
        fi
    done
}

ask_input() {
    local prompt=$1
    local default=$2
    local input

    echo -ne "${YELLOW}$prompt${NC}"
    if [ -n "$default" ]; then
        echo -ne " [${CYAN}$default${NC}]: "
    else
        echo -ne ": "
    fi

    read -r input
    echo "${input:-$default}"
}

# ============================================================================
# Detection Functions
# ============================================================================

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

detect_architecture() {
    local arch
    arch=$(uname -m)

    case $arch in
        x86_64 | amd64)
            echo "amd64"
            ;;
        aarch64 | arm64)
            echo "arm64"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

detect_gpu() {
    # Check for NVIDIA GPU
    if command -v nvidia-smi &> /dev/null; then
        local vram
        vram=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
        echo "nvidia"
        return 0
    fi

    # Check for Apple Silicon (Metal)
    if [[ "$(detect_os)" == "macos" ]]; then
        if sysctl -a | grep -q "machdep.cpu.brand_string.*Apple"; then
            echo "apple_silicon"
            return 0
        fi
    fi

    # Check for AMD GPU
    if command -v rocm-smi &> /dev/null; then
        echo "amd"
        return 0
    fi

    echo "none"
}

detect_ram() {
    local ram_mb

    if [[ "$(detect_os)" == "linux" ]]; then
        ram_mb=$(grep MemTotal /proc/meminfo | awk '{print int($2 / 1024)}')
    elif [[ "$(detect_os)" == "macos" ]]; then
        ram_mb=$(vm_stat | grep "Pages free" | awk '{printf "%.0f\n", $3 * 4 / 1024}')
    else
        ram_mb=8192  # Default guess
    fi

    echo $((ram_mb / 1024))  # Convert to GB
}

check_docker_installed() {
    if command -v docker &> /dev/null; then
        return 0
    else
        return 1
    fi
}

check_docker_compose_installed() {
    if command -v docker-compose &> /dev/null; then
        return 0
    elif docker compose version &> /dev/null; then
        return 0
    else
        return 1
    fi
}

check_docker_running() {
    if docker ps &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# Installation Functions
# ============================================================================

install_docker_linux() {
    print_section "Installing Docker on Linux"

    if ! check_docker_installed; then
        print_status "INFO" "Running Docker installation script..."
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sudo bash /tmp/get-docker.sh
        sudo usermod -aG docker "$USER"
        print_status "SUCCESS" "Docker installed. You may need to log out and back in."
    else
        print_status "SUCCESS" "Docker is already installed"
    fi
}

install_docker_macos() {
    print_section "Docker on macOS"

    if ! check_docker_installed; then
        print_status "WARNING" "Docker Desktop is required on macOS"
        print_status "INFO" "Please install from: https://www.docker.com/products/docker-desktop"
        ask_yes_no "Open Docker Desktop download page?" && open "https://www.docker.com/products/docker-desktop"
        return 1
    else
        print_status "SUCCESS" "Docker is already installed"
    fi
}

install_docker_windows() {
    print_section "Docker on Windows"

    if ! check_docker_installed; then
        print_status "WARNING" "Docker Desktop is required on Windows"
        print_status "INFO" "Please install from: https://www.docker.com/products/docker-desktop"
        start "https://www.docker.com/products/docker-desktop" 2>/dev/null || true
        return 1
    else
        print_status "SUCCESS" "Docker is already installed"
    fi
}

setup_docker_daemon_gpu_nvidia() {
    print_section "Configuring NVIDIA GPU support"

    if ! command -v nvidia-docker &> /dev/null; then
        print_status "INFO" "Installing NVIDIA Docker runtime..."
        if check_docker_installed; then
            curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
            distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
            curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
                sudo tee /etc/apt/sources.list.d/nvidia-docker.list
            sudo apt-get update && sudo apt-get install -y nvidia-docker2
            sudo systemctl restart docker
            print_status "SUCCESS" "NVIDIA Docker runtime installed"
        fi
    else
        print_status "SUCCESS" "NVIDIA Docker runtime is already installed"
    fi
}

# ============================================================================
# Configuration Functions
# ============================================================================

recommend_model_for_ram() {
    local ram_gb=$1

    if [ "$ram_gb" -lt 4 ]; then
        echo "phi3:mini"
    elif [ "$ram_gb" -lt 8 ]; then
        echo "phi3:mini"
    elif [ "$ram_gb" -lt 16 ]; then
        echo "qwen2.5:7b"
    elif [ "$ram_gb" -lt 32 ]; then
        echo "qwen2.5:14b"
    else
        echo "qwen2.5:32b"
    fi
}

model_size_gb() {
    local model=$1

    case "$model" in
        "phi3:mini")
            echo "2.2"
            ;;
        "qwen2.5:7b")
            echo "4.0"
            ;;
        "mistral:latest")
            echo "4.1"
            ;;
        "qwen2.5:14b")
            echo "8.9"
            ;;
        "qwen2.5:32b")
            echo "20.3"
            ;;
        *)
            echo "4.0"
            ;;
    esac
}

configure_environment() {
    print_header "CVGen Configuration"

    local os
    local ram_gb
    local gpu_type
    local recommended_model

    os=$(detect_os)
    ram_gb=$(detect_ram)
    gpu_type=$(detect_gpu)
    recommended_model=$(recommend_model_for_ram "$ram_gb")

    print_status "INFO" "Detected System Information:"
    echo "  OS: $os | RAM: ${ram_gb}GB | GPU: $gpu_type | Architecture: $(detect_architecture)"
    echo ""

    # Model selection
    print_section "LLM Model Selection"

    echo "Available models (recommended: $recommended_model):"
    echo "  • phi3:mini        - 2.2GB - Very fast, best for <4GB RAM"
    echo "  • qwen2.5:7b       - 4.0GB - Recommended, balanced"
    echo "  • mistral:latest   - 4.1GB - Fast, good coding"
    echo "  • qwen2.5:14b      - 8.9GB - Better quality, 8-16GB RAM"
    echo "  • qwen2.5:32b      - 20.3GB - Best quality, 32GB+ RAM"
    echo ""

    local model
    model=$(ask_input "Select model" "$recommended_model")

    # Port selection
    print_section "Port Configuration"
    local port
    port=$(ask_input "CVGen API port" "8000")

    # Quantum backend selection
    print_section "Quantum Backend Mode"

    echo "Available backends:"
    echo "  1. Simulator (local, no quantum hardware needed)"
    echo "  2. Origin Pilot (distributed simulator)"
    echo "  3. IBM Quantum (cloud, requires API token)"
    echo "  4. AWS Braket (cloud, requires credentials)"
    echo "  5. Azure Quantum (cloud, requires credentials)"
    echo ""

    local backend
    backend=$(ask_choice "Select quantum backend" \
        "Simulator" "Origin Pilot" "IBM Quantum" "AWS Braket" "Azure Quantum")

    # GPU options
    print_section "GPU Configuration"

    if [ "$gpu_type" = "nvidia" ]; then
        if ask_yes_no "Enable NVIDIA GPU acceleration (requires nvidia-docker)?"; then
            # This will be handled in docker-compose.full.yml
            print_status "SUCCESS" "GPU support will be enabled in docker-compose"
        fi
    elif [ "$gpu_type" = "apple_silicon" ]; then
        print_status "INFO" "Apple Silicon detected - Docker Metal support enabled automatically"
    fi

    # Create .env file
    print_section "Creating .env Configuration"

    create_env_file "$model" "$port" "$backend"

    print_status "SUCCESS" ".env file created"
    print_divider
}

create_env_file() {
    local model=$1
    local port=$2
    local backend=$3

    cat > "$ENV_FILE" << EOF
# ================================================================
# CVGen Configuration - Generated by setup.sh
# ================================================================
# Edit this file to customize your CVGen deployment

# CVGen API Configuration
CVGEN_PORT=$port
CVGEN_HOST=0.0.0.0
CVGEN_LOG_LEVEL=INFO
CVGEN_API_URL=http://cvgen:8000

# Ollama LLM Backend
OLLAMA_MODEL=$model
OLLAMA_HOST=http://ollama:11434

# Qdrant Vector Database
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=cvgen_qpanda3

# Origin Pilot (Quantum Backend)
ORIGIN_PILOT_HOST=localhost
ORIGIN_PILOT_JOB_PORT=5555
ORIGIN_PILOT_TELEMETRY_PORT=5556

# IBM Quantum (optional - set if using IBM backend)
# IBM_QUANTUM_TOKEN=
# IBM_QUANTUM_BACKEND=ibm_brisbane

# AWS Braket (optional - set if using AWS backend)
# AWS_DEFAULT_REGION=
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# CVGEN_BRAKET_S3_BUCKET=

# Azure Quantum (optional - set if using Azure backend)
# AZURE_QUANTUM_RESOURCE_ID=
# AZURE_QUANTUM_LOCATION=eastus

# ================================================================
# Notes:
# 1. Model will be auto-pulled on first startup
# 2. Initialize with: bash scripts/health_check.sh
# 3. Access at: http://localhost:$port
# ================================================================
EOF

    print_status "SUCCESS" "Configuration saved to .env"
}

# ============================================================================
# Service Management Functions
# ============================================================================

start_services() {
    print_header "Starting CVGen Services"

    if ! check_docker_running; then
        print_status "ERROR" "Docker daemon is not running"
        print_status "INFO" "Please start Docker and try again"
        return 1
    fi

    print_section "Pulling and Starting Containers"
    echo "This may take a few minutes on first run..."
    echo ""

    if docker-compose -f "$COMPOSE_FILE" up -d; then
        print_status "SUCCESS" "All containers started"
        return 0
    else
        print_status "ERROR" "Failed to start containers"
        return 1
    fi
}

wait_for_services() {
    print_header "Waiting for Services to Be Ready"

    local cvgen_healthy=false
    local ollama_healthy=false
    local qdrant_healthy=false
    local elapsed=0

    print_section "Checking Service Health"
    echo "Timeout: ${CONTAINER_CHECK_TIMEOUT}s"
    echo ""

    while [ $elapsed -lt $CONTAINER_CHECK_TIMEOUT ]; do
        # Check CVGen
        if ! $cvgen_healthy; then
            if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
                print_status "SUCCESS" "CVGen API is healthy"
                cvgen_healthy=true
            else
                echo -ne "CVGen API... "
            fi
        fi

        # Check Ollama
        if ! $ollama_healthy; then
            if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
                print_status "SUCCESS" "Ollama is healthy"
                ollama_healthy=true
            else
                echo -ne "Ollama... "
            fi
        fi

        # Check Qdrant
        if ! $qdrant_healthy; then
            if curl -sf http://localhost:6333/health > /dev/null 2>&1; then
                print_status "SUCCESS" "Qdrant is healthy"
                qdrant_healthy=true
            else
                echo -ne "Qdrant... "
            fi
        fi

        if $cvgen_healthy && $ollama_healthy && $qdrant_healthy; then
            echo ""
            print_divider
            print_status "SUCCESS" "All services are healthy and ready!"
            return 0
        fi

        sleep 2
        elapsed=$((elapsed + 2))
        echo -ne "\r[${elapsed}s]"
    done

    echo ""
    print_status "WARNING" "Timeout waiting for services"
    print_status "INFO" "Services may still be starting. Check with: docker logs -f cvgen-api"
    return 1
}

# ============================================================================
# Display Information Functions
# ============================================================================

display_next_steps() {
    print_header "Setup Complete!"

    local port
    port=$(grep "CVGEN_PORT" "$ENV_FILE" | cut -d= -f2)

    echo -e "${GREEN}CVGen is now running!${NC}\n"

    echo "Available services:"
    echo "  • ${CYAN}CVGen Web UI:${NC}       http://localhost:${port}"
    echo "  • ${CYAN}API Swagger Docs:${NC}    http://localhost:${port}/docs"
    echo "  • ${CYAN}Ollama:${NC}              http://localhost:11434"
    echo "  • ${CYAN}Qdrant:${NC}              http://localhost:6333"
    echo ""

    echo "Useful commands:"
    echo "  • View logs:         ${CYAN}docker logs -f cvgen-api${NC}"
    echo "  • Stop services:     ${CYAN}docker-compose -f docker-compose.full.yml down${NC}"
    echo "  • Restart services:  ${CYAN}docker-compose -f docker-compose.full.yml restart${NC}"
    echo "  • Health check:      ${CYAN}bash scripts/health_check.sh${NC}"
    echo "  • Pull new model:    ${CYAN}docker exec cvgen-ollama ollama pull mistral${NC}"
    echo ""

    echo "Configuration:"
    echo "  • Settings file:     ${CYAN}$ENV_FILE${NC}"
    echo "  • Compose file:      ${CYAN}$COMPOSE_FILE${NC}"
    echo ""

    echo "Next steps:"
    echo "  1. Visit http://localhost:${port} to access CVGen"
    echo "  2. Try building a quantum circuit with the visual builder"
    echo "  3. Ask the AI agent to generate quantum code"
    echo "  4. Check API docs at http://localhost:${port}/docs"
    echo ""

    print_divider
}

display_troubleshooting() {
    print_header "Troubleshooting"

    echo "If services don't start:"
    echo ""

    echo "  Check Docker is running:"
    echo "    ${CYAN}docker ps${NC}"
    echo ""

    echo "  View container logs:"
    echo "    ${CYAN}docker logs cvgen-api${NC}"
    echo "    ${CYAN}docker logs cvgen-ollama${NC}"
    echo "    ${CYAN}docker logs cvgen-qdrant${NC}"
    echo ""

    echo "  Restart all services:"
    echo "    ${CYAN}docker-compose -f docker-compose.full.yml restart${NC}"
    echo ""

    echo "  Full reset (warning: deletes data):"
    echo "    ${CYAN}docker-compose -f docker-compose.full.yml down -v${NC}"
    echo "    ${CYAN}docker-compose -f docker-compose.full.yml up -d${NC}"
    echo ""

    echo "  Check resource usage:"
    echo "    ${CYAN}docker stats${NC}"
    echo ""

    print_divider
}

# ============================================================================
# Main Setup Flow
# ============================================================================

main() {
    clear

    print_header "CVGen Setup Script"
    echo "Quantum Computing for Every Device - Docker All-in-One Stack"
    echo "Version: Phase 4"
    echo ""

    # System detection
    print_section "System Detection"

    local os
    local ram_gb
    local gpu_type
    local arch

    os=$(detect_os)
    ram_gb=$(detect_ram)
    gpu_type=$(detect_gpu)
    arch=$(detect_architecture)

    print_status "INFO" "Operating System: $os"
    print_status "INFO" "Architecture: $arch"
    print_status "INFO" "Available RAM: ${ram_gb}GB"
    print_status "INFO" "GPU Detected: $gpu_type"
    print_divider

    # Docker validation
    print_section "Docker Verification"

    if ! check_docker_installed; then
        print_status "WARNING" "Docker is not installed"
        case "$os" in
            "linux")
                if ask_yes_no "Install Docker automatically?"; then
                    install_docker_linux
                else
                    print_status "ERROR" "Docker is required to continue"
                    return 1
                fi
                ;;
            "macos")
                install_docker_macos || return 1
                ;;
            "windows")
                install_docker_windows || return 1
                ;;
        esac
    else
        print_status "SUCCESS" "Docker is installed"
        docker_version=$(docker --version)
        print_status "INFO" "$docker_version"
    fi

    if ! check_docker_compose_installed; then
        print_status "ERROR" "Docker Compose is not installed"
        return 1
    else
        print_status "SUCCESS" "Docker Compose is installed"
    fi

    if ! check_docker_running; then
        print_status "ERROR" "Docker daemon is not running"
        print_status "INFO" "Please start Docker and try again"
        return 1
    else
        print_status "SUCCESS" "Docker daemon is running"
    fi

    print_divider

    # GPU setup
    if [ "$gpu_type" = "nvidia" ] && [ "$os" = "linux" ]; then
        if ask_yes_no "Setup NVIDIA GPU acceleration?"; then
            setup_docker_daemon_gpu_nvidia
        fi
    fi

    # Configuration
    configure_environment

    # Start services
    if ! start_services; then
        print_status "ERROR" "Failed to start services"
        display_troubleshooting
        return 1
    fi

    # Wait for health
    if wait_for_services; then
        display_next_steps

        # Try to open browser
        if ask_yes_no "Open CVGen in your browser?"; then
            local port
            port=$(grep "CVGEN_PORT" "$ENV_FILE" | cut -d= -f2)

            case "$os" in
                "linux")
                    xdg-open "http://localhost:${port}" 2>/dev/null || true
                    ;;
                "macos")
                    open "http://localhost:${port}"
                    ;;
                "windows")
                    start "http://localhost:${port}"
                    ;;
            esac
        fi
    else
        display_troubleshooting
    fi
}

# ============================================================================
# Script Entry Point
# ============================================================================

# Change to script directory
cd "$SCRIPT_DIR"

# Run main
main
