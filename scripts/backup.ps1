param([string]$Name = "sabha-$((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')).archive.gz")
$ErrorActionPreference = 'Stop'
if ([IO.Path]::GetFileName($Name) -ne $Name) { throw 'Backup name must not contain a path' }
New-Item -ItemType Directory -Force -Path 'backups' | Out-Null
$backupPath = Join-Path (Resolve-Path 'backups').Path $Name
docker run --rm --network sabha_data --env-file .env `
    --mount "type=bind,source=$((Resolve-Path 'backups').Path),target=/backups" `
    --env "BACKUP_NAME=$Name" `
    mongo:8.0.32-noble sh -ec 'exec mongodump --host mongo --username "$MONGO_APP_USERNAME" --password "$MONGO_APP_PASSWORD" --authenticationDatabase "$MONGO_DATABASE" --db "$MONGO_DATABASE" --archive="/backups/$BACKUP_NAME" --gzip'
if ($LASTEXITCODE -ne 0) { throw 'MongoDB backup failed' }
Write-Host "Wrote $backupPath"
