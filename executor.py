import os
import shutil
import shlex
import psutil
import datetime
from typing import Tuple, List


class CommandExecutor:

    def __init__(self):
        pass

    def run(self, raw_cmd: str, cwd: str = None) -> Tuple[str, str, str, int]:
        if cwd is None:
            cwd = "/tmp"
            os.makedirs(cwd, exist_ok=True)

        raw_cmd = raw_cmd.strip()
        if not raw_cmd:
            return ("", "", cwd, 0)

        # simple split while respecting quotes
        try:
            parts = shlex.split(raw_cmd)
        except ValueError as e:
            return ("", f"parse error: {e}", cwd, 2)

        cmd = parts[0]
        args = parts[1:]

        try:
            if cmd == "pwd":
                return (cwd + "\n", "", cwd, 0)

            if cmd == "ls":
                return self._ls(args, cwd)

            if cmd == "cd":
                return self._cd(args, cwd)

            if cmd == "mkdir":
                return self._mkdir(args, cwd)

            if cmd == "rm":
                return self._rm(args, cwd)

            if cmd == "rmdir":
                return self._rmdir(args, cwd)

            if cmd == "cat":
                return self._cat(args, cwd)

            if cmd == "touch":
                return self._touch(args, cwd)

            if cmd == "mv":
                return self._mv(args, cwd)

            if cmd == "cp":
                return self._cp(args, cwd)

            if cmd == "echo":
                return self._echo(args, cwd)

            if cmd == "cpu":
                return self._cpu()

            if cmd == "mem":
                return self._mem()

            if cmd == "ps":
                return self._ps(args)

            if cmd == "whoami":
                return (os.getenv("USER", "user") + "\n", "", cwd, 0)

            if cmd == "date":
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return (now + "\n", "", cwd, 0)

            if cmd == "uptime":
                uptime = psutil.boot_time()
                now = datetime.datetime.now().timestamp()
                delta = int(now - uptime)
                hrs, rem = divmod(delta, 3600)
                mins, secs = divmod(rem, 60)
                return (f"up {hrs}h {mins}m {secs}s\n", "", cwd, 0)

            if cmd == "head":
                return self._head(args, cwd)

            if cmd == "tail":
                return self._tail(args, cwd)

            if cmd == "clear":
                # Special marker for frontend to clear screen
                return ("__CLEAR__", "", cwd, 0)

            # help
            if cmd in ("help", "--help", "-h"):
                return (self._help_text(), "", cwd, 0)

            return ("", f"Command not found: {cmd}\n", cwd, 127)
        except Exception as e:
            return ("", f"Error: {e}\n", cwd, 1)

    # Implementations

    def _path_resolve(self, path: str, cwd: str) -> str:
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(cwd, path))

    def _ls(self, args: List[str], cwd: str):
        target = cwd
        long_format = False
        if args:
            if args[0] == "-l":
                long_format = True
                if len(args) > 1:
                    target = self._path_resolve(args[1], cwd)
            else:
                target = self._path_resolve(args[0], cwd)

        if not os.path.exists(target):
            return ("", f"ls: cannot access '{target}': No such file or directory\n", cwd, 2)

        if os.path.isfile(target):
            return (os.path.basename(target) + "\n", "", cwd, 0)

        entries = sorted(os.listdir(target))
        if long_format:
            lines = []
            for e in entries:
                p = os.path.join(target, e)
                size = os.path.getsize(p)
                lines.append(f"{size:8d} {e}")
            return ("\n".join(lines) + ("\n" if lines else ""), "", cwd, 0)
        else:
            return ("  ".join(entries) + ("\n" if entries else "\n"), "", cwd, 0)

    def _cd(self, args: List[str], cwd: str):
        if not args:
            new = os.path.expanduser("~")
        else:
            new = self._path_resolve(args[0], cwd)

        if not os.path.exists(new):
            return ("", f"cd: {args[0]}: No such file or directory\n", cwd, 1)
        if not os.path.isdir(new):
            return ("", f"cd: {args[0]}: Not a directory\n", cwd, 1)
        return ("", "", new, 0)

    def _mkdir(self, args: List[str], cwd: str):
        if not args:
            return ("", "mkdir: missing operand\n", cwd, 2)
        for a in args:
            p = self._path_resolve(a, cwd)
            try:
                os.makedirs(p, exist_ok=False)
            except FileExistsError:
                return ("", f"mkdir: cannot create directory '{a}': File exists\n", cwd, 1)
        return ("", "", cwd, 0)

    def _rm(self, args: List[str], cwd: str):
        if not args:
            return ("", "rm: missing operand\n", cwd, 2)

        recursive = False
        paths = []
        for a in args:
            if a in ("-r", "-rf", "-fr"):
                recursive = True
            else:
                paths.append(a)

        if not paths:
            return ("", "rm: missing path\n", cwd, 2)

        for p in paths:
            rp = self._path_resolve(p, cwd)
            if not os.path.exists(rp):
                return ("", f"rm: cannot remove '{p}': No such file or directory\n", cwd, 1)
            if os.path.isdir(rp) and not recursive:
                return ("", f"rm: cannot remove '{p}': Is a directory\n", cwd, 1)
            if os.path.isdir(rp):
                shutil.rmtree(rp)
            else:
                os.remove(rp)
        return ("", "", cwd, 0)

    def _rmdir(self, args: List[str], cwd: str):
        if not args:
            return ("", "rmdir: missing operand\n", cwd, 2)
        for a in args:
            path = self._path_resolve(a, cwd)
            if not os.path.exists(path):
                return ("", f"rmdir: failed to remove '{a}': No such file or directory\n", cwd, 1)
            if not os.path.isdir(path):
                return ("", f"rmdir: failed to remove '{a}': Not a directory\n", cwd, 1)
            try:
                os.rmdir(path) 
            except OSError:
                return ("", f"rmdir: failed to remove '{a}': Directory not empty\n", cwd, 1)
        return ("", "", cwd, 0)

    def _echo(self, args: List[str], cwd: str):
        if ">" in args:
            try:
                idx = args.index(">")
                text = " ".join(args[:idx])
                filepath = self._path_resolve(args[idx + 1], cwd)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(text + "\n")
                return ("", "", cwd, 0)
            except Exception as e:
                return ("", f"echo: redirection error: {e}\n", cwd, 1)

        if ">>" in args:
            try:
                idx = args.index(">>")
                text = " ".join(args[:idx])
                filepath = self._path_resolve(args[idx + 1], cwd)
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write(text + "\n")
                return ("", "", cwd, 0)
            except Exception as e:
                return ("", f"echo: redirection error: {e}\n", cwd, 1)

        return (" ".join(args) + "\n", "", cwd, 0)

    def _cat(self, args: List[str], cwd: str):
        if not args:
            return ("", "cat: missing file operand\n", cwd, 2)
        out_lines = []
        for a in args:
            p = self._path_resolve(a, cwd)
            if not os.path.exists(p):
                return ("", f"cat: {a}: No such file or directory\n", cwd, 1)
            if os.path.isdir(p):
                return ("", f"cat: {a}: Is a directory\n", cwd, 1)
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                out_lines.append(f.read())
        return ("\n".join(out_lines), "", cwd, 0)

    def _head(self, args: List[str], cwd: str):
        if not args:
            return ("", "head: missing file operand\n", cwd, 2)
        path = self._path_resolve(args[0], cwd)
        if not os.path.exists(path):
            return ("", f"head: {args[0]}: No such file or directory\n", cwd, 1)
        if os.path.isdir(path):
            return ("", f"head: {args[0]}: Is a directory\n", cwd, 1)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[:10]
        return ("".join(lines), "", cwd, 0)

    def _tail(self, args: List[str], cwd: str):
        if not args:
            return ("", "tail: missing file operand\n", cwd, 2)
        path = self._path_resolve(args[0], cwd)
        if not os.path.exists(path):
            return ("", f"tail: {args[0]}: No such file or directory\n", cwd, 1)
        if os.path.isdir(path):
            return ("", f"tail: {args[0]}: Is a directory\n", cwd, 1)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-10:]
        return ("".join(lines), "", cwd, 0)

    def _touch(self, args: List[str], cwd: str):
        if not args:
            return ("", "touch: missing file operand\n", cwd, 2)
        for a in args:
            p = self._path_resolve(a, cwd)
            dirp = os.path.dirname(p)
            if dirp and not os.path.exists(dirp):
                os.makedirs(dirp, exist_ok=True)
            with open(p, "a"):
                os.utime(p, None)
        return ("", "", cwd, 0)

    def _mv(self, args: List[str], cwd: str):
        if len(args) < 2:
            return ("", "mv: missing file operands\n", cwd, 2)
        srcs = [self._path_resolve(a, cwd) for a in args[:-1]]
        dest = self._path_resolve(args[-1], cwd)
        if len(srcs) > 1 and not os.path.isdir(dest):
            return ("", "mv: target is not a directory\n", cwd, 1)
        try:
            for s in srcs:
                if not os.path.exists(s):
                    return ("", f"mv: cannot stat '{s}': No such file or directory\n", cwd, 1)
                if os.path.isdir(dest):
                    shutil.move(s, os.path.join(dest, os.path.basename(s)))
                else:
                    shutil.move(s, dest)
            return ("", "", cwd, 0)
        except Exception as e:
            return ("", f"mv error: {e}\n", cwd, 1)

    def _cp(self, args: List[str], cwd: str):
        if len(args) < 2:
            return ("", "cp: missing file operands\n", cwd, 2)
        recursive = False
        files = []
        dest = None
        for a in args:
            if a == "-r":
                recursive = True
            else:
                files.append(a)
        if len(files) < 2:
            return ("", "cp: missing destination file operand after source\n", cwd, 2)
        srcs = [self._path_resolve(a, cwd) for a in files[:-1]]
        dest = self._path_resolve(files[-1], cwd)
        if len(srcs) > 1 and not os.path.isdir(dest):
            return ("", "cp: target is not a directory\n", cwd, 1)
        try:
            for s in srcs:
                if not os.path.exists(s):
                    return ("", f"cp: cannot stat '{s}': No such file or directory\n", cwd, 1)
                if os.path.isdir(s):
                    if not recursive:
                        return ("", f"cp: -r not specified; omitting directory '{s}'\n", cwd, 1)
                    shutil.copytree(s, os.path.join(dest, os.path.basename(s)))
                else:
                    if os.path.isdir(dest):
                        shutil.copy2(s, os.path.join(dest, os.path.basename(s)))
                    else:
                        shutil.copy2(s, dest)
            return ("", "", cwd, 0)
        except Exception as e:
            return ("", f"cp error: {e}\n", cwd, 1)

    def _cpu(self):
        perc = psutil.cpu_percent(interval=0.5, percpu=False)
        return (f"CPU: {perc}%\n", "", None, 0)

    def _mem(self):
        m = psutil.virtual_memory()
        total = m.total
        used = m.used
        percent = m.percent
        return (f"Memory: {used}/{total} bytes ({percent}%)\n", "", None, 0)

    def _ps(self, args: List[str]):
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            info = p.info
            procs.append(f"{info.get('pid'):6d} {info.get('name')[:20]:20s} CPU%:{info.get('cpu_percent'):5.1f} MEM%:{info.get('memory_percent'):5.1f}")
        procs_sorted = sorted(procs)[:200]  # limit
        return ("\n".join(procs_sorted) + "\n", "", None, 0)

    def _help_text(self):
        return (
            "Supported commands:\n"
            "  pwd, ls [-l] [path], cd <path>, mkdir <name>, rmdir <name>, rm [-r] <path>\n"
            "  cat <file>, touch <file>, mv <src> <dest>, cp [-r] <src> <dest>\n"
            "  echo [text] [> file] [>> file], head <file>, tail <file>\n"
            "  cpu, mem, ps, whoami, date, uptime\n"
            "  clear, help\n"
        )