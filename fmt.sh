#!/bin/bash -e

ktfmt --kotlinlang-style android_app/{app,build-logic} android_app/library/{network,utils} android_app/library/*
black app/ scripts/
npx prettier --write evaluation/