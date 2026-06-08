from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from core_types import BinaryReader, Client, DatThingAttr, DatThingCategory, FrameGroupType, GameFeature


class FrameGroup:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.real_size = 0
        self.layers = 0
        self.pattern_x = 0
        self.pattern_y = 0
        self.pattern_z = 0
        self.animation_phases = 0
        self.animator: Optional[Animator] = None
        self.sprites_index: List[int] = []

    def get_sprite_index(self, w: int, h: int, l: int, x: int, y: int, z: int, a: int) -> int:
        index = ((((((a % self.animation_phases) * self.pattern_z + z) * self.pattern_y + y) * self.pattern_x + x) * self.layers + l) * self.height + h) * self.width + w
        if index >= len(self.sprites_index):
            raise RuntimeError("Sprite index out of range")
        return index


class Animator:
    def __init__(self):
        self.animation_phases = 0
        self.start_phase = 0
        self.loop_count = 0
        self.async_mode = False
        self.phase_durations: List[tuple[int, int]] = []

    def unserialize(self, animation_phases: int, reader: BinaryReader):
        self.animation_phases = animation_phases
        self.async_mode = reader.read_u8() == 0
        self.loop_count = reader.read_s32()
        self.start_phase = reader.read_s8()
        self.phase_durations = []
        for _ in range(self.animation_phases):
            minimum = reader.read_u32()
            maximum = reader.read_u32()
            self.phase_durations.append((minimum, maximum))

    def get_duration_ms(self, phase_index: int, fallback_ms: int) -> int:
        if phase_index < 0 or phase_index >= len(self.phase_durations):
            return fallback_ms
        minimum, maximum = self.phase_durations[phase_index]
        if minimum <= 0 and maximum <= 0:
            return fallback_ms
        if maximum <= 0:
            return max(1, minimum)
        return max(1, (minimum + maximum) // 2)


class DatThingType:
    def __init__(self):
        self.null = True
        self.id = 0
        self.category = DatThingCategory.ThingCategoryItem
        self.attrs: Dict[int, object] = {}
        self.frame_groups: Dict[int, FrameGroup] = {}

    def is_null(self) -> bool:
        return self.null

    def set_attr(self, key: int, value: object):
        self.attrs[key] = value

    def has_attr(self, key: int) -> bool:
        return key in self.attrs

    def is_pickupable(self) -> bool:
        return self.has_attr(DatThingAttr.ThingAttrPickupable)

    def is_stackable(self) -> bool:
        return self.has_attr(DatThingAttr.ThingAttrStackable)

    def get_frame_group(self, group_type: int) -> Optional[FrameGroup]:
        return self.frame_groups.get(group_type)

    def iter_sprite_ids(self):
        for frame_group in self.frame_groups.values():
            for sprite_id in frame_group.sprites_index:
                yield sprite_id


class DatManager:
    def __init__(self, client: Client):
        self.client = client
        self.dat_signature = 0
        self.content_revision = 0
        self.thing_types: List[List[Optional[DatThingType]]] = []
        for _ in range(DatThingCategory.ThingLastCategory):
            self.thing_types.append([])

    def get_category(self, category: int):
        return self.thing_types[category]

    def get_item(self, client_id: int) -> Optional[DatThingType]:
        return self._get_thing_type(client_id, DatThingCategory.ThingCategoryItem)

    def get_outfit(self, client_id: int) -> Optional[DatThingType]:
        return self._get_thing_type(client_id, DatThingCategory.ThingCategoryCreature)

    def get_effect(self, client_id: int) -> Optional[DatThingType]:
        return self._get_thing_type(client_id, DatThingCategory.ThingCategoryEffect)

    def get_missile(self, client_id: int) -> Optional[DatThingType]:
        return self._get_thing_type(client_id, DatThingCategory.ThingCategoryMissile)

    def _get_thing_type(self, client_id: int, category: int) -> Optional[DatThingType]:
        if category >= DatThingCategory.ThingLastCategory:
            return None
        items = self.thing_types[category]
        if client_id < 0 or client_id >= len(items):
            return None
        return items[client_id]

    def load_dat(self, path: Path) -> bool:
        try:
            reader = BinaryReader(path.read_bytes())
            self.dat_signature = reader.read_u32()
            self.content_revision = self.dat_signature & 0xFFFF

            category_counts = [reader.read_u16() + 1 for _ in range(DatThingCategory.ThingLastCategory)]
            self.thing_types = [[] for _ in range(DatThingCategory.ThingLastCategory)]
            self.thing_types[DatThingCategory.ThingCategoryItem] = [None] * category_counts[DatThingCategory.ThingCategoryItem]

            translation = self._client_translation_array()
            category = DatThingCategory.ThingCategoryItem
            first_id = 100
            for client_id in range(first_id, len(self.thing_types[category])):
                thing = DatThingType()
                thing.null = False
                thing.id = client_id
                thing.category = category
                self._unserialize_thing(thing, reader, translation)
                self.thing_types[category][client_id] = thing

            return True
        except Exception as exc:
            raise RuntimeError(f"Failed to read DAT file: {exc}") from exc

    def _client_translation_array(self) -> Dict[int, int]:
        client_attributes_translator: Dict[int, int] = {}
        for thing_attr in range(DatThingAttr.ThingLastAttr):
            client_dat_attribute = thing_attr
            if self.client.version >= 1000:
                if thing_attr == DatThingAttr.ThingAttrNoMoveAnimation:
                    client_dat_attribute = 16
                elif thing_attr >= DatThingAttr.ThingAttrPickupable:
                    client_dat_attribute += 1
            elif self.client.version >= 860:
                pass
            elif self.client.version >= 780:
                if thing_attr == DatThingAttr.ThingAttrChargeable:
                    client_dat_attribute = DatThingAttr.ThingAttrWritable
                elif thing_attr >= DatThingAttr.ThingAttrWritable:
                    client_dat_attribute += 1
            elif self.client.version >= 755:
                if thing_attr == DatThingAttr.ThingAttrFloorChange:
                    client_dat_attribute = 23
            elif self.client.version >= 740:
                if thing_attr > 1 and thing_attr <= 16:
                    thing_attr -= 1
                elif thing_attr == DatThingAttr.ThingAttrLight:
                    thing_attr = 16
                elif thing_attr == DatThingAttr.ThingAttrFloorChange:
                    thing_attr = 17
                elif thing_attr == DatThingAttr.ThingAttrFullGround:
                    thing_attr = 18
                elif thing_attr == DatThingAttr.ThingAttrElevation:
                    thing_attr = 19
                elif thing_attr == DatThingAttr.ThingAttrDisplacement:
                    thing_attr = 20
                elif thing_attr == DatThingAttr.ThingAttrMinimapColor:
                    thing_attr = 22
                elif thing_attr == DatThingAttr.ThingAttrRotateable:
                    thing_attr = 23
                elif thing_attr == DatThingAttr.ThingAttrLyingCorpse:
                    thing_attr = 24
                elif thing_attr == DatThingAttr.ThingAttrHangable:
                    thing_attr = 25
                elif thing_attr == DatThingAttr.ThingAttrHookSouth:
                    thing_attr = 26
                elif thing_attr == DatThingAttr.ThingAttrHookEast:
                    thing_attr = 27
                elif thing_attr == DatThingAttr.ThingAttrAnimateAlways:
                    thing_attr = 28

                if thing_attr == DatThingAttr.ThingAttrMultiUse:
                    client_dat_attribute = DatThingAttr.ThingAttrForceUse
                elif thing_attr == DatThingAttr.ThingAttrForceUse:
                    client_dat_attribute = DatThingAttr.ThingAttrMultiUse

            client_attributes_translator[client_dat_attribute] = thing_attr

        return dict(sorted(client_attributes_translator.items()))

    def _unserialize_thing(self, thing: DatThingType, reader: BinaryReader, translation: Dict[int, int]):
        count = 0
        done = False
        current_attr = -1
        while count < DatThingAttr.ThingLastAttr:
            count += 1
            current_attr = reader.read_u8()
            if current_attr == DatThingAttr.ThingLastAttr:
                done = True
                break

            thing_attr = translation.get(current_attr, current_attr)

            if thing_attr == DatThingAttr.ThingAttrDisplacement:
                if self.client.version >= 755:
                    thing.set_attr(thing_attr, (reader.read_u16(), reader.read_u16()))
                else:
                    thing.set_attr(thing_attr, (8, 8))
            elif thing_attr == DatThingAttr.ThingAttrLight:
                thing.set_attr(thing_attr, (reader.read_u16(), reader.read_u16()))
            elif thing_attr == DatThingAttr.ThingAttrMarket:
                thing.set_attr(
                    thing_attr,
                    (
                        reader.read_u16(),
                        reader.read_u16(),
                        reader.read_u16(),
                        reader.read_string(),
                        reader.read_u16(),
                        reader.read_u16(),
                    ),
                )
            elif thing_attr == DatThingAttr.ThingAttrBones:
                thing.set_attr(thing_attr, tuple(reader.read_u16() for _ in range(8)))
            elif thing_attr in (
                DatThingAttr.ThingAttrElevation,
                DatThingAttr.ThingAttrUsable,
                DatThingAttr.ThingAttrGround,
                DatThingAttr.ThingAttrWritable,
                DatThingAttr.ThingAttrWritableOnce,
                DatThingAttr.ThingAttrMinimapColor,
                DatThingAttr.ThingAttrCloth,
                DatThingAttr.ThingAttrLensHelp,
            ):
                thing.set_attr(thing_attr, reader.read_u16())
            else:
                thing.set_attr(thing_attr, True)

        if not done:
            raise RuntimeError(f"Corrupt DAT data at thing {thing.id}, attr {current_attr}")

        has_frame_groups = thing.category == DatThingCategory.ThingCategoryCreature and self.client.get_feature(GameFeature.GameIdleAnimations)
        group_count = reader.read_u8() if has_frame_groups else 1

        for _ in range(group_count):
            group_type = FrameGroupType.FrameGroupMoving if thing.category == DatThingCategory.ThingCategoryCreature else FrameGroupType.FrameGroupIdle
            if has_frame_groups:
                group_type = reader.read_u8()

            frame_group = FrameGroup()
            frame_group.width = reader.read_u8()
            frame_group.height = reader.read_u8()
            if frame_group.width > 1 or frame_group.height > 1:
                frame_group.real_size = reader.read_u8()
            frame_group.layers = reader.read_u8()
            frame_group.pattern_x = reader.read_u8()
            frame_group.pattern_y = reader.read_u8()
            frame_group.pattern_z = reader.read_u8() if self.client.version >= 755 else 1
            frame_group.animation_phases = reader.read_u8()

            if frame_group.animation_phases > 1 and self.client.get_feature(GameFeature.GameEnhancedAnimations):
                frame_group.animator = Animator()
                frame_group.animator.unserialize(frame_group.animation_phases, reader)

            total_sprites = (
                frame_group.width
                * frame_group.height
                * frame_group.layers
                * frame_group.pattern_x
                * frame_group.pattern_y
                * frame_group.pattern_z
                * frame_group.animation_phases
            )

            frame_group.sprites_index = []
            for _ in range(total_sprites):
                sprite_id = reader.read_u32() if self.client.get_feature(GameFeature.GameSpritesU32) else reader.read_u16()
                frame_group.sprites_index.append(sprite_id)

            thing.frame_groups[group_type] = frame_group
