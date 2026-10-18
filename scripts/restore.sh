#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: ./scripts/restore.sh <backup-file-name>" >&2
  exit 2
fi
backup_file=$1
case "$backup_file" in
  */*|*\\*) echo "Backup name must not contain a path" >&2; exit 2 ;;
esac
if [ ! -f "backups/$backup_file" ]; then
  echo "Backup not found: backups/$backup_file" >&2
  exit 2
fi
docker run --rm --network sabha_data --env-file .env \
  -v "$(pwd)/backups:/backups:ro" \
  -e "BACKUP_NAME=$backup_file" mongo:8.0.32-noble sh -ec '
    exec mongorestore --host mongo --username "$MONGO_APP_USERNAME" \
      --password "$MONGO_APP_PASSWORD" --authenticationDatabase "$MONGO_DATABASE" \
      --db "$MONGO_DATABASE" --archive="/backups/$BACKUP_NAME" --gzip
  '
