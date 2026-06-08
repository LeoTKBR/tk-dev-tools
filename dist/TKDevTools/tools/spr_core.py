from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PIL import Image

from core_types import BinaryReader, Client, GameFeature, SPRITE_SIZE


class Pixel:
    def __init__(self, r: int, g: int, b: int, a: int):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def is_transparent(self) -> bool:
        return self.r == 0 and self.g == 0 and self.b == 0 and self.a == 0


class Sprite:
    def __init__(self, image: Image.Image):
        self.image = image


class SpriteManager:
    def __init__(self, client: Client):
        self.client = client
        self.signature = 0
        self.sprites: List[Optional[Sprite]] = []

    def load_spr(self, path: Path, used_sprite_ids: Optional[set[int]] = None) -> bool:
        try:
            reader = BinaryReader(path.read_bytes())
            self.signature = reader.read_u32()
            sprite_count = reader.read_u32() if self.client.get_feature(GameFeature.GameSpritesU32) else reader.read_u16()
            sprites_offset = reader.tell()
            self.sprites = [None] * (sprite_count + 1)
            if used_sprite_ids is not None:
                used_sprite_ids = {sprite_id for sprite_id in used_sprite_ids if 1 <= sprite_id <= sprite_count}

            for sprite_id in range(1, sprite_count + 1):
                reader.seek(sprites_offset + (sprite_id - 1) * 4)
                sprite_address = reader.read_u32()
                if sprite_address == 0 or self.sprites[sprite_id] is not None:
                    continue
                if used_sprite_ids is not None and sprite_id not in used_sprite_ids:
                    continue

                reader.seek(sprite_address)
                self.sprites[sprite_id] = Sprite(self._read_sprite(reader))

            return True
        except Exception as exc:
            raise RuntimeError(f"Failed to load SPR file: {exc}") from exc

    def _read_sprite(self, reader: BinaryReader) -> Image.Image:
        reader.read_bytes(3)
        pixel_data_size = reader.read_u16()
        write_pos = 0
        read = 0
        use_alpha = self.client.get_feature(GameFeature.GameSpritesAlphaChannel)
        channels = 4 if use_alpha else 3
        pixels: List[int] = []

        while read < pixel_data_size and write_pos < SPRITE_SIZE * SPRITE_SIZE * 4:
            transparent_pixels = reader.read_u16()
            colored_pixels = reader.read_u16()

            for _ in range(transparent_pixels):
                pixels.extend([0, 0, 0, 0])
                write_pos += 4

            for _ in range(colored_pixels):
                r = reader.read_u8()
                g = reader.read_u8()
                b = reader.read_u8()
                a = reader.read_u8() if use_alpha else 255
                pixels.extend([r, g, b, a])
                write_pos += 4

            read += 4 + (channels * colored_pixels)

        while write_pos < SPRITE_SIZE * SPRITE_SIZE * 4:
            pixels.extend([0, 0, 0, 0])
            write_pos += 4

        return Image.frombytes("RGBA", (SPRITE_SIZE, SPRITE_SIZE), bytes(pixels))

    def get_sprite(self, sprite_id: int) -> Optional[Sprite]:
        if sprite_id < 0 or sprite_id >= len(self.sprites):
            return None
        return self.sprites[sprite_id]
