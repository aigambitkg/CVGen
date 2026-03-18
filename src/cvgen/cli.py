"""Command-line interface for CVGen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cvgen import __version__


class ColorCode:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

    @staticmethod
    def supports_color() -> bool:
        """Check if terminal supports color."""
        if sys.platform == "win32":
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32
                mode = ctypes.c_ulong()
                if kernel32.GetConsoleMode(kernel32.GetStdHandle(-11), ctypes.byref(mode)):
                    mode.value |= 0x0004
                    return kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), mode)
            except Exception:
                return False
        return True


def _print_colored(text: str, color: str) -> None:
    """Print colored text if terminal supports it."""
    if ColorCode.supports_color():
        print(f"{color}{text}{ColorCode.RESET}")
    else:
        print(text)


def _print_success(msg: str) -> None:
    """Print success message in green."""
    _print_colored(f"✓ {msg}", ColorCode.GREEN)


def _print_error(msg: str) -> None:
    """Print error message in red."""
    _print_colored(f"✗ {msg}", ColorCode.RED)


def _print_info(msg: str) -> None:
    """Print info message in blue."""
    _print_colored(f"ℹ {msg}", ColorCode.BLUE)


def _print_warning(msg: str) -> None:
    """Print warning message in yellow."""
    _print_colored(f"⚠ {msg}", ColorCode.YELLOW)


def cmd_version(args: argparse.Namespace) -> int:
    """Print CVGen version."""
    print(f"CVGen version {__version__}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new CVGen configuration file."""
    config_path = Path(".cvgen.yaml")

    if config_path.exists() and not args.force:
        _print_error(f"Config file already exists at {config_path}")
        return 1

    try:
        _print_info("Initializing CVGen configuration...")

        config_content = """cvgen:
  version: "1.0.0"
  log_level: INFO

server:
  host: "0.0.0.0"
  port: 8000

backends:
  simulator:
    enabled: true
    max_qubits: 20
  origin_pilot:
    enabled: false
    host: localhost
    job_port: 5555
    telemetry_port: 5556
  ibm_quantum:
    enabled: false
    token: ""
    backend: "ibm_brisbane"
  aws_braket:
    enabled: false
  azure_quantum:
    enabled: false

llm:
  provider: ollama
  url: "http://localhost:11434"
  model: "qwen2.5:7b"

rag:
  enabled: true
  qdrant_url: "http://localhost:6333"
  collection: "cvgen_qpanda3"
"""

        config_path.write_text(config_content)
        _print_success(f"Configuration file created at {config_path}")
        return 0

    except Exception as e:
        _print_error(f"Failed to create configuration: {e}")
        return 1


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the CVGen API server."""
    try:
        import uvicorn
    except ImportError:
        _print_error("API extra not installed. Run: pip install cvgen[api]")
        return 1

    try:
        from cvgen.web import create_app

        app = create_app()

        _print_info(f"Starting CVGen API server on {args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
        return 0

    except Exception as e:
        _print_error(f"Failed to start server: {e}")
        return 1


def cmd_health(args: argparse.Namespace) -> int:
    """Check health of all configured services."""
    try:
        from cvgen.config import CloudConfig  # noqa: F401
    except ImportError:
        _print_error("Failed to import CVGen modules")
        return 1

    _print_info("Checking CVGen service health...")

    health_status = {}

    try:
        import httpx

        client = httpx.Client(timeout=5.0)

        if args.check_api:
            try:
                resp = client.get(f"http://{args.api_host}:{args.api_port}/api/v1/health")
                health_status["API Server"] = resp.status_code == 200
            except Exception as e:
                _print_warning(f"API Server: {e}")
                health_status["API Server"] = False

        if args.check_qdrant:
            try:
                resp = client.get(f"{args.qdrant_url}/health")
                health_status["Qdrant"] = resp.status_code == 200
            except Exception as e:
                _print_warning(f"Qdrant: {e}")
                health_status["Qdrant"] = False

        if args.check_ollama:
            try:
                resp = client.get(f"{args.ollama_url}/api/tags")
                health_status["Ollama"] = resp.status_code == 200
            except Exception as e:
                _print_warning(f"Ollama: {e}")
                health_status["Ollama"] = False

        client.close()

    except ImportError:
        _print_warning("httpx not installed. Install with: pip install httpx")
        return 1

    all_healthy = True
    for service, is_healthy in health_status.items():
        if is_healthy:
            _print_success(f"{service} is healthy")
        else:
            _print_error(f"{service} is unhealthy or unreachable")
            all_healthy = False

    return 0 if all_healthy else 1


def cmd_run(args: argparse.Namespace) -> int:
    """Execute a quantum circuit from a Python file."""
    circuit_path = Path(args.circuit)

    if not circuit_path.exists():
        _print_error(f"Circuit file not found: {circuit_path}")
        return 1

    if not circuit_path.suffix == ".py":
        _print_error("Circuit file must be a Python file (.py)")
        return 1

    try:
        _print_info(f"Executing circuit from {circuit_path}")

        import importlib.util

        spec = importlib.util.spec_from_file_location("circuit_module", circuit_path)
        if spec is None or spec.loader is None:
            _print_error("Failed to load circuit module")
            return 1

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "circuit"):
            _print_warning("No 'circuit' variable found in module")
            return 1

        circuit = module.circuit

        from cvgen.backends.simulator import StateVectorSimulator

        simulator = StateVectorSimulator(max_qubits=20)
        result = simulator.run(circuit, shots=1000)

        _print_success("Execution completed successfully")
        print(f"\nResults: {result}")

        return 0

    except Exception as e:
        _print_error(f"Failed to execute circuit: {e}")
        return 1


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="cvgen",
        description="CVGen - Quantum Computing for Every Device",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    version_parser = subparsers.add_parser("version", help="Show version")
    version_parser.set_defaults(func=cmd_version)

    init_parser = subparsers.add_parser("init", help="Initialize configuration")
    init_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing configuration",
    )
    init_parser.set_defaults(func=cmd_init)

    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Server host (default: 0.0.0.0)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)",
    )
    serve_parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug"],
        help="Log level (default: info)",
    )
    serve_parser.set_defaults(func=cmd_serve)

    health_parser = subparsers.add_parser("health", help="Check service health")
    health_parser.add_argument(
        "--api",
        action="store_true",
        default=True,
        help="Check API server health",
    )
    health_parser.add_argument(
        "--api-host",
        default="localhost",
        help="API server host",
    )
    health_parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="API server port",
    )
    health_parser.add_argument(
        "--qdrant",
        action="store_true",
        default=False,
        dest="check_qdrant",
        help="Check Qdrant health",
    )
    health_parser.add_argument(
        "--qdrant-url",
        default="http://localhost:6333",
        help="Qdrant URL",
    )
    health_parser.add_argument(
        "--ollama",
        action="store_true",
        default=False,
        dest="check_ollama",
        help="Check Ollama health",
    )
    health_parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama URL",
    )
    health_parser.set_defaults(func=cmd_health)

    run_parser = subparsers.add_parser("run", help="Execute a quantum circuit")
    run_parser.add_argument(
        "circuit",
        help="Path to circuit Python file",
    )
    run_parser.add_argument(
        "--shots",
        type=int,
        default=1000,
        help="Number of measurement shots",
    )
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    try:
        return args.func(args)
    except KeyboardInterrupt:
        _print_warning("\nInterrupted by user")
        return 130
    except Exception as e:
        _print_error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
