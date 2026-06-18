# -*- coding: utf-8 -*-
"""
Деплой лайт-лэндинга на SpaceWeb по FTP.
Креды читаются из локального файла .ftp (в .gitignore, в git не попадает).

Формат .ftp (key=value, по строке):
    host=ftp.xxxxx.swtest.ru
    user=ваш_ftp_логин
    pass=ваш_ftp_пароль
    dir=/public_html
    url=https://xxxxx.swtest.ru   # опционально, для проверки после заливки

Запуск:  python deploy_sweb.py
"""
import os, sys, io, glob
from ftplib import FTP, FTP_TLS, error_perm

REPO = os.path.dirname(os.path.abspath(__file__))
CREDS = os.path.join(REPO, ".ftp")

def read_creds():
    if not os.path.isfile(CREDS):
        sys.exit("НЕТ файла .ftp с кредами — положи его рядом со скриптом (см. шапку файла).")
    c = {}
    with io.open(CREDS, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            c[k.strip()] = v.strip()
    for k in ("host", "user", "pass"):
        if not c.get(k):
            sys.exit("В .ftp не хватает поля: %s" % k)
    c.setdefault("dir", "/public_html")
    return c

def connect(c):
    # сначала пробуем защищённый FTPS, иначе обычный FTP
    try:
        ftps = FTP_TLS()
        ftps.connect(c["host"], 21, timeout=30)
        ftps.login(c["user"], c["pass"])
        ftps.prot_p()
        ftps.set_pasv(True)
        print("Подключение: FTPS (шифрованное)")
        return ftps
    except Exception as e:
        print("FTPS не вышло (%s) — пробую обычный FTP" % type(e).__name__)
        ftp = FTP()
        ftp.connect(c["host"], 21, timeout=30)
        ftp.login(c["user"], c["pass"])
        ftp.set_pasv(True)
        print("Подключение: обычный FTP")
        return ftp

def ensure_cwd(ftp, path):
    ftp.cwd(path)

def upload(ftp, localpath, remotename):
    with open(localpath, "rb") as f:
        ftp.storbinary("STOR " + remotename, f)
    print("  ↑ %s (%.0f КБ)" % (remotename, os.path.getsize(localpath)/1024))

def main():
    c = read_creds()
    ftp = connect(c)
    try:
        ensure_cwd(ftp, c["dir"])
        print("Каталог сайта: %s" % c["dir"])

        # index.html (перезаписываем дефолтный)
        upload(ftp, os.path.join(REPO, "index.html"), "index.html")

        # папка img
        try:
            ftp.cwd("img")
        except error_perm:
            ftp.mkd("img")
            ftp.cwd("img")
            print("  создан каталог img/")
        imgs = sorted(glob.glob(os.path.join(REPO, "img", "*.jpg")))
        for p in imgs:
            upload(ftp, p, os.path.basename(p))
        print("Загружено картинок: %d" % len(imgs))
        ftp.cwd(c["dir"])

        print("\nСодержимое %s:" % c["dir"])
        ftp.retrlines("LIST")
    finally:
        try: ftp.quit()
        except Exception: ftp.close()

    if c.get("url"):
        print("\nПроверь: %s" % c["url"])

if __name__ == "__main__":
    main()
