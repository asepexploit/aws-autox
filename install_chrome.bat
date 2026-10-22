@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

title AWS-AutoX Installer
echo ============================================================
echo           AWS-AUTOX AUTO INSTALLER
echo ============================================================
echo.

set "TEMP_DIR=%USERPROFILE%\Downloads"
set "PYTHON_URL=https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe"
set "PYTHON_EXE=%TEMP_DIR%\python-3.14.0-amd64.exe"
set "GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.56.0.windows.2/Git-2.56.0.2-64-bit.exe"
set "GIT_EXE=%TEMP_DIR%\Git-2.56.0.2-64-bit.exe"
set "CHROME_EXE=%TEMP_DIR%\ChromeSetup.exe"
set "REPO_DIR=%USERPROFILE%\aws-autox"

:: ── Python ──────────────────────────────────────────────────────────────────
echo [1/5] Download Python 3.14 ...
if exist "%PYTHON_EXE%" (
    echo       Sudah ada di Downloads, skip download.
) else (
    curl -L -o "%PYTHON_EXE%" "%PYTHON_URL%"
    if !errorlevel! neq 0 (
        echo [ERROR] Gagal download Python. Cek koneksi internet.
        pause & exit /b 1
    )
)
echo [1/5] Install Python 3.14 ...
"%PYTHON_EXE%" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_launcher=1
if !errorlevel! neq 0 (
    echo [ERROR] Gagal install Python.
    pause & exit /b 1
)
echo       Python 3.14 berhasil diinstall.
echo.
set "PATH=%LocalAppData%\Programs\Python\Python314\;%LocalAppData%\Programs\Python\Python314\Scripts\;%ProgramFiles%\Python314\;%ProgramFiles%\Python314\Scripts\;%PATH%"

:: ── Git ─────────────────────────────────────────────────────────────────────
echo [2/5] Download Git ...
if exist "%GIT_EXE%" (
    echo       Sudah ada di Downloads, skip download.
) else (
    curl -L -o "%GIT_EXE%" "%GIT_URL%"
    if !errorlevel! neq 0 (
        echo [ERROR] Gagal download Git. Cek koneksi internet.
        pause & exit /b 1
    )
)
echo [2/5] Install Git ...
"%GIT_EXE%" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"
if !errorlevel! neq 0 (
    echo [ERROR] Gagal install Git.
    pause & exit /b 1
)
echo       Git berhasil diinstall.
echo.
set "PATH=%ProgramFiles%\Git\cmd;%PATH%"

:: ── Chrome ──────────────────────────────────────────────────────────────────
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    echo [SKIP] Chrome sudah terinstall.
) else (
    echo [3/5] Download Chrome ...
    if exist "%CHROME_EXE%" (
        echo       Sudah ada di Downloads, skip download.
    ) else (
        curl -L -o "%CHROME_EXE%" "https://dl.google.com/tag/s/appguid%%3D%%7B8A69D345-D564-463C-AFF1-A69D9E530F96%%7D%%26iid%%3D%%7B6DC4D1AC-51F1-161C-831D-769C157B16B2%%7D%%26lang%%3Den%%26browser%%3D4%%26usagestats%%3D1%%26appname%%3DGoogle%%2520Chrome%%26needsadmin%%3Dprefers%%26ap%%3D-arch_x64-statsdef_1%%26installdataindex%%3Dempty%%26brand%%3DHKFL/update2/installers/ChromeSetup.exe"
        if !errorlevel! neq 0 (
            echo [ERROR] Gagal download Chrome.
            pause & exit /b 1
        )
    )
    echo [3/5] Install Chrome ...
    "%CHROME_EXE%" /silent /install
    if !errorlevel! neq 0 (
        echo [ERROR] Gagal install Chrome.
        pause & exit /b 1
    )
    echo       Chrome berhasil diinstall.
)
echo.

:: ── Git clone aws-autox ─────────────────────────────────────────────────────
echo [4/5] Clone aws-autox ke %REPO_DIR% ...
if exist "%REPO_DIR%\.git" (
    echo       Repo sudah ada, pull terbaru ...
    cd /d "%REPO_DIR%"
    git pull origin master
) else (
    if exist "%REPO_DIR%" rd /s /q "%REPO_DIR%"
    git clone https://github.com/asepexploit/aws-autox.git "%REPO_DIR%"
    if !errorlevel! neq 0 (
        echo [ERROR] Gagal clone repo.
        pause & exit /b 1
    )
    cd /d "%REPO_DIR%"
)
echo       aws-autox berhasil di-clone.
echo.

:: ── pip install + patchright ─────────────────────────────────────────────────
echo [5/5] Install Python dependencies ...
cd /d "%REPO_DIR%"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [ERROR] Gagal install requirements.
    pause & exit /b 1
)
pip install patchright
if !errorlevel! neq 0 (
    echo [ERROR] Gagal install patchright.
    pause & exit /b 1
)
python -m patchright install chromium
if !errorlevel! neq 0 (
    echo [ERROR] Gagal install patchright chromium.
    pause & exit /b 1
)
echo       Dependencies berhasil diinstall.
echo.

echo ============================================================
echo  Semua selesai! Repo ada di: %REPO_DIR%
echo  Jalankan: python main.py
echo ============================================================
pause
endlocal
