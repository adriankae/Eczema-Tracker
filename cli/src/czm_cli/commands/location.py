from __future__ import annotations

import argparse
import mimetypes
from pathlib import Path

from ..errors import CzmError, EXIT_USAGE
from ..formatting import format_location, format_location_image_result, format_location_list
from ..schemas import LocationListResponse
from ._common import emit, resolve_location_id


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("location", parents=[parent], help="Manage locations")
    location_subparsers = parser.add_subparsers(dest="location_command", required=True)

    create = location_subparsers.add_parser("create", parents=[parent], help="Create a location")
    create.add_argument("--code", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--image")
    create.set_defaults(handler=handle_create)

    listing = location_subparsers.add_parser("list", parents=[parent], help="List locations")
    listing.set_defaults(handler=handle_list)

    image = location_subparsers.add_parser("image", parents=[parent], help="Manage a location image")
    image_subparsers = image.add_subparsers(dest="location_image_command", required=True)

    image_set = image_subparsers.add_parser("set", parents=[parent], help="Add or replace a location image")
    image_set.add_argument("location")
    image_set.add_argument("path")
    image_set.set_defaults(handler=handle_image_set)

    image_get = image_subparsers.add_parser("get", parents=[parent], help="Download a location image")
    image_get.add_argument("location")
    image_get.add_argument("--output", required=True)
    image_get.set_defaults(handler=handle_image_get)

    image_remove = image_subparsers.add_parser("remove", parents=[parent], help="Remove a location image")
    image_remove.add_argument("location")
    image_remove.set_defaults(handler=handle_image_remove)


def _image_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.exists() or not path.is_file():
        raise CzmError(f"image file not found: {value}", exit_code=EXIT_USAGE)
    return path


def _guess_content_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _upload_image(ctx, location_id: int, image_path: Path):
    return ctx.client.upload_file(
        f"/locations/{location_id}/image",
        field_name="image",
        file_path=image_path,
        content_type=_guess_content_type(image_path),
    )


def handle_create(ctx, args) -> int:
    payload = ctx.client.post("/locations", json={"code": args.code, "display_name": args.display_name})
    if args.image:
        location_id = payload["location"]["id"]
        try:
            payload = _upload_image(ctx, location_id, _image_path(args.image))
        except Exception as exc:
            raise CzmError(f"location created but image upload failed: {exc}", exit_code=getattr(exc, "exit_code", EXIT_USAGE)) from exc
    emit(ctx, payload, lambda data: format_location_image_result(data))
    return 0


def handle_list(ctx, args) -> int:
    payload = ctx.client.get("/locations")
    emit(ctx, payload, lambda data: format_location_list(LocationListResponse.model_validate(data).locations))
    return 0


def handle_image_set(ctx, args) -> int:
    location_id = resolve_location_id(ctx, args.location)
    payload = _upload_image(ctx, location_id, _image_path(args.path))
    emit(ctx, payload, format_location_image_result)
    return 0


def handle_image_get(ctx, args) -> int:
    if ctx.json_output:
        raise CzmError("location image get writes bytes to --output; JSON output is not supported", exit_code=EXIT_USAGE)
    location_id = resolve_location_id(ctx, args.location)
    content, _ = ctx.client.download_file(f"/locations/{location_id}/image")
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)
    if not ctx.quiet:
        print(f"Wrote location image to {output_path}")
    return 0


def handle_image_remove(ctx, args) -> int:
    location_id = resolve_location_id(ctx, args.location)
    payload = ctx.client.delete(f"/locations/{location_id}/image")
    emit(ctx, payload, format_location_image_result)
    return 0
