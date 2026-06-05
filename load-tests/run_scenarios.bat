@echo off
REM ==========================================================================
REM run_scenarios.bat — orchestrator for the 72-scenario load test battery
REM
REM Runs Locust headless for every combination of:
REM   - operation: resize, grayscale, edge
REM   - image_size: small, medium, large
REM   - users: 1, 10, 50, 100  (200 removed to stay within Learner Lab credit limits)
REM   - repetition: 2
REM
REM Total: 3 x 3 x 4 x 2 = 72 runs, 2 minutes each ≈ 2.4-3 hours.
REM (Original config was 90 runs x 5 min = 7.5 h, ~$57/person — exceeds Vocareum $50 limit)
REM
REM Output CSVs land in results\ with names like:
REM   results\grayscale_medium_50u_rep1_stats.csv
REM ==========================================================================

setlocal enabledelayedexpansion

REM Check that Locust is available
where locust >nul 2>&1
if errorlevel 1 (
    echo ERROR: locust is not on PATH. Activate the venv first:
    echo    .venv\Scripts\activate
    exit /b 1
)

REM Make sure results folder exists
if not exist results mkdir results

REM Run duration per scenario (Locust accepts e.g. "5m", "3m", "30s")
REM Reduced from 5m to 2m — enough samples for reliable stats, stays within credit budget
set RUN_TIME=2m

REM Spawn rate (users/sec ramp-up)
set SPAWN_RATE=10

REM HOST argument can be a dummy because the locustfile uses absolute URLs.
set HOST_DUMMY=https://placeholder.example.com

REM Operations to test
set OPERATIONS=resize grayscale edge

REM Image sizes
set SIZES=small medium large

REM Concurrency levels (200 removed — too costly on Learner Lab)
set USERS=1 10 50 100

REM Repetitions
set REPS=1 2

set TOTAL=0
for %%o in (%OPERATIONS%) do (
    for %%s in (%SIZES%) do (
        for %%u in (%USERS%) do (
            for %%r in (%REPS%) do (
                set /a TOTAL=!TOTAL!+1
            )
        )
    )
)
echo Will run %TOTAL% scenarios. Estimated total time: ~%TOTAL% x %RUN_TIME%.
echo Press Ctrl-C to abort, otherwise starting in 5 seconds...
timeout /t 5 /nobreak >nul

set COUNT=0
for %%o in (%OPERATIONS%) do (
    for %%s in (%SIZES%) do (
        for %%u in (%USERS%) do (
            for %%r in (%REPS%) do (
                set /a COUNT=!COUNT!+1
                set OPERATION=%%o
                set IMAGE_SIZE=%%s
                set OUTFILE=results\%%o_%%s_%%uu_rep%%r

                echo.
                echo ==========================================================
                echo [!COUNT!/%TOTAL%] op=%%o size=%%s users=%%u rep=%%r
                echo ==========================================================
                locust -f locustfile.py ^
                    --host !HOST_DUMMY! ^
                    --users %%u ^
                    --spawn-rate %SPAWN_RATE% ^
                    --run-time %RUN_TIME% ^
                    --headless ^
                    --csv !OUTFILE!

                REM Small pause between scenarios so Lambda has time to settle
                echo Waiting 30 seconds before next scenario...
                timeout /t 30 /nobreak >nul
            )
        )
    )
)

echo.
echo All scenarios complete. Results saved to load-tests\results\
endlocal
