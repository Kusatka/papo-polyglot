# Экспорт двух собранных DOCX через Microsoft Word, как в предыдущих отчётах проекта.
$ErrorActionPreference = 'Stop'
$reportWord = New-Object -ComObject Word.Application
$reportWord.Visible = $false
$reportWord.DisplayAlerts = 0
try {
    foreach ($number in @(2, 3)) {
        $sourcePath = Join-Path $PSScriptRoot "Отчёт_Лабораторная_$number.docx"
        $reportDocument = $reportWord.Documents.Open($sourcePath)
        try {
            $reportDocument.ExportAsFixedFormat([IO.Path]::ChangeExtension($sourcePath, '.pdf'), 17)
        } finally {
            $reportDocument.Close($false)
        }
    }
} finally {
    $reportWord.Quit()
}
