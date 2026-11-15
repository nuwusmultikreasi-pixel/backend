"""Ambil folder dinezy/ (templates & static) dari repo frontend saat build."""
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

FOLDER = "dinezy"


def unduh(repo, branch, token, tujuan):
    url = f"https://api.github.com/repos/{repo}/tarball/{branch}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=120) as resp, open(tujuan, "wb") as f:
        shutil.copyfileobj(resp, f)


def ekstrak(arsip, tujuan):
    tujuan = Path(tujuan)
    with tarfile.open(arsip) as tar:
        pilih = []
        for m in tar.getmembers():
            bagian = Path(m.name).parts
            if len(bagian) > 2 and bagian[1] == FOLDER:
                m.name = str(Path(*bagian[2:]))
                pilih.append(m)
        if not pilih:
            sys.exit(f"Folder '{FOLDER}/' tidak ditemukan di repo frontend.")
        if tujuan.exists():
            shutil.rmtree(tujuan)
        tujuan.mkdir(parents=True)
        tar.extractall(tujuan, members=pilih, filter="data")
    print(f"{len(pilih)} file tampilan disalin ke {tujuan}")


def main():
    repo = os.environ.get("FRONTEND_REPO", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    branch = os.environ.get("FRONTEND_BRANCH", "").strip() or "main"
    if not repo or not token:
        sys.exit("FRONTEND_REPO dan GITHUB_TOKEN wajib diisi di Environment Variables Coolify.")
    with tempfile.TemporaryDirectory() as tmp:
        arsip = Path(tmp) / "frontend.tar.gz"
        unduh(repo, branch, token, arsip)
        ekstrak(arsip, sys.argv[1] if len(sys.argv) > 1 else "frontend")


if __name__ == "__main__":
    main()
