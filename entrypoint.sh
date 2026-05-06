#!/bin/sh
set -e

if [ ! -d "data/ethereum-lists/_data/chains" ]; then
    echo "Chain data not found, bootstrapping..."
    omni-rpc init-chains
fi

exec "$@"
