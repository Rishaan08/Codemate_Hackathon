import os
import readline  
from executor import CommandExecutor

def main():
    execr = CommandExecutor()
    cwd = "/tmp"   
    os.makedirs(cwd, exist_ok=True)
    print("Python Terminal - type 'help' for commands. Ctrl-C to quit.")
    try:
        while True:
            try:
                inp = input(f"{cwd} $ ")
            except EOFError:
                print()
                break
            out, err, new_cwd, code = execr.run(inp, cwd)
            # if executor returns None as new_cwd for system stats, keep cwd
            if new_cwd:
                cwd = new_cwd
            if out:
                print(out, end="")
            if err:
                print(err, end="")
    except KeyboardInterrupt:
        print("\nExiting.")
    except Exception as e:
        print("Fatal error:", e)

if __name__ == "__main__":
    main()