#!/usr/bin/env bash
# Download the 8 canonical two-domain PDB structures used throughout thread 2.
set -e
mkdir -p "$(dirname "$0")/../data/pdb"
cd "$(dirname "$0")/../data/pdb"
for p in 1CLL 3PGK 1PHP 1GD1 6LDH 8TLN 4AKE 2LZM; do
  [ -f "$p.pdb" ] || curl -sL "https://files.rcsb.org/download/$p.pdb" -o "$p.pdb"
done
echo "fetched: $(ls *.pdb | tr '\n' ' ')"
