@echo off
echo ==============================================
echo  Soil Recommendation Engine - Mistral 7B QLoRA
echo ==============================================

echo Checking dependencies...
pip install -r requirements.txt

echo.
echo Starting FastAPI server...
echo Please wait while the model loads into VRAM (this may take a few minutes)...
echo.

python -m uvicorn app:app --host 0.0.0.0 --port 8000

pause
