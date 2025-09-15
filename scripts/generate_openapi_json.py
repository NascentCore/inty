import argparse
import json

from app.main import app

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=str, default="app/openapi.json")
args = parser.parse_args()

json_str = json.dumps(app.openapi(), indent=4)

with open(args.output, "w") as f:
    f.write(json_str)

print(f"OpenAPI JSON saved to {args.output}")
