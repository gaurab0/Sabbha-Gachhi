#!/bin/sh
set -eu

for network in sabha_edge sabha_data; do
  if ! docker network inspect "$network" >/dev/null 2>&1; then
    docker network create "$network" >/dev/null
    printf 'Created Docker network %s\n' "$network"
  else
    printf 'Docker network %s already exists\n' "$network"
  fi
done
