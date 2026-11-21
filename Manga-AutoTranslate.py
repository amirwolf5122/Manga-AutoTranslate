
import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", auto_download=["html"])


@app.cell
def _():
    import subprocess

    subprocess.run(
        "rm -rf * && "
        "git clone https://github.com/amirwolf5122/Manga-AutoTranslate.git && "
        "cd Manga-AutoTranslate && "
        "mv * ../ && "
        "rm -rf Manga-AutoTranslate",
        shell=True,
        check=True
    )
    return


@app.cell
def _():

    import os
    import sys
    import manga_app as app

    print("=" * 45)
    print("     Manga Translator")
    print("=" * 45)
    print("  [1] Web  - رابط مرورگر")
    print("  [2] CLI  - ترمینال")
    print("  [3] Exit")
    print()

    app.ensure_dirs()

    choice = input("انتخاب کنید [1/2/3]: ").strip().lower()

    if choice in ("1", "web"):
        app.run_web()

    elif choice in ("2", "cli"):
        app.auto_update_on_start(log=print)

        if not app.manga_py_ok():
            print(app.MANGA_MIXED_MSG)
        else:
            app.run_cli([])

    elif choice in ("3", "exit", "q"):
        print("خروج...")

    else:
        print("گزینه نامعتبر")

    return


if __name__ == "__main__":
    app.run()
