"""
The Env class

Written with help from GPT-5
"""
import os
import tempfile
import cloudpickle as cp
import execnet
import sciris as sc

__all__ = ['Env']


class Env:
    """Persistent child interpreter in a chosen venv, with
    automatic dump/load for all values using cloudpickle + tmp files.
    """
    def __init__(self, python_exe, verbose=True):
        """Launch the child interpreter."""
        code = r"""
            import importlib, os, tempfile
            import cloudpickle as cp

            ns = {}

            def _dump(val):
                fd, path = tempfile.mkstemp(prefix="subenv_session_", suffix=".pkl")
                os.close(fd)
                with open(path, "wb") as f:
                    cp.dump(val, f)
                return path

            def _load(path):
                with open(path, "rb") as f:
                    val = cp.load(f)
                try:
                    os.unlink(path)
                except Exception:
                    pass
                return val

            def _import_by_path(path):
                mod, attr = path.split(":", 1)
                m = importlib.import_module(mod)
                return getattr(m, attr)

            channel.send("ready")

            for kind, payload in channel:
                try:
                    if kind == "exec":
                        code = payload
                        exec(code, ns, ns)
                        channel.send(("ok", None))

                    elif kind == "eval":
                        expr = payload
                        val = eval(expr, ns, ns)
                        channel.send(("ok", _dump(val)))

                    elif kind == "call":
                        target, args_path, kwargs_path = payload
                        fn = _import_by_path(target)
                        args = _load(args_path)
                        kwargs = _load(kwargs_path)
                        val = fn(*args, **kwargs)
                        channel.send(("ok", _dump(val)))

                    elif kind == "get":
                        name = payload
                        channel.send(("ok", _dump(ns[name])))

                    elif kind == "set":
                        name, value_path = payload
                        ns[name] = _load(value_path)
                        channel.send(("ok", None))

                    elif kind == "quit":
                        channel.send(("ok", None))
                        break

                    else:
                        channel.send(("err", f"unknown message type: {kind!r}"))

                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    channel.send(("err", f"{e.__class__.__name__}: {e}\n{tb}"))
        """
        T = sc.timer()
        self.verbose = verbose
        if self.verbose: print(f'Starting {python_exe} ... ', end='')
        self.gw = execnet.makegateway(f"popen//python={python_exe}")
        self.ch = self.gw.remote_exec(code)
        ready = self.ch.receive()
        if ready != "ready":
            raise RuntimeError("Failed to start child interpreter")
        if self.verbose: print(f'{T.total:0.1f} s')
        return

    def _recv_ok(self):
        status, payload = self.ch.receive()
        if status == "ok":
            return payload
        raise RuntimeError(payload)

    def _dump_local(self, obj):
        fd, path = tempfile.mkstemp(prefix="subenv_session_parent_", suffix=".pkl")
        os.close(fd)
        with open(path, "wb") as f:
            cp.dump(obj, f)
        return path

    def _load_local(self, path):
        with open(path, "rb") as f:
            val = cp.load(f)
        try:
            os.unlink(path)
        except Exception:
            pass
        return val

    # Public API -------------------------------------------------------------

    def exec(self, code, verbose=False):
        """Execute statements in the child (no return value)."""
        T = sc.timer()
        if self.verbose: print(code)
        self.ch.send(("exec", code))
        self._recv_ok()
        if self.verbose: print(f'✓ {T.total:0.1f} s')
        return

    def eval(self, expr):
        """Evaluate an expression in the child and return the value."""
        self.ch.send(("eval", expr))
        path = self._recv_ok()
        return self._load_local(path)

    def call(self, target, *args, **kwargs):
        """Call a function by 'pkg.mod:func' in the child and return the value."""
        apath = self._dump_local(args)
        kpath = self._dump_local(kwargs)
        try:
            self.ch.send(("call", (target, apath, kpath)))
            path = self._recv_ok()
        finally:
            try:
                os.unlink(apath)
            except Exception:
                pass
            try:
                os.unlink(kpath)
            except Exception:
                pass
        return self._load_local(path)

    def get(self, name):
        """Fetch a variable from the child's namespace and return it."""
        self.ch.send(("get", name))
        path = self._recv_ok()
        return self._load_local(path)

    def set(self, name, value):
        """Set a variable in the child's namespace to 'value'."""
        vpath = self._dump_local(value)
        try:
            self.ch.send(("set", (name, vpath)))
            self._recv_ok()
        finally:
            try:
                os.unlink(vpath)
            except Exception:
                pass

    def close(self):
        """Shut down the child interpreter."""
        try:
            self.ch.send(("quit", None))
            self._recv_ok()
        finally:
            self.gw.exit()