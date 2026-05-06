import difflib
import json
from pathlib import Path

from fastapi import FastAPI

from omni_rpc._app import create_app


def write_openapi_spec(service_name: str, spec: str) -> None:
    out_path = Path(f"openapi/{service_name}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(spec, encoding="utf-8")


def read_openapi_spec(service_name: str) -> str:
    try:
        with open(f"./openapi/{service_name}.json") as file:
            return json.dumps(json.load(file), indent=2) + "\n"
    except FileNotFoundError:
        return "{}"


def is_spec_updated(service_name: str, existing: str, new: str) -> bool:
    diff = difflib.unified_diff(
        existing.splitlines(True),
        new.splitlines(True),
        fromfile="existing",
        tofile="new",
    )
    diff_string = "".join(diff)
    if diff_string:
        print(f"❌ OpenAPI spec for {service_name} has changed:")
        print(diff_string)
        return True
    print(f"✅ OpenAPI spec for {service_name} is up to date.")
    return False


def get_new_spec(app: FastAPI) -> str:
    openapi = app.openapi()
    return json.dumps(openapi, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    service_name = "omni-rpc"
    app = create_app()

    new_spec = get_new_spec(app)
    existing_spec = read_openapi_spec(service_name)

    if is_spec_updated(service_name, existing_spec, new_spec):
        write_openapi_spec(service_name, new_spec)
        print(f"Wrote openapi/{service_name}.json")


if __name__ == "__main__":
    main()
