"""Chronos 1.0 desktop entry point. Application state is always per installation."""
import argparse
import ctypes
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import multiprocessing
import os
from pathlib import Path
import socket
import sys
import threading
import time
import webbrowser

BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(BUNDLE / "backend"), str(BUNDLE)]


def isolated_environment():
    for key in list(os.environ):
        if key.upper().startswith("CHRONOS_") or key.upper() in {"DATABASE_URL", "JWT_SECRET"}:
            os.environ.pop(key, None)


def start_workers(application, settings, folder, stop):
    from app.services.optimization_worker import work_once as optimize
    from app.services.automation_worker import work_once as automate
    def consume(kind):
        while not stop.is_set():
            try:
                factory = application.state.session_factory
                if kind == "optimization":
                    optimize(factory, settings, folder / "solver", stop_event=stop)
                else:
                    automate(factory, settings, scheduler=False)
            except Exception as error:
                logging.getLogger("chronos.desktop").error("Worker %s: %s", kind, type(error).__name__)
            stop.wait(.8)
    threads = [threading.Thread(target=consume, args=(kind,), daemon=True) for kind in ("optimization", "events")]
    for thread in threads:
        thread.start()
    return threads


def main():
    multiprocessing.freeze_support()
    if len(sys.argv) == 4 and sys.argv[1] == "--chronos-solver":
        isolated_environment()
        from desktop.solver import solve_files
        solve_files(sys.argv[2], sys.argv[3])
        return 0
    parser = argparse.ArgumentParser(description="Chronos 1.0 — demonstração para Windows")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    isolated_environment()
    from desktop.runtime import data_folder, prepare
    folder = data_folder(args.data_dir)
    if args.self_test:
        if args.data_dir is None or any(folder.iterdir()):
            raise ValueError("O autoteste exige uma pasta nova, vazia e explicitamente indicada.")
        (folder / ".chronos-self-test").touch()
    mutex = None
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.restype = ctypes.c_void_p
        mutex = kernel.CreateMutexW(None, False, "Local\\ChronosDemo-" + hashlib.sha256(str(folder).lower().encode()).hexdigest()[:24])
        if not mutex:
            raise OSError("Não foi possível proteger a pasta de dados.")
        if ctypes.get_last_error() == 183:
            session = json.loads((folder / "session.json").read_text(encoding="utf-8"))
            from urllib.parse import urlsplit
            address = urlsplit(session["url"])
            if address.scheme == "http" and address.hostname == "127.0.0.1" and address.port:
                webbrowser.open(session["url"])
            kernel.CloseHandle(ctypes.c_void_p(mutex))
            return 0
    handler = RotatingFileHandler(folder / "chronos.log", maxBytes=2_000_000, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    stop = threading.Event()
    server = application = api_thread = None
    workers = []
    trace_stream = None
    try:
        if args.self_test:
            import faulthandler
            trace_stream = (folder / "startup-trace.log").open("w")
            faulthandler.dump_traceback_later(45, file=trace_stream)
        try:
            listener.bind(("127.0.0.1", 5189))
        except OSError:
            listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        url = "http://127.0.0.1:" + str(listener.getsockname()[1])
        settings = prepare(folder, url)
        logging.getLogger("chronos.desktop").info("Fresh local database ready")
        from desktop.webapp import create_desktop_app
        application = create_desktop_app(settings, BUNDLE)
        logging.getLogger("chronos.desktop").info("Application and frontend ready")
        import uvicorn
        server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", log_config=None,
            access_log=False, loop="asyncio", http="h11", ws="none"))
        server_errors = []
        def serve():
            try:
                server.run(sockets=[listener])
            except BaseException as error:
                server_errors.append(error)
                logging.getLogger("chronos.desktop").exception("Local server startup failed")
        api_thread = threading.Thread(target=serve, daemon=True)
        api_thread.start()
        logging.getLogger("chronos.desktop").info("Local server thread started")
        deadline = time.monotonic() + 120
        while not server.started:
            if not api_thread.is_alive() or time.monotonic() >= deadline:
                detail = type(server_errors[0]).__name__ if server_errors else "timeout" if api_thread.is_alive() else "server stopped"
                raise RuntimeError("A inicialização local não foi concluída: " + detail)
            time.sleep(.1)
        workers = start_workers(application, settings, folder, stop)
        if args.self_test:
            faulthandler.cancel_dump_traceback_later()
        (folder / "session.json").write_text(json.dumps({"url": url, "pid": os.getpid()}), encoding="utf-8")
        if args.self_test:
            from desktop.selftest import run
            run(url, folder, BUNDLE, application.state.session_factory)
        else:
            from desktop.window import ControlWindow
            window = ControlWindow(url, folder, BUNDLE, application.state.session_factory)
            if not args.no_browser:
                webbrowser.open(url + "/login")
            window.run()
        return 0
    except Exception as error:
        logging.getLogger("chronos.desktop").error("Startup: %s", type(error).__name__)
        if args.self_test:
            (folder / "self-test-error.json").write_text(json.dumps({"type": type(error).__name__, "message": str(error)}), encoding="utf-8")
        elif os.name == "nt":
            ctypes.windll.user32.MessageBoxW(None, "Não foi possível abrir o Chronos. Consulte o log em:\n" + str(folder), "Chronos 1.0", 16)
        return 1
    finally:
        if trace_stream:
            faulthandler.cancel_dump_traceback_later()
            trace_stream.close()
        stop.set()
        if server:
            server.should_exit = True
        for thread in workers:
            thread.join(timeout=12)
        if api_thread:
            api_thread.join(timeout=10)
        if application:
            application.state.engine.dispose()
        listener.close()
        if mutex:
            kernel.CloseHandle(ctypes.c_void_p(mutex))


if __name__ == "__main__":
    raise SystemExit(main())
