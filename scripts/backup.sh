#!/bin/sh
set -eu

backup_name=${1:-"sabha-$(date -u +%Y%m%dT%H%M%SZ).archive.gz"}
case "$backup_name" in
  */*|*\\*) echo "Backup name must not contain a path" >&2; exit 2 ;;
esac
mkdir -p backups
docker run --rm --network sabha_data --env-file .env \
  -v "$(pwd)/backups:/backups" \
  -e "BACKUP_NAME=$backup_name" mongo:8.0.32-noble sh -ec '
    exec mongodump --host mongo --username "$MONGO_APP_USERNAME" \
      --password "$MONGO_APP_PASSWORD" --authenticationDatabase "$MONGO_DATABASE" \
      --db "$MONGO_DATABASE" --archive="/backups/$BACKUP_NAME" --gzip
  '
printf 'Wrote backups/%s\n' "$backup_name"
