@echo off

python.msi
pause

cls
copy ffmpeg.exe C:\Python27\


cls

C:\Python27\Scripts\pip.exe install autosub
echo - Step 1 Autosub Installed - Completed 
pause

cls
copy autosub_app.py C:\Python27\Scripts\
echo - Step 2 Completed 
echo - Fix Script 0.3.12 For Windows Installed 

python -m pip install --upgrade pip
pause

cls
copy AutoSub_English.bat "%APPDATA%\Microsoft\Windows\SendTo"
copy AutoSub_Japanese.bat "%APPDATA%\Microsoft\Windows\SendTo"
copy AutoSub_Korean.bat "%APPDATA%\Microsoft\Windows\SendTo"
copy AutoSub_Indo.bat "%APPDATA%\Microsoft\Windows\SendTo"


echo - Step 3 "Batch Send To" Completed 

cd python27
xcopy *.*/s/a c:\python27

Explorer shell:sendto
