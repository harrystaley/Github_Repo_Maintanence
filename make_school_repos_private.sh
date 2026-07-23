#!/usr/bin/env bash
set -euo pipefail

user="harrystaley"

gh repo list "$user" --limit 1000 --json name,isPrivate \
  --jq '.[] | select(.name | test("GT_|TAMUSA_"; "i")) | [.name, .isPrivate] | @tsv' \
  | while IFS=$'\t' read -r name isPrivate; do
      if [ "$isPrivate" = "true" ]; then
        echo "Already private: $user/$name"
      else
        echo "Making private: $user/$name"
        gh repo edit "$user/$name" \
          --visibility private \
          --accept-visibility-change-consequences
      fi
    done
