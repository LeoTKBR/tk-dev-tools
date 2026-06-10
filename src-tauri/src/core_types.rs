use std::collections::HashSet;
use std::path::Path;

pub const SPRITE_SIZE: u32 = 32;

pub struct GameFeature;

#[allow(dead_code)]
impl GameFeature {
    pub const GAME_FORMAT_CREATURE_NAME: u32 = 22;
    pub const GAME_PROTOCOL_CHECKSUM: u32 = 1;
    pub const GAME_ACCOUNT_NAMES: u32 = 2;
    pub const GAME_CHALLENGE_ON_LOGIN: u32 = 3;
    pub const GAME_PENALITY_ON_DEATH: u32 = 4;
    pub const GAME_NAME_ON_NPC_TRADE: u32 = 5;
    pub const GAME_DOUBLE_FREE_CAPACITY: u32 = 6;
    pub const GAME_DOUBLE_EXPERIENCE: u32 = 7;
    pub const GAME_TOTAL_CAPACITY: u32 = 8;
    pub const GAME_SKILLS_BASE: u32 = 9;
    pub const GAME_PLAYER_REGENERATION_TIME: u32 = 10;
    pub const GAME_CHANNEL_PLAYER_LIST: u32 = 11;
    pub const GAME_PLAYER_MOUNTS: u32 = 12;
    pub const GAME_ENVIRONMENT_EFFECT: u32 = 13;
    pub const GAME_CREATURE_EMBLEMS: u32 = 14;
    pub const GAME_ITEM_ANIMATION_PHASE: u32 = 15;
    pub const GAME_PLAYER_MARKET: u32 = 17;
    pub const GAME_ATTACK_SEQ: u32 = 32;
    pub const GAME_PLAYER_ADDONS: u32 = 44;
    pub const GAME_PLAYER_STAMINA: u32 = 43;
    pub const GAME_LOOKTYPE_U16: u32 = 42;
    pub const GAME_SPELL_LIST: u32 = 23;
    pub const GAME_MESSAGE_STATEMENTS: u32 = 45;
    pub const GAME_MESSAGE_LEVEL: u32 = 46;
    pub const GAME_NEW_FLUIDS: u32 = 47;
    pub const GAME_PLAYER_STATE_U16: u32 = 48;
    pub const GAME_NEW_OUTFIT_PROTOCOL: u32 = 49;
    pub const GAME_PVP_MODE: u32 = 50;
    pub const GAME_WRITABLE_DATE: u32 = 51;
    pub const GAME_ADDITIONAL_VIP_INFO: u32 = 52;
    pub const GAME_BASE_SKILL_U16: u32 = 53;
    pub const GAME_CREATURE_ICONS: u32 = 54;
    pub const GAME_HIDE_NPC_NAMES: u32 = 55;
    pub const GAME_SPRITES_ALPHA_CHANNEL: u32 = 56;
    pub const GAME_PREMIUM_EXPIRATION: u32 = 57;
    pub const GAME_BROWSE_FIELD: u32 = 58;
    pub const GAME_ENHANCED_ANIMATIONS: u32 = 59;
    pub const GAME_OGL_INFORMATION: u32 = 60;
    pub const GAME_MESSAGE_SIZE_CHECK: u32 = 61;
    pub const GAME_PREVIEW_STATE: u32 = 62;
    pub const GAME_LOGIN_PACKET_ENCRYPTION: u32 = 63;
    pub const GAME_CLIENT_VERSION: u32 = 64;
    pub const GAME_CONTENT_REVISION: u32 = 65;
    pub const GAME_EXPERIENCE_BONUS: u32 = 66;
    pub const GAME_AUTHENTICATOR: u32 = 67;
    pub const GAME_UNJUSTIFIED_POINTS: u32 = 68;
    pub const GAME_SESSION_KEY: u32 = 69;
    pub const GAME_DEATH_TYPE: u32 = 70;
    pub const GAME_IDLE_ANIMATIONS: u32 = 71;
    pub const GAME_INGAME_STORE: u32 = 73;
    pub const GAME_INGAME_STORE_HIGHLIGHTS: u32 = 74;
    pub const GAME_INGAME_STORE_SERVICE_TYPE: u32 = 75;
    pub const GAME_ADDITIONAL_SKILLS: u32 = 76;
    pub const GAME_SPRITES_U32: u32 = 18;
    pub const GAME_PURSE_SLOT: u32 = 21;
    pub const GAME_CLIENT_PING: u32 = 24;
    pub const GAME_OFFLINE_TRAINING_TIME: u32 = 20;
    pub const GAME_LOGIN_PENDING: u32 = 35;
    pub const GAME_NEW_SPEED_LAW: u32 = 36;
    pub const GAME_CONTAINER_PAGINATION: u32 = 40;
    pub const GAME_THING_MARKS: u32 = 41;
    pub const GAME_DOUBLE_SKILLS: u32 = 29;
}

pub struct DatThingCategory;

#[allow(dead_code)]
impl DatThingCategory {
    pub const THING_CATEGORY_ITEM: usize = 0;
    pub const THING_CATEGORY_CREATURE: usize = 1;
    pub const THING_CATEGORY_EFFECT: usize = 2;
    pub const THING_CATEGORY_MISSILE: usize = 3;
    pub const THING_LAST_CATEGORY: usize = 4;
}

pub struct FrameGroupType;

#[allow(dead_code)]
impl FrameGroupType {
    pub const FRAME_GROUP_IDLE: u8 = 0;
    pub const FRAME_GROUP_MOVING: u8 = 1;
}

pub struct DatThingAttr;

#[allow(dead_code)]
impl DatThingAttr {
    pub const THING_ATTR_GROUND: u32 = 0;
    pub const THING_ATTR_GROUND_BORDER: u32 = 1;
    pub const THING_ATTR_ON_BOTTOM: u32 = 2;
    pub const THING_ATTR_ON_TOP: u32 = 3;
    pub const THING_ATTR_CONTAINER: u32 = 4;
    pub const THING_ATTR_STACKABLE: u32 = 5;
    pub const THING_ATTR_FORCE_USE: u32 = 6;
    pub const THING_ATTR_MULTI_USE: u32 = 7;
    pub const THING_ATTR_WRITABLE: u32 = 8;
    pub const THING_ATTR_WRITABLE_ONCE: u32 = 9;
    pub const THING_ATTR_FLUID_CONTAINER: u32 = 10;
    pub const THING_ATTR_SPLASH: u32 = 11;
    pub const THING_ATTR_NOT_WALKABLE: u32 = 12;
    pub const THING_ATTR_NOT_MOVEABLE: u32 = 13;
    pub const THING_ATTR_BLOCK_PROJECTILE: u32 = 14;
    pub const THING_ATTR_NOT_PATHABLE: u32 = 15;
    pub const THING_ATTR_PICKUPABLE: u32 = 16;
    pub const THING_ATTR_HANGABLE: u32 = 17;
    pub const THING_ATTR_HOOK_SOUTH: u32 = 18;
    pub const THING_ATTR_HOOK_EAST: u32 = 19;
    pub const THING_ATTR_ROTATEABLE: u32 = 20;
    pub const THING_ATTR_LIGHT: u32 = 21;
    pub const THING_ATTR_DONT_HIDE: u32 = 22;
    pub const THING_ATTR_TRANSLUCENT: u32 = 23;
    pub const THING_ATTR_DISPLACEMENT: u32 = 24;
    pub const THING_ATTR_ELEVATION: u32 = 25;
    pub const THING_ATTR_LYING_CORPSE: u32 = 26;
    pub const THING_ATTR_ANIMATE_ALWAYS: u32 = 27;
    pub const THING_ATTR_MINIMAP_COLOR: u32 = 28;
    pub const THING_ATTR_LENS_HELP: u32 = 29;
    pub const THING_ATTR_FULL_GROUND: u32 = 30;
    pub const THING_ATTR_LOOK: u32 = 31;
    pub const THING_ATTR_CLOTH: u32 = 32;
    pub const THING_ATTR_MARKET: u32 = 33;
    pub const THING_ATTR_USABLE: u32 = 34;
    pub const THING_ATTR_WRAPABLE: u32 = 35;
    pub const THING_ATTR_UNWRAPABLE: u32 = 36;
    pub const THING_ATTR_TOP_EFFECT: u32 = 37;
    pub const THING_ATTR_BONES: u32 = 38;
    pub const THING_ATTR_OPACITY: u32 = 100;
    pub const THING_ATTR_NOT_PRE_WALKABLE: u32 = 101;
    pub const THING_ATTR_FLOOR_CHANGE: u32 = 252;
    pub const THING_ATTR_NO_MOVE_ANIMATION: u32 = 253;
    pub const THING_ATTR_CHARGEABLE: u32 = 254;
    pub const THING_LAST_ATTR: u32 = 255;
}

#[derive(Clone)]
pub struct BinaryReader {
    data: Vec<u8>,
    pos: usize,
}

#[allow(dead_code)]
impl BinaryReader {
    pub fn new(data: Vec<u8>) -> Self {
        Self { data, pos: 0 }
    }

    pub fn from_path(path: &Path) -> Result<Self, String> {
        std::fs::read(path)
            .map(Self::new)
            .map_err(|err| format!("failed to read {}: {}", path.display(), err))
    }

    pub fn tell(&self) -> usize {
        self.pos
    }

    pub fn seek(&mut self, pos: usize) {
        self.pos = pos;
    }

    pub fn can_read(&self, size: usize) -> bool {
        self.pos + size <= self.data.len()
    }

    fn take(&mut self, size: usize) -> Result<&[u8], String> {
        if !self.can_read(size) {
            return Err("unexpected end of file".to_string());
        }
        let start = self.pos;
        self.pos += size;
        Ok(&self.data[start..start + size])
    }

    pub fn read_u8(&mut self) -> Result<u8, String> {
        Ok(*self.take(1)?.first().ok_or_else(|| "unexpected end of file".to_string())?)
    }

    pub fn read_s8(&mut self) -> Result<i8, String> {
        Ok(i8::from_le_bytes([self.read_u8()?]))
    }

    pub fn read_u16(&mut self) -> Result<u16, String> {
        let bytes = self.take(2)?;
        Ok(u16::from_le_bytes([bytes[0], bytes[1]]))
    }

    pub fn read_u32(&mut self) -> Result<u32, String> {
        let bytes = self.take(4)?;
        Ok(u32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]))
    }

    pub fn read_s32(&mut self) -> Result<i32, String> {
        let bytes = self.take(4)?;
        Ok(i32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]))
    }

    pub fn read_bytes(&mut self, count: usize) -> Result<Vec<u8>, String> {
        Ok(self.take(count)?.to_vec())
    }

    pub fn read_string(&mut self, length: Option<usize>) -> Result<String, String> {
        let len = match length {
            Some(len) if len > 0 => len,
            _ => self.read_u16()? as usize,
        };
        let bytes = self.read_bytes(len)?;
        Ok(String::from_utf8_lossy(&bytes).to_string())
    }
}

pub struct Client {
    pub version: u32,
    features: HashSet<u32>,
}

impl Client {
    pub fn new(version: u32) -> Self {
        Self {
            version,
            features: client_update_features(version),
        }
    }

    pub fn get_feature(&self, feature: u32) -> bool {
        self.features.contains(&feature)
    }
}

pub fn client_update_features(version: u32) -> HashSet<u32> {
    let mut features = HashSet::from([GameFeature::GAME_FORMAT_CREATURE_NAME]);

    let mut enable = |feature| {
        features.insert(feature);
    };

    if version >= 770 {
        enable(GameFeature::GAME_LOOKTYPE_U16);
        enable(GameFeature::GAME_MESSAGE_STATEMENTS);
        enable(GameFeature::GAME_LOGIN_PACKET_ENCRYPTION);
    }
    if version >= 780 {
        enable(GameFeature::GAME_PLAYER_ADDONS);
        enable(GameFeature::GAME_PLAYER_STAMINA);
        enable(GameFeature::GAME_NEW_FLUIDS);
        enable(GameFeature::GAME_MESSAGE_LEVEL);
        enable(GameFeature::GAME_PLAYER_STATE_U16);
        enable(GameFeature::GAME_NEW_OUTFIT_PROTOCOL);
    }
    if version >= 790 {
        enable(GameFeature::GAME_WRITABLE_DATE);
    }
    if version >= 840 {
        enable(GameFeature::GAME_PROTOCOL_CHECKSUM);
        enable(GameFeature::GAME_ACCOUNT_NAMES);
        enable(GameFeature::GAME_DOUBLE_FREE_CAPACITY);
    }
    if version >= 841 {
        enable(GameFeature::GAME_CHALLENGE_ON_LOGIN);
        enable(GameFeature::GAME_MESSAGE_SIZE_CHECK);
    }
    if version >= 854 {
        enable(GameFeature::GAME_CREATURE_EMBLEMS);
    }
    if version >= 860 {
        enable(GameFeature::GAME_ATTACK_SEQ);
    }
    if version >= 862 {
        enable(GameFeature::GAME_PENALITY_ON_DEATH);
    }
    if version >= 870 {
        enable(GameFeature::GAME_DOUBLE_EXPERIENCE);
        enable(GameFeature::GAME_PLAYER_MOUNTS);
        enable(GameFeature::GAME_SPELL_LIST);
    }
    if version >= 910 {
        enable(GameFeature::GAME_NAME_ON_NPC_TRADE);
        enable(GameFeature::GAME_TOTAL_CAPACITY);
        enable(GameFeature::GAME_SKILLS_BASE);
        enable(GameFeature::GAME_PLAYER_REGENERATION_TIME);
        enable(GameFeature::GAME_CHANNEL_PLAYER_LIST);
        enable(GameFeature::GAME_ENVIRONMENT_EFFECT);
        enable(GameFeature::GAME_ITEM_ANIMATION_PHASE);
    }
    if version >= 940 {
        enable(GameFeature::GAME_PLAYER_MARKET);
    }
    if version >= 953 {
        enable(GameFeature::GAME_PURSE_SLOT);
        enable(GameFeature::GAME_CLIENT_PING);
    }
    if version >= 960 {
        enable(GameFeature::GAME_SPRITES_U32);
        enable(GameFeature::GAME_OFFLINE_TRAINING_TIME);
    }
    if version >= 963 {
        enable(GameFeature::GAME_ADDITIONAL_VIP_INFO);
    }
    if version >= 980 {
        enable(GameFeature::GAME_PREVIEW_STATE);
        enable(GameFeature::GAME_CLIENT_VERSION);
    }
    if version >= 981 {
        enable(GameFeature::GAME_LOGIN_PENDING);
        enable(GameFeature::GAME_NEW_SPEED_LAW);
    }
    if version >= 984 {
        enable(GameFeature::GAME_CONTAINER_PAGINATION);
        enable(GameFeature::GAME_BROWSE_FIELD);
    }
    if version >= 1000 {
        enable(GameFeature::GAME_THING_MARKS);
        enable(GameFeature::GAME_PVP_MODE);
    }
    if version >= 1035 {
        enable(GameFeature::GAME_DOUBLE_SKILLS);
        enable(GameFeature::GAME_BASE_SKILL_U16);
    }
    if version >= 1036 {
        enable(GameFeature::GAME_CREATURE_ICONS);
        enable(GameFeature::GAME_HIDE_NPC_NAMES);
    }
    if version >= 1038 {
        enable(GameFeature::GAME_PREMIUM_EXPIRATION);
    }
    if version >= 1050 {
        enable(GameFeature::GAME_ENHANCED_ANIMATIONS);
    }
    if version >= 1053 {
        enable(GameFeature::GAME_UNJUSTIFIED_POINTS);
    }
    if version >= 1054 {
        enable(GameFeature::GAME_EXPERIENCE_BONUS);
    }
    if version >= 1055 {
        enable(GameFeature::GAME_DEATH_TYPE);
    }
    if version >= 1057 {
        enable(GameFeature::GAME_IDLE_ANIMATIONS);
    }
    if version >= 1061 {
        enable(GameFeature::GAME_OGL_INFORMATION);
    }
    if version >= 1071 {
        enable(GameFeature::GAME_CONTENT_REVISION);
    }
    if version >= 1072 {
        enable(GameFeature::GAME_AUTHENTICATOR);
    }
    if version >= 1074 {
        enable(GameFeature::GAME_SESSION_KEY);
    }
    if version >= 1080 {
        enable(GameFeature::GAME_INGAME_STORE);
    }
    if version >= 1092 {
        enable(GameFeature::GAME_INGAME_STORE_SERVICE_TYPE);
    }
    if version >= 1093 {
        enable(GameFeature::GAME_INGAME_STORE_HIGHLIGHTS);
    }
    if version >= 1094 {
        enable(GameFeature::GAME_ADDITIONAL_SKILLS);
    }

    features
}
