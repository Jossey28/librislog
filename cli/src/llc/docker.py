import subprocess
from enum import Enum
from pathlib import Path

import typer
from llc._interactive import console

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEV_COMPOSE = _PROJECT_ROOT / "docker-compose.dev.yml"
_PROD_COMPOSE = _PROJECT_ROOT / "docker-compose.yml"
_E2E_COMPOSE = _PROJECT_ROOT / "docker-compose.e2e.yml"


class ComposeEnv(str, Enum):
    dev = "dev"
    prod = "prod"
    e2e = "e2e"


def _resolve_compose(env: ComposeEnv) -> Path:
    return {"dev": _DEV_COMPOSE, "prod": _PROD_COMPOSE, "e2e": _E2E_COMPOSE}[env.value]


def _compose_cmd(compose_file: Path, args: list[str]) -> list[str]:
    return ["docker", "compose", "-f", str(compose_file), *args]


def cmd_up(service: str | None = None, *, env: ComposeEnv = ComposeEnv.dev) -> None:
    cmd = ["up", "--build", "-d"]
    if service:
        cmd.append(service)
    label = f" [cyan]{service}[/cyan]" if service else ""
    console.print(f"[bold]Building and starting{label}...[/bold]")
    code = subprocess.call(_compose_cmd(_resolve_compose(env), cmd))
    if code != 0:
        raise typer.Exit(code=code)


def cmd_down(*, env: ComposeEnv = ComposeEnv.dev) -> None:
    console.print("[bold]Stopping containers...[/bold]")
    code = subprocess.call(_compose_cmd(_resolve_compose(env), ["down"]))
    if code != 0:
        raise typer.Exit(code=code)


def cmd_logs(follow: bool = False, service: str | None = None, *, env: ComposeEnv = ComposeEnv.dev) -> None:
    cmd = ["logs"]
    if follow:
        cmd.append("-f")
    if service:
        cmd.append(service)
    code = subprocess.call(_compose_cmd(_resolve_compose(env), cmd))
    if code != 0:
        raise typer.Exit(code=code)


def cmd_status(*, env: ComposeEnv = ComposeEnv.dev) -> None:
    code = subprocess.call(_compose_cmd(_resolve_compose(env), ["ps"]))
    if code != 0:
        raise typer.Exit(code=code)


def cmd_shell(service: str) -> None:
    console.print(f"[bold]Opening shell in [cyan]{service}[/cyan]...[/bold]")
    code = subprocess.call(_compose_cmd(_DEV_COMPOSE, ["exec", service, "sh"]))
    if code != 0:
        raise typer.Exit(code=code)


def cmd_restart(service: str, *, env: ComposeEnv = ComposeEnv.dev) -> None:
    console.print(f"[bold]Restarting [cyan]{service}[/cyan]...[/bold]")
    code = subprocess.call(_compose_cmd(_resolve_compose(env), ["restart", service]))
    if code != 0:
        raise typer.Exit(code=code)
