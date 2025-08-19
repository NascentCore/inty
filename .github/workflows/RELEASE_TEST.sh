#!/bin/bash -e

# Run this script to perform a set of test before releasing a new version

# Rebuild the docker image to make sure all dependencies are up to date
docker compose up --build --detach

# Run the evaluation frontend
pushd evaluation
npm run dev
popd
