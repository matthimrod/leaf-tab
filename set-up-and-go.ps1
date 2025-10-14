Push-Location .

# Set the location to the script's directory
Set-Location -Path $PSScriptRoot

$output_filename = "output\leaf_tab $((Get-Date).ToString('yyyy-MM-dd hhmm')).xlsx"

.venv\Scripts\activate.ps1
python .\leaf_tab.py -o "$($output_filename)"
start "$($output_filename)"

Pop-Location
