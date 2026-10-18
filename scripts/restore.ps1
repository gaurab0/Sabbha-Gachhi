param([Parameter(Mandatory = $true)][string]$Name)
$ErrorActionPreference = 'Stop'
if ([IO.Path]::GetFileName($Name) -ne $Name) { throw 'Backup name must not contain a path' }
$backupDirectory = (Resolve-Path 'backups').Path
$backupPath = Join-Path $backupDirectory $Name
if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) { throw "Backup not found: $backupPath" }
docker run --rm --network sabha_data --env-file .env `
    --mount "type=bind,source=$backupDirectory,target=/backups,readonly" `
    --env "BACKUP_NAME=$Name" `
    mongo:8.0.32-noble sh -ec 'exec mongorestore --host mongo --username "$MONGO_APP_USERNAME" --password "$MONGO_APP_PASSWORD" --authenticationDatabase "$MONGO_DATABASE" --db "$MONGO_DATABASE" --archive="/backups/$BACKUP_NAME" --gzip'
if ($LASTEXITCODE -ne 0) { throw 'MongoDB restore failed' }
