#!/bin/bash -e

ktfmt android_app/
black app/ scripts/
prettier --write evaluation/