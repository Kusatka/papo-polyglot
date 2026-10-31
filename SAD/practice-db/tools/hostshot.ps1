# Кадр экрана хоста без следов Claude: прячет ВСЕ видимые окна процессов Claude (окно приложения,
# рамку computer-use, значок на панели задач уходит вместе с окном), снимает весь экран, возвращает окна.
#   .\hostshot.ps1 -Out ...\pr1\screens\01.png [-Activate <часть заголовка окна>] [-Delay 2]
param([Parameter(Mandatory)][string]$Out, [string]$Activate = '', [int]$Delay = 2, [int[]]$Mouse = @(1915, 600))
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
if (-not ('W3' -as [type])) {
Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class W3 {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern void SwitchToThisWindow(IntPtr h, bool alt);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, int dx, int dy, uint d, UIntPtr e);
  public static List<IntPtr> Visible(HashSet<uint> pids) {
    var r = new List<IntPtr>();
    EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p); if (pids.Contains(p) && IsWindowVisible(h)) r.Add(h); return true; }, IntPtr.Zero);
    return r;
  }
  public static IntPtr ByTitle(string part) {
    IntPtr found = IntPtr.Zero;
    EnumWindows((h, l) => { if (!IsWindowVisible(h)) return true; var sb = new StringBuilder(512); GetWindowText(h, sb, 512);
      if (sb.ToString().IndexOf(part, StringComparison.OrdinalIgnoreCase) >= 0) { found = h; return false; } return true; }, IntPtr.Zero);
    return found;
  }
}
"@ }
[W3]::SetProcessDPIAware() | Out-Null
$pids = New-Object 'System.Collections.Generic.HashSet[uint32]'
Get-Process -Name Claude -ErrorAction SilentlyContinue | ForEach-Object { [void]$pids.Add([uint32]$_.Id) }
$wins = [W3]::Visible($pids)
try {
  [W3]::SetCursorPos($Mouse[0], $Mouse[1]) | Out-Null   # заранее: окно не должно подняться под курсором (подсветка кнопки «Закрыть»)
  foreach ($h in $wins) { [W3]::ShowWindow($h, 0) | Out-Null }
  if ($Activate) {
    $t = [W3]::ByTitle($Activate)
    if ($t -ne [IntPtr]::Zero) {
      [W3]::SwitchToThisWindow($t, $true)   # без нажатия Alt: в браузере Alt подсвечивает кнопку меню
      [W3]::ShowWindow($t, 3) | Out-Null; [W3]::BringWindowToTop($t) | Out-Null; [W3]::SetForegroundWindow($t) | Out-Null
    } else { Write-Warning "окно '$Activate' не найдено" }
  }
  [W3]::SetCursorPos($Mouse[0], $Mouse[1]) | Out-Null   # курсор в сторону: без подсказок и подсветки под ним
  [W3]::mouse_event(1, 2, 2, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 150; [W3]::mouse_event(1, -2, -2, 0, [UIntPtr]::Zero)   # настоящее движение: окно снимает подсветку кнопок рамки
  Start-Sleep $Delay
  $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $gr = [System.Drawing.Graphics]::FromImage($bmp); $gr.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
  $bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png); $gr.Dispose(); $bmp.Dispose()
  "$Out $($b.Width)x$($b.Height), скрыто окон Claude: $($wins.Count)"
} finally { foreach ($h in $wins) { [W3]::ShowWindow($h, 5) | Out-Null } }
