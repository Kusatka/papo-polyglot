# Brave с отдельным чистым профилем и портом отладки 9222 (им управляет tools\cdp.mjs). .\brave.ps1 [url]
param([string]$Url = 'about:blank')
$prof = "$env:LOCALAPPDATA\sad-brave-profile"
$exe = "$env:ProgramFiles\BraveSoftware\Brave-Browser\Application\brave.exe"
Start-Process $exe -ArgumentList @('--remote-debugging-port=9222', "--user-data-dir=$prof", '--no-first-run',
  '--no-default-browser-check', '--start-maximized', '--lang=ru', '--disable-features=AIChat,Translate,CalculateNativeWinOcclusion',
  '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding', $Url)
