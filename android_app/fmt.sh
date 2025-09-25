#!/bin/bash -e

ktfmt android_app/app/src
black app/ scripts/
npx prettier --write evaluation/