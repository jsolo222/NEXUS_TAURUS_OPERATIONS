"""
CLI Entry Point

Command-line interface for the NTO Ground Station server.
"""

import argparse
import os
import uvicorn


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="nto-server",
        description="NEXUS TAURUS OPERATIONS Ground Station Server"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Start the server")
    run_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to listen on (default: 8765)"
    )
    run_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    run_parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)"
    )
    run_parser.add_argument(
        "--simulate",
        action="store_true",
        help="Start telemetry simulator (no hardware needed)"
    )

    args = parser.parse_args()

    if args.command == "run":
        sim_status = "ENABLED (no hardware needed)" if args.simulate else "disabled"
        print(f"""
╔═══════════════════════════════════════════════════════════════╗
║           NEXUS TAURUS OPERATIONS - Ground Station            ║
╠═══════════════════════════════════════════════════════════════╣
║  Server starting on http://{args.host}:{args.port}                      ║
║  Simulator: {sim_status:<49}║
║                                                               ║
║  Endpoints:                                                   ║
║    REST API:     http://{args.host}:{args.port}/api                     ║
║    Vehicle WS:   ws://{args.host}:{args.port}/ws/vehicle/{{id}}          ║
║    Dashboard WS: ws://{args.host}:{args.port}/ws/dashboard              ║
║    API Docs:     http://{args.host}:{args.port}/docs                    ║
╚═══════════════════════════════════════════════════════════════╝
        """)

        # Set environment variable for simulator
        if args.simulate:
            os.environ["NTO_SIMULATE"] = "1"

        uvicorn.run(
            "nto_server.app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
