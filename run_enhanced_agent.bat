@echo off
echo Enhanced MCP Agent Launcher
echo ===========================

cd %~dp0

REM Parse command line options
set SERVERS=
set SAFE_MODE=
set FAIL_FAST=
set RETRY=
set INIT_ONLY=
set FALLBACK_ONLY=

:parse_args
if "%~1"=="" goto run_agent
if /i "%~1"=="--safe" (
    set SAFE_MODE=--safe-mode
    shift
    goto parse_args
)
if /i "%~1"=="--fail-fast" (
    set FAIL_FAST=--fail-fast
    shift
    goto parse_args
)
if /i "%~1"=="--fallback" (
    set FALLBACK_ONLY=--fallback-only
    shift
    goto parse_args
)
if /i "%~1"=="--retry" (
    set RETRY=--retry %~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--init-only" (
    set INIT_ONLY=--init-only
    shift
    goto parse_args
)
if /i "%~1"=="--servers" (
    shift
    :parse_servers
    if "%~1"=="" goto run_agent
    if "%~1:~0,2%"=="--" goto parse_args
    set SERVERS=%SERVERS% %1
    shift
    goto parse_servers
)
REM If not a known option, assume it's a server name
set SERVERS=%SERVERS% %1
shift
goto parse_args

:run_agent
if "%FALLBACK_ONLY%"=="--fallback-only" (
    echo Fallback mode enabled - using built-in tools only.
    python run_enhanced_agent.py %FALLBACK_ONLY% %INIT_ONLY%
) else if "%SERVERS%"=="" (
    if "%SAFE_MODE%"=="" (
        echo No specific MCP servers specified, using all available servers.
        python run_enhanced_agent.py %FAIL_FAST% %RETRY% %INIT_ONLY%
    ) else (
        echo Safe mode enabled - using only essential servers.
        python run_enhanced_agent.py %SAFE_MODE% %FAIL_FAST% %RETRY% %INIT_ONLY%
    )
) else (
    echo Initializing with specified servers:%SERVERS%
    python run_enhanced_agent.py --servers%SERVERS% %SAFE_MODE% %FAIL_FAST% %RETRY% %INIT_ONLY%
)

if not "%INIT_ONLY%"=="" (
    echo Initialization complete. ADK web was not started due to --init-only flag.
)

pause
