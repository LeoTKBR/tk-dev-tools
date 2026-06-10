use std::fs::File;
use std::io::BufWriter;
use std::path::Path;
use std::time::Duration;

use image::codecs::gif::{GifEncoder, Repeat};
use image::imageops::overlay;
use image::{Delay, Frame, RgbaImage};

use crate::core_types::{DatThingCategory, FrameGroupType, SPRITE_SIZE};
use crate::dat::{DatManager, DatThingType, FrameGroup};
use crate::spr::SpriteManager;

pub fn render_item_frame(frame_group: &FrameGroup, sprite_manager: &SpriteManager, x: u8, y: u8, z: u8, animation_frame: u8) -> Result<RgbaImage, String> {
    let width_px = u32::from(SPRITE_SIZE) * u32::from(frame_group.width.max(1));
    let height_px = u32::from(SPRITE_SIZE) * u32::from(frame_group.height.max(1));
    let mut result = RgbaImage::new(width_px, height_px);

    for layer in 0..frame_group.layers.max(1) {
        for w in 0..frame_group.width.max(1) {
            for h in 0..frame_group.height.max(1) {
                let sprite_index = frame_group.get_sprite_index(w, h, layer, x, y, z, animation_frame)?;
                let sprite_id = frame_group.sprites_index[sprite_index];
                if let Some(sprite) = sprite_manager.get_sprite(sprite_id) {
                    let dest_x = u32::from(SPRITE_SIZE) * u32::from(frame_group.width.max(1) - w - 1);
                    let dest_y = u32::from(SPRITE_SIZE) * u32::from(frame_group.height.max(1) - h - 1);
                    overlay(&mut result, &sprite.image, i64::from(dest_x), i64::from(dest_y));
                }
            }
        }
    }

    Ok(result)
}

pub fn build_item_frames(thing: &DatThingType, sprite_manager: &SpriteManager, fallback_duration_ms: u32) -> Result<(Vec<RgbaImage>, Vec<u32>), String> {
    let frame_group = match thing.get_frame_group(FrameGroupType::FRAME_GROUP_IDLE) {
        Some(frame_group) => frame_group,
        None => return Ok((Vec::new(), Vec::new())),
    };

    let mut frames: Vec<RgbaImage> = Vec::new();
    let mut durations: Vec<u32> = Vec::new();

    if thing.is_stackable() && frame_group.pattern_x == 4 && frame_group.pattern_y == 2 {
        for pattern_y in 0..frame_group.pattern_y {
            for pattern_x in 0..frame_group.pattern_x {
                frames.push(render_item_frame(frame_group, sprite_manager, pattern_x, pattern_y, 0, 0)?);
                durations.push(fallback_duration_ms);
            }
        }
    } else {
        for animation_frame in 0..frame_group.animation_phases.max(1) {
            frames.push(render_item_frame(frame_group, sprite_manager, 0, 0, 0, animation_frame)?);
            let duration = frame_group
                .animator
                .as_ref()
                .map(|animator| animator.get_duration_ms(usize::from(animation_frame), fallback_duration_ms))
                .unwrap_or(fallback_duration_ms);
            durations.push(duration);
        }
    }

    Ok((frames, durations))
}

pub fn save_gif(frames: &[RgbaImage], out_path: &Path, durations_ms: &[u32]) -> Result<(), String> {
    if frames.is_empty() {
        return Ok(());
    }

    if let Some(parent) = out_path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|err| format!("failed to create {}: {}", parent.display(), err))?;
    }

    let file = File::create(out_path)
        .map_err(|err| format!("failed to create {}: {}", out_path.display(), err))?;
    let mut encoder = GifEncoder::new(BufWriter::new(file));
    encoder
        .set_repeat(Repeat::Infinite)
        .map_err(|err| format!("failed to set gif repeat: {}", err))?;

    for (index, frame) in frames.iter().enumerate() {
        let duration = durations_ms.get(index).copied().unwrap_or(100);
        let delay = Delay::from_saturating_duration(Duration::from_millis(u64::from(duration)));
        let gif_frame = Frame::from_parts(frame.clone(), 0, 0, delay);
        encoder
            .encode_frame(gif_frame)
            .map_err(|err| format!("failed to encode gif frame: {}", err))?;
    }

    Ok(())
}

pub fn build_jobs(
    dat: &DatManager,
    only_pickable: bool,
    start_id: Option<u32>,
    end_id: Option<u32>,
) -> Vec<(u32, u32)> {
    let items = dat.get_category(DatThingCategory::THING_CATEGORY_ITEM);
    if items.len() <= 100 {
        return Vec::new();
    }

    let first_id = start_id.unwrap_or(100).max(100);
    let last_id = end_id.unwrap_or((items.len() - 1) as u32).min((items.len() - 1) as u32);
    if last_id < first_id {
        return Vec::new();
    }

    let mut jobs = Vec::new();
    for client_id in first_id..=last_id {
        let item = items.get(client_id as usize).and_then(|thing| thing.as_ref());
        let Some(thing) = item else {
            continue;
        };
        if thing.is_null() {
            continue;
        }
        if only_pickable && !thing.is_pickupable() {
            continue;
        }
        jobs.push((client_id, client_id));
    }

    jobs
}

pub fn collect_used_sprite_ids(dat: &DatManager, jobs: &[(u32, u32)]) -> std::collections::HashSet<u32> {
    let mut used_sprite_ids = std::collections::HashSet::new();
    for &(_, client_id) in jobs {
        if let Some(thing) = dat.get_item(client_id) {
            if thing.is_null() {
                continue;
            }
            for sprite_id in thing.iter_sprite_ids() {
                if sprite_id != 0 {
                    used_sprite_ids.insert(sprite_id);
                }
            }
        }
    }
    used_sprite_ids
}

pub fn is_blank_frame(image: &RgbaImage) -> bool {
    image.pixels().all(|pixel| pixel.0[3] == 0)
}
