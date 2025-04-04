Push-Location .

# Set the location to the script's directory
Set-Location -Path $PSScriptRoot

.venv\Scripts\activate.ps1
python .\leaf_tab.py
start .\leaf_tab.xlsx

Pop-Location
