#!/usr/bin/env python3
"""
Compiler.py — expanded launcher for modules/files in the repository.

Additions:
 - Invoke a callable inside a module or file:
     module:my_pkg.my_mod:main   (or module:my_pkg.my_mod.main)
     file:tools/script.py:entry
   The callable is invoked with forwarded args (strings). If callable is async it will be awaited.
 - --capture FILE  : capture stdout/stderr to FILE (appends)
 - --log-file FILE : write internal logs to FILE
 - improved env context manager (restores cleanly)
 - more robust verbose/error messages
"""
from __future__ import annotations

import sys
import os
import argparse
import runpy
import importlib
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Callable
from contextlib import contextmanager, redirect_stdout, redirect_stderr

ROOT = Path(__file__).resolve().parent

# Default mapping of friendly commands -> module filenames (module name without .py)
DEFAULT_MAP: Dict[str, str] = {
    "codegen": "codegen",
    "executor": "executor",
    "trizzle": "run_trizzle",
    "veil": "run_veil",
    "run_trizzle": "run_trizzle",
    "run_veil": "run_veil",
}


def discover_runnable() -> Tuple[Dict[str, Path], Dict[str, str]]:
    files: Dict[str, Path] = {}
    modules: Dict[str, str] = {}

    for p in ROOT.glob("*.py"):
        name = p.stem
        if name == Path(__file__).stem:
            continue
        files[name] = p
        modules[name] = name

    for key, mod in DEFAULT_MAP.items():
        modules.setdefault(key, mod)

    return files, modules


@contextmanager
def temp_environ(updates: Dict[str, str]):
    old = os.environ.copy()
    try:
        os.environ.update(updates)
        yield
    finally:
        os.environ.clear()
        os.environ.update(old)


@contextmanager
def maybe_capture(capture_path: Optional[Path]):
    if capture_path is None:
        yield
    else:
        capture_path.parent.mkdir(parents=True, exist_ok=True)
        f = open(capture_path, "a", encoding="utf-8")
        try:
            with redirect_stdout(f), redirect_stderr(f):
                yield
        finally:
            f.close()


def _call_callable(module_name: str, func_name: str, args: List[str], verbose: bool = False) -> int:
    """
    Import module and call callable named func_name. If callable is coroutine function, await it.
    Try calling with *args; if TypeError, try single argument list.
    Returns exit code.
    """
    if verbose:
        logging.info("importing module '%s' to call '%s'", module_name, func_name)
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        logging.exception("failed to import module '%s': %s", module_name, e)
        print(f"Error: cannot import module '{module_name}': {e}", file=sys.stderr)
        return 2

    if not hasattr(mod, func_name):
        logging.error("module '%s' has no attribute '%s'", module_name, func_name)
        print(f"Error: module '{module_name}' has no attribute '{func_name}'", file=sys.stderr)
        return 3

    fn = getattr(mod, func_name)
    try:
        if asyncio.iscoroutinefunction(fn):
            # try calling with single list parameter first, then *args
            try:
                return_code = asyncio.run(fn(*args))
            except TypeError:
                return_code = asyncio.run(fn(args))
            return 0 if return_code is None else int(return_code)
        else:
            try:
                result = fn(*args)
            except TypeError:
                result = fn(args)
            return 0 if result is None else int(result)
    except SystemExit as se:
        return se.code if isinstance(se.code, int) else 0
    except Exception as e:
        logging.exception("error while calling %s.%s: %s", module_name, func_name, e)
        print(f"Exception while calling {module_name}.{func_name}: {e}", file=sys.stderr)
        return 1


def _call_file_callable(file_path: Path, func_name: str, args: List[str], verbose: bool = False) -> int:
    """
    Execute the file as module first (so top-level code runs) then import it by a generated name and call func.
    Uses importlib.machinery.SourceFileLoader to load as module.
    """
    import importlib.machinery
    import importlib.util
    name = f"__launcher_loaded__{abs(hash(str(file_path)))}"
    try:
        loader = importlib.machinery.SourceFileLoader(name, str(file_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)  # type: ignore
    except Exception as e:
        logging.exception("failed to load file '%s' as module: %s", file_path, e)
        print(f"Error loading file '{file_path}': {e}", file=sys.stderr)
        return 2

    if not hasattr(module, func_name):
        logging.error("file module '%s' has no attribute '%s'", file_path, func_name)
        print(f"Error: file '{file_path}' (as module) has no attribute '{func_name}'", file=sys.stderr)
        return 3

    fn = getattr(module, func_name)
    try:
        if asyncio.iscoroutinefunction(fn):
            try:
                return_code = asyncio.run(fn(*args))
            except TypeError:
                return_code = asyncio.run(fn(args))
            return 0 if return_code is None else int(return_code)
        else:
            try:
                result = fn(*args)
            except TypeError:
                result = fn(args)
            return 0 if result is None else int(result)
    except SystemExit as se:
        return se.code if isinstance(se.code, int) else 0
    except Exception as e:
        logging.exception("error while calling %s in file %s: %s", func_name, file_path, e)
        print(f"Exception while calling {func_name} in {file_path}: {e}", file=sys.stderr)
        return 1


def run_module_as_script(module_name: str, argv: List[str], env_updates: Dict[str, str],
                         verbose: bool = False, dry_run: bool = False,
                         capture: Optional[Path] = None, callable_name: Optional[str] = None) -> int:
    if dry_run:
        print(f"[DRY RUN] module: {module_name} argv={argv} callable={callable_name} env={env_updates}")
        return 0
    if verbose:
        logging.info("running module '%s' (callable=%s) argv=%s env=%s", module_name, callable_name, argv, env_updates)

    with temp_environ(env_updates):
        with maybe_capture(capture):
            # If a callable is requested, import + call it
            if callable_name:
                return _call_callable(module_name, callable_name, argv, verbose=verbose)
            # else execute as module (like -m)
            try:
                runpy.run_module(module_name, run_name="__main__", alter_sys=True)
                return 0
            except ModuleNotFoundError:
                logging.exception("module not found: %s", module_name)
                print(f"Module '{module_name}' not found.", file=sys.stderr)
                return 2
            except SystemExit as se:
                return se.code if isinstance(se.code, int) else 0
            except Exception as e:
                logging.exception("error running module %s: %s", module_name, e)
                print(f"Error while running module '{module_name}': {e}", file=sys.stderr)
                return 1


def run_file_as_script(file_path: Path, argv: List[str], env_updates: Dict[str, str],
                       verbose: bool = False, dry_run: bool = False,
                       capture: Optional[Path] = None, callable_name: Optional[str] = None) -> int:
    if dry_run:
        print(f"[DRY RUN] file: {file_path} argv={argv} callable={callable_name} env={env_updates}")
        return 0
    if verbose:
        logging.info("running file '%s' (callable=%s) argv=%s env=%s", file_path, callable_name, argv, env_updates)

    if not file_path.exists():
        logging.error("file not found: %s", file_path)
        print(f"File '{file_path}' does not exist.", file=sys.stderr)
        return 2

    with temp_environ(env_updates):
        with maybe_capture(capture):
            if callable_name:
                return _call_file_callable(file_path, callable_name, argv, verbose=verbose)
            try:
                runpy.run_path(str(file_path), run_name="__main__")
                return 0
            except SystemExit as se:
                return se.code if isinstance(se.code, int) else 0
            except Exception as e:
                logging.exception("error running file %s: %s", file_path, e)
                print(f"Error while running file '{file_path}': {e}", file=sys.stderr)
                return 1


def print_discovered(files: Dict[str, Path], modules: Dict[str, str]) -> None:
    print("Discovered python files:")
    for name, p in sorted(files.items()):
        print(f"  {name} -> {p.name}")
    print("\nExposed module commands:")
    for cmd, mod in sorted(modules.items()):
        print(f"  {cmd} -> module '{mod}'")


def parse_env_list(env_list: List[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in env_list or []:
        if "=" in item:
            k, v = item.split("=", 1)
            result[k] = v
        else:
            result[item] = ""
    return result


def _parse_module_or_file_with_callable(raw: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Parse strings like:
      module:pkg.mod:callable  -> ("module", "pkg.mod", "callable")
      module:pkg.mod.callable -> ("module", "pkg.mod", "callable")
      file:path/to/script.py:entry -> ("file", "path/to/script.py", "entry")
      plain -> ("", "plain", None)
    """
    if raw.startswith("module:"):
        tail = raw.split(":", 1)[1]
        if ":" in tail:
            mod, fn = tail.split(":", 1)
            return "module", mod, fn
        if "." in tail:
            # treat last dotted segment as callable if present as suffix
            parts = tail.rsplit(".", 1)
            if len(parts) == 2:
                return "module", parts[0], parts[1]
        return "module", tail, None
    if raw.startswith("file:"):
        tail = raw.split(":", 1)[1]
        if ":" in tail:
            path, fn = tail.split(":", 1)
            return "file", path, fn
        if ":" in raw:
            # fallback
            return "file", tail, None
        return "file", tail, None
    return "", raw, None


def run_one_command(raw_cmd: str, args_forward: List[str], files: Dict[str, Path],
                    verbose: bool, dry_run: bool, env_updates: Dict[str, str],
                    capture: Optional[Path]) -> int:
    """
    Handle a single command string (supports prefixes module:/file: and friendly names).
    """
    # Trim
    cmd = raw_cmd.strip()
    if not cmd:
        return 0

    prefix, core, callable_name = _parse_module_or_file_with_callable(cmd)

    # If explicit module prefix
    if prefix == "module":
        return run_module_as_script(core, args_forward, env_updates, verbose=verbose, dry_run=dry_run, capture=capture, callable_name=callable_name)

    # If explicit file prefix
    if prefix == "file":
        return run_file_as_script(Path(core), args_forward, env_updates, verbose=verbose, dry_run=dry_run, capture=capture, callable_name=callable_name)

    # Friendly mapping
    if core in DEFAULT_MAP:
        mod = DEFAULT_MAP[core]
        # allow callable specified separately with syntax core:callable via comma? user can use module:...
        return run_module_as_script(mod, args_forward, env_updates, verbose=verbose, dry_run=dry_run, capture=capture, callable_name=callable_name)

    # Exact discovered file
    if core in files:
        return run_file_as_script(files[core], args_forward, env_updates, verbose=verbose, dry_run=dry_run, capture=capture, callable_name=callable_name)

    # Path-like
    potential = Path(core)
    if potential.suffix == ".py" or potential.exists():
        return run_file_as_script(potential, args_forward, env_updates, verbose=verbose, dry_run=dry_run, capture=capture, callable_name=callable_name)

    # Fallback: try as module name (dotted)
    return run_module_as_script(core, args_forward, env_updates, verbose=verbose, dry_run=dry_run, capture=capture, callable_name=callable_name)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="Compiler.py",
        description="Launcher for repo modules/files (codegen, executor, run_trizzle, run_veil, ...)"
    )
    parser.add_argument("command", nargs="?", help="command to run (module name, friendly name, file path or comma-separated list). Use --list to discover.")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="arguments forwarded to the chosen module/file")
    parser.add_argument("--list", action="store_true", help="discover and list runnable python modules/files in repository root")
    parser.add_argument("--module", action="store_true", help="treat command explicitly as a module name")
    parser.add_argument("--file", action="store_true", help="treat command explicitly as a filesystem path to a python file")
    parser.add_argument("--env", action="append", default=[], help="inject environment variable(s) for run: KEY=VAL (repeatable)")
    parser.add_argument("--verbose", "-v", action="store_true", help="verbose output")
    parser.add_argument("--dry-run", action="store_true", help="print actions without executing")
    parser.add_argument("--capture", help="capture stdout/stderr to FILE (append)", default=None)
    parser.add_argument("--log-file", help="write internal launcher logs to FILE", default=None)
    args = parser.parse_args(argv)

    # configure logging
    if args.log_file:
        logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, filename=args.log_file, filemode="a", format="%(asctime)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    files, modules = discover_runnable()

    if args.list:
        print_discovered(files, modules)
        return 0

    if not args.command:
        parser.print_help()
        return 0

    env_updates = parse_env_list(args.env)
    capture_path = Path(args.capture) if args.capture else None

    # Support comma-separated multi-commands: "cmd1,cmd2"
    raw_cmds = [c.strip() for c in args.command.split(",") if c.strip()]

    exit_code = 0
    for raw_cmd in raw_cmds:
        code = run_one_command(raw_cmd, args.args or [], files, verbose=args.verbose, dry_run=args.dry_run, env_updates=env_updates, capture=capture_path)
        if args.verbose:
            logging.info("RESULT: '%s' → exit %s", raw_cmd, code)
        if code != 0 and exit_code == 0:
            exit_code = code  # report first non-zero
        # continue through commands even if one fails

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

