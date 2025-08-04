import os
import sys
import msvcrt
import subprocess
import json
from colorama import Fore, Style

# My custom imports
from ncpm import install, uninstall
colour_state = {'code': Style.RESET_ALL}

def coloured_input(prompt):
    sys.stdout.write(colour_state['code'] + prompt)
    sys.stdout.flush()
    buffer, cursor = [], 0
    prompt_len = len(prompt)  # Protect this much from backspace

    while True:
        ch = msvcrt.getwch()
        if ch == '\r':
            sys.stdout.write('\n')
            break
        elif ch == '\x08':  # Backspace
            if cursor > 0:
                buffer.pop(cursor - 1)
                cursor -= 1
                sys.stdout.write('\b' + ''.join(buffer[cursor:]) + ' ')
                sys.stdout.write('\b' * (len(buffer) - cursor + 1))
                sys.stdout.flush()
        elif ch == '\xe0':  # Arrow keys
            code = msvcrt.getwch()
            if code == 'K' and cursor > 0:  # Left
                sys.stdout.write('\b')
                cursor -= 1
            elif code == 'M' and cursor < len(buffer):  # Right
                sys.stdout.write(buffer[cursor])
                cursor += 1
            sys.stdout.flush()
        else:
            buffer.insert(cursor, ch)
            sys.stdout.write(ch + ''.join(buffer[cursor + 1:]))
            sys.stdout.write('\b' * (len(buffer) - cursor - 1))
            cursor += 1
            sys.stdout.flush()
    return ''.join(buffer).strip()

def loadN0vaCommand():
    # --- setup colour map & state ---
    colour_map = {
        'red': Fore.RED,
        'orange': Fore.LIGHTRED_EX,
        'yellow': Fore.YELLOW,
        'green': Fore.GREEN,
        'blue': Fore.BLUE,
        'purple': Fore.MAGENTA,
        'pink': Fore.LIGHTMAGENTA_EX,
        'white': Fore.WHITE,
        'black': Fore.BLACK,
        'grey': Fore.LIGHTBLACK_EX,
        'default': Style.RESET_ALL
    }
    colour_state = {'code': Style.RESET_ALL}

    # --- wrap stdout & stderr for colourful output ---
    class ColourWriter:
        def __init__(self, orig): self.orig = orig
        def write(self, text): self.orig.write(colour_state['code'] + text + Style.RESET_ALL)
        def flush(self): self.orig.flush()
        def isatty(self): return getattr(self.orig, 'isatty', lambda: False)()

    sys.stdout = ColourWriter(sys.stdout)
    sys.stderr = ColourWriter(sys.stderr)

    # --- file system & config setup ---
    userprofile = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    base_dir = os.path.join(userprofile, 'N0vaCommand')
    files_dir = os.path.join(base_dir, 'files')
    home = files_dir  # This is your root command dir like "~"
    path_file = os.path.join(base_dir, 'path.json')
    os.makedirs(files_dir, exist_ok=True)

    # --- load or init path list ---
    try:
        with open(path_file, 'r') as f: paths = json.load(f)
    except Exception:
        paths = []

    cwd = files_dir

    def save_paths():
        with open(path_file, 'w') as f: json.dump(paths, f, indent=2)

    # --- resolve a name to an executable file path ---
    def resolve_executable(name):
        base, ext = os.path.splitext(name)
        suffixes = [ext] if ext else ['.exe', '.bat', '.json', '']
        # search current dir
        for suf in suffixes:
            candidate = os.path.join(cwd, name + (suf if not name.endswith(suf) else ''))
            if os.path.isfile(candidate): return candidate
        # search added paths
        for p in paths:
            p_full = os.path.join(files_dir, p)
            if os.path.isdir(p_full):
                # look inside directory
                for suf in suffixes:
                    cand = os.path.join(p_full, name + (suf if not name.endswith(suf) else ''))
                    if os.path.isfile(cand): return cand
            else:
                basep, extp = os.path.splitext(p_full)
                if extp:
                    if basep == os.path.splitext(name)[0] or os.path.basename(p_full) == name:
                        return p_full
                else:
                    for suf in suffixes:
                        cand = p_full + suf
                        if os.path.isfile(cand): return cand
        return None

    # --- command processor ---
    def process_line(line):
        nonlocal cwd
        parts = line.split(None, 1)
        cmd = parts[0].lower()

        # run
        if cmd == 'run':
            if len(parts) < 2:
                sys.stdout.write("Usage: run <name> [args]\n"); return
            toks = parts[1].split(); name = toks[0]; flags = toks[1:]
            exe = resolve_executable(name)
            if not exe: sys.stdout.write(f"run: '{name}' not found\n"); return
            _, e = os.path.splitext(exe)
            if e.lower() in ('.exe', '.bat'):
                subprocess.call([exe] + flags, cwd=os.path.dirname(exe))
            else:
                try: os.startfile(exe)
                except: sys.stdout.write(f"Could not open '{exe}'\n")
            return

        # path add/remove
        if cmd == 'path':
            if len(parts) < 2:
                sys.stdout.write("Usage: path <add|remove> <path/to/file_or_folder>\n")
                return

            args = parts[1].split(None, 1)
            if len(args) < 2:
                sys.stdout.write("Usage: path <add|remove> <path/to/file_or_folder>\n")
                return
            sub, rel = args
            rel = rel.strip().replace('\\', '/')

            # 🎯 Resolve into an absolute path:
            if rel.startswith('~/'):
                # ~/... → under your home
                abs_p = os.path.abspath(os.path.join(home, rel[2:]))
            elif rel.startswith('/'):
                # absolute in Unix style (rare on Windows, but just in case)
                abs_p = os.path.abspath(rel)
            else:
                # everything else → relative to cwd
                abs_p = os.path.abspath(os.path.join(cwd, rel))

            # 🔒 Security: only allow under files_dir
            if not abs_p.startswith(files_dir):
                sys.stdout.write("path: can only manage paths under N0vaCommand/files\n")
                return

            if not os.path.exists(abs_p):
                sys.stdout.write(f"path: '{rel}' does not exist\n")
                return

            norm = os.path.relpath(abs_p, files_dir).replace('\\', '/')
            if sub == 'add':
                if norm in paths:
                    sys.stdout.write(f"path: '{norm}' already in path\n")
                else:
                    paths.append(norm)
                    save_paths()
                    sys.stdout.write(f"Added '{norm}' to path\n")
            elif sub == 'remove':
                if norm in paths:
                    paths.remove(norm)
                    save_paths()
                    sys.stdout.write(f"Removed '{norm}' from path\n")
                else:
                    sys.stdout.write(f"path: '{norm}' not found in path\n")
            else:
                sys.stdout.write("Usage: path <add|remove> <path/to/file_or_folder>\n")
            return

        # ---- colour command ----
        if cmd in ('colour', 'color'):
            if len(parts) < 2:
                sys.stdout.write("Usage: colour <colourname>\n")
            else:
                choice = parts[1].strip().lower()
                colour_state['code'] = colour_map.get(choice, Style.RESET_ALL)
            return

        # ---- exit/quit ----
        if cmd in ('exit', 'quit'):
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            colour_state['code'] = Style.RESET_ALL
            print(Style.RESET_ALL, end='')
            sys.exit(0)

        # ---- change directory ----
        if cmd == 'cd':
            target = parts[1] if len(parts) > 1 else ''
            if target in ('', '~', '~/'):
                cwd = home
            else:
                if target.startswith('~/') or target.startswith('~\\'):
                    path = os.path.join(home, target[2:].lstrip("\\/"))
                else:
                    path = os.path.join(cwd, target)
                real = os.path.abspath(path)
                if os.path.isdir(real) and real.startswith(home):
                    cwd = real
                else:
                    sys.stdout.write(f"cd: no such directory: {target}\n")
            return

        # ---- make directory ----
        if cmd == 'mkdir':
            if len(parts) < 2 or not parts[1].strip():
                sys.stdout.write("mkdir: missing directory name\n")
                return
            tgt = parts[1].strip()
            if tgt.startswith('~/') or tgt.startswith('~\\'):
                path = os.path.join(home, tgt[2:].lstrip("\\/"))
            else:
                path = os.path.join(cwd, tgt)
            try:
                os.makedirs(path)
            except FileExistsError:
                sys.stdout.write(f"mkdir: cannot create '{tgt}': Already exists\n")
            except Exception as e:
                sys.stdout.write(f"mkdir: cannot create '{tgt}': {e}\n")
            return

        # ---- open Explorer ----
        if cmd == 'explorer':
            try:
                subprocess.Popen(f'explorer "{cwd}"')
            except Exception as e:
                sys.stdout.write(f"Failed to open explorer: {e}\n")
            return

        # ---- ncpm install/uninstall ----
        if cmd == 'ncpm':
            if len(parts) < 2:
                sys.stdout.write("Usage: ncpm <install/uninstall> <Creator.PackageName>\n")
                return  # not enough args

            sub_parts = parts[1].strip().split(None, 1)
            if len(sub_parts) < 2:
                sys.stdout.write("Usage: ncpm <install/uninstall> <Creator.PackageName>\n")
                return  # still not enough args

            sub_cmd, pkg_name = sub_parts[0].lower(), sub_parts[1].strip()
            
            if sub_cmd == 'install':
                install(pkg_name)
            elif sub_cmd == 'uninstall':
                uninstall(pkg_name)
            return

        # ---- list files and folders ----
        if cmd == 'list':
            try:
                entries = os.listdir(cwd)
                if not entries:
                    sys.stdout.write("📂 This folder is empty.\n")
                else:
                    for entry in entries:
                        full_path = os.path.join(cwd, entry)
                        if os.path.isdir(full_path):
                            sys.stdout.write(f"{Fore.YELLOW}📁 {entry}{Style.RESET_ALL}\n")
                        else:
                            sys.stdout.write(f"{Fore.YELLOW}📄 {entry}{Style.RESET_ALL}\n")
            except Exception as e:
                sys.stdout.write(f"{Fore.RED}list: error listing files: {e}{Style.RESET_ALL}\n")
            print("")
            return

        sys.stdout.write(f"{cmd}: command not found\n")

    # banner & REPL
    os.system('cls' if os.name=='nt' else 'clear')
    print("N0vaCommand [Version 1.0.0]\nCreated by SuperGamer474\n")
    while True:
        rel = os.path.relpath(cwd, files_dir)
        display = "~\\" if rel=='.' else "~\\" + rel.replace('/', '\\') + "\\"
        try: line = coloured_input(f"{display}> ")
        except: print(); break
        if not line.strip(): continue
        for cmd in [c.strip() for c in line.split('&') if c.strip()]: process_line(cmd)

if __name__ == "__main__":
    loadN0vaCommand()