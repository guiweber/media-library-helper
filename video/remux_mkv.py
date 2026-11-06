
from pathlib import Path
import subprocess


def remux_mkv(path, confirm=True, recursive=True):
    path = Path(path).resolve()

    if path.is_file():
        files = [path] if path.suffix.lower() == ".mkv" else []
    elif path.is_dir():
        pattern = "**/*" if recursive else "*"
        files = sorted(
            p for p in path.glob(pattern)
            if p.is_file() and p.suffix.lower() == ".mkv"
        )
    else:
        raise FileNotFoundError(path)

    if not files:
        print("No MKV files found.")
        return

    print(f"Found {len(files)} MKV file(s) to process.")

    if confirm:
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return

    completed = 0
    failed = 0

    for file in files:
        tmp = file.with_name(file.stem + ".remux_tmp.mkv")

        print(f"Processing: {file}")

        try:
            subprocess.run(
                ["mkvmerge", "-o", str(tmp), str(file)],
                check=True,
                capture_output=True,
                text=True
            )

            tmp.replace(file)

            completed += 1
            print(f"Completed: {file}")

        except subprocess.CalledProcessError as e:
            failed += 1
            print(f"FAILED: {file}")
            print(e.stderr)

        finally:
            if tmp.exists():
                tmp.unlink()

    print(f"\nFinished: {completed} completed, {failed} failed.")
