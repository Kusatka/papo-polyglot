# Кадр ПР №1: где хранятся данные (тома) и журналы (каталоги хоста) у каждой СУБД
$f = '{{.Name}}{{range .Mounts}}{{println}}   {{.Type}}  {{if .Name}}{{.Name}}{{else}}{{.Source}}{{end}}  ->  {{.Destination}}{{end}}'
Run "docker inspect -f '$f' practice01-redis practice01-mongodb practice01-neo4j practice01-elasticsearch practice01-postgres"
Write-Host ''
Run 'docker volume inspect practice01_postgres_data --format "{{.Name}}: driver={{.Driver}} mountpoint={{.Mountpoint}}"'
Write-Host ''
$global:KeepPrompt = $true   # дальше настоящее приглашение PowerShell
