$ErrorActionPreference = 'Stop'
foreach ($networkName in @('sabha_edge', 'sabha_data')) {
    docker network inspect $networkName *> $null
    if ($LASTEXITCODE -ne 0) {
        docker network create $networkName | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not create Docker network $networkName" }
        Write-Host "Created Docker network $networkName"
    } else {
        Write-Host "Docker network $networkName already exists"
    }
}
