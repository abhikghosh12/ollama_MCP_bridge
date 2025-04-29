@echo off
echo Starting ADK Web Server with MCP Agent Solution
echo ==============================================

cd %~dp0

REM Parse command line options
set SERVERS=
set SKIP_PREP=

:parse_args
if "%~1"=="" goto run_scripts
if /i "%~1"=="--servers" (
    shift
    :parse_servers
    if "%~1"=="" goto run_scripts
    if "%~1:~0,2%"=="--" goto parse_args
    set SERVERS=%SERVERS% %1
    shift
    goto parse_servers
)
if /i "%~1"=="--skip-prep" (
    set SKIP_PREP=true
    shift
    goto parse_args
)
REM If not a known option, assume it's a server name
set SERVERS=%SERVERS% %1
shift
goto parse_args

:run_scripts
if "%SKIP_PREP%"=="true" (
    echo Skipping MCP tools preparation as requested.
) else (
    echo Preparing MCP tools (all servers from config)...    
    if "%SERVERS%"=="" (
        python prepare_mcp_tools.py
    ) else (
        python prepare_mcp_tools.py --servers%SERVERS%
    )
    echo MCP tools preparation complete.
)

echo Launching ADK Web Server...
adk web

pause
