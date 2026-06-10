use std::collections::{HashMap, HashSet};
use std::path::Path;

use crate::core_types::{BinaryReader, Client, DatThingAttr, DatThingCategory, FrameGroupType, GameFeature};

#[derive(Clone, Debug)]
pub struct FrameGroup {
    pub width: u8,
    pub height: u8,
    pub real_size: u8,
    pub layers: u8,
    pub pattern_x: u8,
    pub pattern_y: u8,
    pub pattern_z: u8,
    pub animation_phases: u8,
    pub animator: Option<Animator>,
    pub sprites_index: Vec<u32>,
}

impl FrameGroup {
    pub fn new() -> Self {
        Self {
            width: 0,
            height: 0,
            real_size: 0,
            layers: 0,
            pattern_x: 0,
            pattern_y: 0,
            pattern_z: 0,
            animation_phases: 0,
            animator: None,
            sprites_index: Vec::new(),
        }
    }

    pub fn get_sprite_index(&self, w: u8, h: u8, l: u8, x: u8, y: u8, z: u8, a: u8) -> Result<usize, String> {
        let animation_phases = usize::from(self.animation_phases.max(1));
        let index = ((((((usize::from(a) % animation_phases) * usize::from(self.pattern_z.max(1)) + usize::from(z))
            * usize::from(self.pattern_y.max(1))
            + usize::from(y))
            * usize::from(self.pattern_x.max(1))
            + usize::from(x))
            * usize::from(self.layers.max(1))
            + usize::from(l))
            * usize::from(self.height.max(1))
            + usize::from(h))
            * usize::from(self.width.max(1))
            + usize::from(w);

        if index >= self.sprites_index.len() {
            return Err("sprite index out of range".to_string());
        }

        Ok(index)
    }
}

#[derive(Clone, Debug)]
pub struct Animator {
    pub animation_phases: u8,
    pub start_phase: i8,
    pub loop_count: i32,
    pub async_mode: bool,
    pub phase_durations: Vec<(u32, u32)>,
}

impl Animator {
    pub fn new() -> Self {
        Self {
            animation_phases: 0,
            start_phase: 0,
            loop_count: 0,
            async_mode: false,
            phase_durations: Vec::new(),
        }
    }

    pub fn unserialize(&mut self, animation_phases: u8, reader: &mut BinaryReader) -> Result<(), String> {
        self.animation_phases = animation_phases;
        self.async_mode = reader.read_u8()? == 0;
        self.loop_count = reader.read_s32()?;
        self.start_phase = reader.read_s8()?;
        self.phase_durations.clear();

        for _ in 0..self.animation_phases {
            let minimum = reader.read_u32()?;
            let maximum = reader.read_u32()?;
            self.phase_durations.push((minimum, maximum));
        }

        Ok(())
    }

    pub fn get_duration_ms(&self, phase_index: usize, fallback_ms: u32) -> u32 {
        if phase_index >= self.phase_durations.len() {
            return fallback_ms;
        }

        let (minimum, maximum) = self.phase_durations[phase_index];
        if minimum == 0 && maximum == 0 {
            return fallback_ms;
        }
        if maximum == 0 {
            return minimum.max(1);
        }
        ((minimum + maximum) / 2).max(1)
    }
}

#[derive(Clone, Debug)]
pub struct DatThingType {
    pub null: bool,
    pub id: u32,
    pub category: usize,
    attrs: HashSet<u32>,
    pub frame_groups: HashMap<u8, FrameGroup>,
}

impl DatThingType {
    pub fn new() -> Self {
        Self {
            null: true,
            id: 0,
            category: DatThingCategory::THING_CATEGORY_ITEM,
            attrs: HashSet::new(),
            frame_groups: HashMap::new(),
        }
    }

    pub fn is_null(&self) -> bool {
        self.null
    }

    pub fn set_attr(&mut self, key: u32) {
        self.attrs.insert(key);
    }

    pub fn has_attr(&self, key: u32) -> bool {
        self.attrs.contains(&key)
    }

    pub fn is_pickupable(&self) -> bool {
        self.has_attr(DatThingAttr::THING_ATTR_PICKUPABLE)
    }

    pub fn is_stackable(&self) -> bool {
        self.has_attr(DatThingAttr::THING_ATTR_STACKABLE)
    }

    pub fn get_frame_group(&self, group_type: u8) -> Option<&FrameGroup> {
        self.frame_groups.get(&group_type)
    }

    pub fn iter_sprite_ids(&self) -> impl Iterator<Item = u32> + '_ {
        self.frame_groups.values().flat_map(|frame_group| frame_group.sprites_index.iter().copied())
    }
}

pub struct DatManager {
    pub client: Client,
    pub dat_signature: u32,
    pub content_revision: u32,
    pub thing_types: Vec<Vec<Option<DatThingType>>>,
}

impl DatManager {
    pub fn new(client: Client) -> Self {
        Self {
            client,
            dat_signature: 0,
            content_revision: 0,
            thing_types: (0..DatThingCategory::THING_LAST_CATEGORY).map(|_| Vec::new()).collect(),
        }
    }

    pub fn get_category(&self, category: usize) -> &Vec<Option<DatThingType>> {
        &self.thing_types[category]
    }

    pub fn get_item(&self, client_id: u32) -> Option<&DatThingType> {
        self.get_thing_type(client_id, DatThingCategory::THING_CATEGORY_ITEM)
    }

    fn get_thing_type(&self, client_id: u32, category: usize) -> Option<&DatThingType> {
        let items = self.thing_types.get(category)?;
        let index = usize::try_from(client_id).ok()?;
        items.get(index)?.as_ref()
    }

    pub fn load_dat(&mut self, path: &Path) -> Result<(), String> {
        let mut reader = BinaryReader::from_path(path)?;
        self.dat_signature = reader.read_u32()?;
        self.content_revision = self.dat_signature & 0xFFFF;

        let category_counts: Vec<usize> = (0..DatThingCategory::THING_LAST_CATEGORY)
            .map(|_| reader.read_u16().map(|value| usize::from(value) + 1))
            .collect::<Result<Vec<_>, _>>()?;

        self.thing_types = (0..DatThingCategory::THING_LAST_CATEGORY)
            .map(|_| Vec::new())
            .collect();
        self.thing_types[DatThingCategory::THING_CATEGORY_ITEM] = vec![None; category_counts[DatThingCategory::THING_CATEGORY_ITEM]];

        let translation = self.client_translation_array();
        let category = DatThingCategory::THING_CATEGORY_ITEM;
        let first_id = 100usize;
        let item_len = self.thing_types[category].len();

        for client_id in first_id..item_len {
            let mut thing = DatThingType::new();
            thing.null = false;
            thing.id = client_id as u32;
            thing.category = category;
            self.unserialize_thing(&mut thing, &mut reader, &translation)?;
            self.thing_types[category][client_id] = Some(thing);
        }

        Ok(())
    }

    fn client_translation_array(&self) -> HashMap<u32, u32> {
        let mut client_attributes_translator: HashMap<u32, u32> = HashMap::new();

        for thing_attr in 0..DatThingAttr::THING_LAST_ATTR {
            let mut thing_attr = thing_attr;
            let mut client_dat_attribute = thing_attr;

            if self.client.version >= 1000 {
                if thing_attr == DatThingAttr::THING_ATTR_NO_MOVE_ANIMATION {
                    client_dat_attribute = 16;
                } else if thing_attr >= DatThingAttr::THING_ATTR_PICKUPABLE {
                    client_dat_attribute += 1;
                }
            } else if self.client.version >= 860 {
            } else if self.client.version >= 780 {
                if thing_attr == DatThingAttr::THING_ATTR_CHARGEABLE {
                    client_dat_attribute = DatThingAttr::THING_ATTR_WRITABLE;
                } else if thing_attr >= DatThingAttr::THING_ATTR_WRITABLE {
                    client_dat_attribute += 1;
                }
            } else if self.client.version >= 755 {
                if thing_attr == DatThingAttr::THING_ATTR_FLOOR_CHANGE {
                    client_dat_attribute = 23;
                }
            } else if self.client.version >= 740 {
                if thing_attr > 1 && thing_attr <= 16 {
                    thing_attr -= 1;
                } else if thing_attr == DatThingAttr::THING_ATTR_LIGHT {
                    thing_attr = 16;
                } else if thing_attr == DatThingAttr::THING_ATTR_FLOOR_CHANGE {
                    thing_attr = 17;
                } else if thing_attr == DatThingAttr::THING_ATTR_FULL_GROUND {
                    thing_attr = 18;
                } else if thing_attr == DatThingAttr::THING_ATTR_ELEVATION {
                    thing_attr = 19;
                } else if thing_attr == DatThingAttr::THING_ATTR_DISPLACEMENT {
                    thing_attr = 20;
                } else if thing_attr == DatThingAttr::THING_ATTR_MINIMAP_COLOR {
                    thing_attr = 22;
                } else if thing_attr == DatThingAttr::THING_ATTR_ROTATEABLE {
                    thing_attr = 23;
                } else if thing_attr == DatThingAttr::THING_ATTR_LYING_CORPSE {
                    thing_attr = 24;
                } else if thing_attr == DatThingAttr::THING_ATTR_HANGABLE {
                    thing_attr = 25;
                } else if thing_attr == DatThingAttr::THING_ATTR_HOOK_SOUTH {
                    thing_attr = 26;
                } else if thing_attr == DatThingAttr::THING_ATTR_HOOK_EAST {
                    thing_attr = 27;
                } else if thing_attr == DatThingAttr::THING_ATTR_ANIMATE_ALWAYS {
                    thing_attr = 28;
                }

                if thing_attr == DatThingAttr::THING_ATTR_MULTI_USE {
                    client_dat_attribute = DatThingAttr::THING_ATTR_FORCE_USE;
                } else if thing_attr == DatThingAttr::THING_ATTR_FORCE_USE {
                    client_dat_attribute = DatThingAttr::THING_ATTR_MULTI_USE;
                }
            }

            client_attributes_translator.insert(client_dat_attribute, thing_attr);
        }

        client_attributes_translator
    }

    fn unserialize_thing(
        &self,
        thing: &mut DatThingType,
        reader: &mut BinaryReader,
        translation: &HashMap<u32, u32>,
    ) -> Result<(), String> {
        let mut count = 0u32;
        let mut done = false;
        let mut current_attr = 0u32;

        while count < DatThingAttr::THING_LAST_ATTR {
            count += 1;
            current_attr = u32::from(reader.read_u8()?);
            if current_attr == DatThingAttr::THING_LAST_ATTR {
                done = true;
                break;
            }

            let thing_attr = translation.get(&current_attr).copied().unwrap_or(current_attr);

            if thing_attr == DatThingAttr::THING_ATTR_DISPLACEMENT {
                if self.client.version >= 755 {
                    let _ = reader.read_u16()?;
                    let _ = reader.read_u16()?;
                }
                thing.set_attr(thing_attr);
            } else if thing_attr == DatThingAttr::THING_ATTR_LIGHT {
                let _ = reader.read_u16()?;
                let _ = reader.read_u16()?;
                thing.set_attr(thing_attr);
            } else if thing_attr == DatThingAttr::THING_ATTR_MARKET {
                let _ = reader.read_u16()?;
                let _ = reader.read_u16()?;
                let _ = reader.read_u16()?;
                let _ = reader.read_string(None)?;
                let _ = reader.read_u16()?;
                let _ = reader.read_u16()?;
                thing.set_attr(thing_attr);
            } else if thing_attr == DatThingAttr::THING_ATTR_BONES {
                for _ in 0..8 {
                    let _ = reader.read_u16()?;
                }
                thing.set_attr(thing_attr);
            } else if matches!(
                thing_attr,
                DatThingAttr::THING_ATTR_ELEVATION
                    | DatThingAttr::THING_ATTR_USABLE
                    | DatThingAttr::THING_ATTR_GROUND
                    | DatThingAttr::THING_ATTR_WRITABLE
                    | DatThingAttr::THING_ATTR_WRITABLE_ONCE
                    | DatThingAttr::THING_ATTR_MINIMAP_COLOR
                    | DatThingAttr::THING_ATTR_CLOTH
                    | DatThingAttr::THING_ATTR_LENS_HELP
            ) {
                let _ = reader.read_u16()?;
                thing.set_attr(thing_attr);
            } else {
                thing.set_attr(thing_attr);
            }
        }

        if !done {
            return Err(format!("corrupt DAT data at thing {}, attr {}", thing.id, current_attr));
        }

        let has_frame_groups = thing.category == DatThingCategory::THING_CATEGORY_CREATURE
            && self.client.get_feature(GameFeature::GAME_IDLE_ANIMATIONS);
        let group_count = if has_frame_groups {
            usize::from(reader.read_u8()?)
        } else {
            1
        };

        for _ in 0..group_count {
            let mut group_type = if thing.category == DatThingCategory::THING_CATEGORY_CREATURE {
                FrameGroupType::FRAME_GROUP_MOVING
            } else {
                FrameGroupType::FRAME_GROUP_IDLE
            };

            if has_frame_groups {
                group_type = reader.read_u8()?;
            }

            let mut frame_group = FrameGroup::new();
            frame_group.width = reader.read_u8()?;
            frame_group.height = reader.read_u8()?;
            if frame_group.width > 1 || frame_group.height > 1 {
                frame_group.real_size = reader.read_u8()?;
            }
            frame_group.layers = reader.read_u8()?;
            frame_group.pattern_x = reader.read_u8()?;
            frame_group.pattern_y = reader.read_u8()?;
            frame_group.pattern_z = if self.client.version >= 755 { reader.read_u8()? } else { 1 };
            frame_group.animation_phases = reader.read_u8()?;

            if frame_group.animation_phases > 1 && self.client.get_feature(GameFeature::GAME_ENHANCED_ANIMATIONS) {
                let mut animator = Animator::new();
                animator.unserialize(frame_group.animation_phases, reader)?;
                frame_group.animator = Some(animator);
            }

            let total_sprites = usize::from(frame_group.width)
                * usize::from(frame_group.height)
                * usize::from(frame_group.layers)
                * usize::from(frame_group.pattern_x)
                * usize::from(frame_group.pattern_y)
                * usize::from(frame_group.pattern_z)
                * usize::from(frame_group.animation_phases);

            frame_group.sprites_index.clear();
            for _ in 0..total_sprites {
                let sprite_id = if self.client.get_feature(GameFeature::GAME_SPRITES_U32) {
                    reader.read_u32()?
                } else {
                    u32::from(reader.read_u16()?)
                };
                frame_group.sprites_index.push(sprite_id);
            }

            thing.frame_groups.insert(group_type, frame_group);
        }

        Ok(())
    }
}
