use std::path::Path;

use image::{ImageBuffer, Rgba, RgbaImage};

use crate::core_types::{BinaryReader, Client, GameFeature, SPRITE_SIZE};

pub struct Sprite {
    pub image: RgbaImage,
}

pub struct SpriteManager {
    pub client: Client,
    pub signature: u32,
    pub sprites: Vec<Option<Sprite>>,
}

impl SpriteManager {
    pub fn new(client: Client) -> Self {
        Self {
            client,
            signature: 0,
            sprites: Vec::new(),
        }
    }

    pub fn load_spr(&mut self, path: &Path, used_sprite_ids: Option<&std::collections::HashSet<u32>>) -> Result<(), String> {
        let mut reader = BinaryReader::from_path(path)?;
        self.signature = reader.read_u32()?;
        let sprite_count = if self.client.get_feature(GameFeature::GAME_SPRITES_U32) {
            reader.read_u32()? as usize
        } else {
            usize::from(reader.read_u16()?)
        };

        let sprites_offset = reader.tell();
        self.sprites = (0..=sprite_count).map(|_| None).collect();
        let filtered_used: Option<std::collections::HashSet<u32>> = used_sprite_ids.map(|ids| {
            ids.iter()
                .copied()
                .filter(|sprite_id| *sprite_id >= 1 && usize::try_from(*sprite_id).map(|sprite_id| sprite_id <= sprite_count).unwrap_or(false))
                .collect()
        });

        for sprite_id in 1..=sprite_count {
            reader.seek(sprites_offset + (sprite_id - 1) * 4);
            let sprite_address = reader.read_u32()?;
            if sprite_address == 0 || self.sprites[sprite_id].is_some() {
                continue;
            }
            if let Some(used) = &filtered_used {
                if !used.contains(&(sprite_id as u32)) {
                    continue;
                }
            }

            reader.seek(sprite_address as usize);
            self.sprites[sprite_id] = Some(Sprite {
                image: self.read_sprite(&mut reader)?,
            });
        }

        Ok(())
    }

    fn read_sprite(&self, reader: &mut BinaryReader) -> Result<RgbaImage, String> {
        let _ = reader.read_bytes(3)?;
        let pixel_data_size = reader.read_u16()? as usize;
        let use_alpha = self.client.get_feature(GameFeature::GAME_SPRITES_ALPHA_CHANNEL);
        let channels = if use_alpha { 4usize } else { 3usize };
        let mut pixels: Vec<u8> = Vec::with_capacity((SPRITE_SIZE * SPRITE_SIZE * 4) as usize);
        let mut read = 0usize;
        let mut write_pos = 0usize;

        while read < pixel_data_size && write_pos < (SPRITE_SIZE * SPRITE_SIZE * 4) as usize {
            let transparent_pixels = reader.read_u16()? as usize;
            let colored_pixels = reader.read_u16()? as usize;
            read += 4;

            for _ in 0..transparent_pixels {
                pixels.extend_from_slice(&[0, 0, 0, 0]);
                write_pos += 4;
            }

            for _ in 0..colored_pixels {
                let r = reader.read_u8()?;
                let g = reader.read_u8()?;
                let b = reader.read_u8()?;
                let a = if use_alpha { reader.read_u8()? } else { 255 };
                pixels.extend_from_slice(&[r, g, b, a]);
                write_pos += 4;
            }

            read += channels * colored_pixels;
        }

        while write_pos < (SPRITE_SIZE * SPRITE_SIZE * 4) as usize {
            pixels.extend_from_slice(&[0, 0, 0, 0]);
            write_pos += 4;
        }

        ImageBuffer::<Rgba<u8>, Vec<u8>>::from_vec(SPRITE_SIZE, SPRITE_SIZE, pixels)
            .ok_or_else(|| "failed to build sprite image".to_string())
    }

    pub fn get_sprite(&self, sprite_id: u32) -> Option<&Sprite> {
        let index = usize::try_from(sprite_id).ok()?;
        self.sprites.get(index)?.as_ref()
    }
}
