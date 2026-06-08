from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from PIL import Image

from core_types import DatThingCategory, SPRITE_SIZE
from dat_core import DatManager, DatThingType, FrameGroupType
from spr_core import SpriteManager


def render_item_frame(frame_group, sprite_manager: SpriteManager, x: int, y: int, z: int, animation_frame: int) -> Image.Image:
    width_px = SPRITE_SIZE * frame_group.width
    height_px = SPRITE_SIZE * frame_group.height
    result = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))

    for layer in range(frame_group.layers):
        for w in range(frame_group.width):
            for h in range(frame_group.height):
                sprite_index = frame_group.sprites_index[
                    frame_group.get_sprite_index(w, h, layer, x, y, z, animation_frame)
                ]
                sprite = sprite_manager.get_sprite(sprite_index)
                if sprite is None:
                    continue
                dest_x = SPRITE_SIZE * (frame_group.width - w - 1)
                dest_y = SPRITE_SIZE * (frame_group.height - h - 1)
                result.paste(sprite.image, (dest_x, dest_y), sprite.image)

    return result


def build_item_frames(thing: DatThingType, sprite_manager: SpriteManager, fallback_duration_ms: int) -> tuple[List[Image.Image], List[int]]:
    frame_group = thing.get_frame_group(FrameGroupType.FrameGroupIdle)
    if frame_group is None:
        return [], []

    frames: List[Image.Image] = []
    durations: List[int] = []
    if thing.is_stackable() and frame_group.pattern_x == 4 and frame_group.pattern_y == 2:
        for pattern_y in range(frame_group.pattern_y):
            for pattern_x in range(frame_group.pattern_x):
                frames.append(render_item_frame(frame_group, sprite_manager, pattern_x, pattern_y, 0, 0))
                durations.append(fallback_duration_ms)
    else:
        for animation_frame in range(frame_group.animation_phases):
            frames.append(render_item_frame(frame_group, sprite_manager, 0, 0, 0, animation_frame))
            if frame_group.animator is not None:
                durations.append(frame_group.animator.get_duration_ms(animation_frame, fallback_duration_ms))
            else:
                durations.append(fallback_duration_ms)

    return frames, durations


def save_gif(frames: List[Image.Image], out_path: Path, duration_ms: int | List[int]):
    if not frames:
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rgba_frames = [frame.convert("RGBA") for frame in frames]
    first, rest = rgba_frames[0], rgba_frames[1:]
    first.save(
        out_path,
        save_all=True,
        append_images=rest,
        duration=duration_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )


def build_jobs(
    dat: DatManager,
    only_pickable: bool,
    start_id: int | None = None,
    end_id: int | None = None,
) -> List[tuple[int, int]]:
    jobs: List[tuple[int, int]] = []
    items = dat.get_category(DatThingCategory.ThingCategoryItem)
    first_id = max(100, start_id if start_id is not None else 100)
    last_id = min(len(items) - 1, end_id if end_id is not None else len(items) - 1)
    if last_id < first_id:
        return jobs

    for client_id in range(first_id, last_id + 1):
        thing = items[client_id] if client_id < len(items) else None
        if thing is None or thing.is_null():
            continue
        if only_pickable and not thing.is_pickupable():
            continue
        jobs.append((client_id, client_id))

    return jobs


def collect_used_sprite_ids(dat: DatManager, jobs: List[tuple[int, int]]) -> set[int]:
    used_sprite_ids: set[int] = set()
    for _, client_id in jobs:
        thing = dat.get_item(client_id)
        if thing is None or thing.is_null():
            continue
        for sprite_id in thing.iter_sprite_ids():
            if sprite_id:
                used_sprite_ids.add(sprite_id)
    return used_sprite_ids


def is_blank_frame(image: Image.Image) -> bool:
    return image.getbbox() is None


@dataclass
class ProgressEvent:
    kind: str
    payload: tuple
