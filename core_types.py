from __future__ import annotations

import struct
from pathlib import Path
from typing import Dict, Optional


SPRITE_SIZE = 32


class GameFeature:
    GameSpritesU32 = 18
    GameSpritesAlphaChannel = 56
    GameEnhancedAnimations = 59
    GameIdleAnimations = 71
    GameFormatCreatureName = 22
    GameLooktypeU16 = 42
    GameMessageStatements = 45
    GameLoginPacketEncryption = 63
    GamePlayerAddons = 44
    GamePlayerStamina = 43
    GameNewFluids = 47
    GameMessageLevel = 46
    GamePlayerStateU16 = 48
    GameNewOutfitProtocol = 49
    GameWritableDate = 51
    GameProtocolChecksum = 1
    GameAccountNames = 2
    GameDoubleFreeCapacity = 6
    GameChallengeOnLogin = 3
    GameMessageSizeCheck = 61
    GameCreatureEmblems = 14
    GameItemAnimationPhase = 15
    GameAttackSeq = 32
    GamePenalityOnDeath = 4
    GameDoubleExperience = 7
    GamePlayerMounts = 12
    GameSpellList = 23
    GameNameOnNpcTrade = 5
    GameTotalCapacity = 8
    GameSkillsBase = 9
    GamePlayerRegenerationTime = 10
    GameChannelPlayerList = 11
    GameEnvironmentEffect = 13
    GamePlayerMarket = 17
    GamePurseSlot = 21
    GameClientPing = 24
    GameOfflineTrainingTime = 20
    GameAdditionalVipInfo = 52
    GamePreviewState = 62
    GameClientVersion = 64
    GameLoginPending = 35
    GameNewSpeedLaw = 36
    GameContainerPagination = 40
    GameBrowseField = 58
    GameThingMarks = 41
    GamePVPMode = 50
    GameDoubleSkills = 29
    GameBaseSkillU16 = 53
    GameCreatureIcons = 54
    GameHideNpcNames = 55
    GamePremiumExpiration = 57
    GameUnjustifiedPoints = 68
    GameExperienceBonus = 66
    GameDeathType = 70
    GameOGLInformation = 60
    GameContentRevision = 65
    GameAuthenticator = 67
    GameSessionKey = 69
    GameIngameStore = 73
    GameIngameStoreServiceType = 75
    GameIngameStoreHighlights = 74
    GameAdditionalSkills = 76


class DatThingCategory:
    ThingCategoryItem = 0
    ThingCategoryCreature = 1
    ThingCategoryEffect = 2
    ThingCategoryMissile = 3
    ThingLastCategory = 4


class FrameGroupType:
    FrameGroupIdle = 0
    FrameGroupMoving = 1


class DatThingAttr:
    ThingAttrGround = 0
    ThingAttrGroundBorder = 1
    ThingAttrOnBottom = 2
    ThingAttrOnTop = 3
    ThingAttrContainer = 4
    ThingAttrStackable = 5
    ThingAttrForceUse = 6
    ThingAttrMultiUse = 7
    ThingAttrWritable = 8
    ThingAttrWritableOnce = 9
    ThingAttrFluidContainer = 10
    ThingAttrSplash = 11
    ThingAttrNotWalkable = 12
    ThingAttrNotMoveable = 13
    ThingAttrBlockProjectile = 14
    ThingAttrNotPathable = 15
    ThingAttrPickupable = 16
    ThingAttrHangable = 17
    ThingAttrHookSouth = 18
    ThingAttrHookEast = 19
    ThingAttrRotateable = 20
    ThingAttrLight = 21
    ThingAttrDontHide = 22
    ThingAttrTranslucent = 23
    ThingAttrDisplacement = 24
    ThingAttrElevation = 25
    ThingAttrLyingCorpse = 26
    ThingAttrAnimateAlways = 27
    ThingAttrMinimapColor = 28
    ThingAttrLensHelp = 29
    ThingAttrFullGround = 30
    ThingAttrLook = 31
    ThingAttrCloth = 32
    ThingAttrMarket = 33
    ThingAttrUsable = 34
    ThingAttrWrapable = 35
    ThingAttrUnwrapable = 36
    ThingAttrTopEffect = 37
    ThingAttrBones = 38
    ThingAttrOpacity = 100
    ThingAttrNotPreWalkable = 101
    ThingAttrFloorChange = 252
    ThingAttrNoMoveAnimation = 253
    ThingAttrChargeable = 254
    ThingLastAttr = 255


class BinaryReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def tell(self) -> int:
        return self.pos

    def seek(self, pos: int) -> None:
        self.pos = pos

    def can_read(self, size: int = 1) -> bool:
        return self.pos + size <= len(self.data)

    def read_u8(self) -> int:
        value = self.data[self.pos]
        self.pos += 1
        return value

    def read_s8(self) -> int:
        value = struct.unpack_from("<b", self.data, self.pos)[0]
        self.pos += 1
        return value

    def read_u16(self) -> int:
        value = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return value

    def read_s16(self) -> int:
        value = struct.unpack_from("<h", self.data, self.pos)[0]
        self.pos += 2
        return value

    def read_u32(self) -> int:
        value = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return value

    def read_s32(self) -> int:
        value = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return value

    def read_bytes(self, count: int) -> bytes:
        value = self.data[self.pos:self.pos + count]
        self.pos += count
        return value

    def read_string(self, length: Optional[int] = None) -> str:
        if length is None or length == 0:
            length = self.read_u16()
        value = self.read_bytes(length)
        return value.decode("latin1", errors="ignore")


def client_update_features(version: int) -> Dict[int, bool]:
    features: Dict[int, bool] = {GameFeature.GameFormatCreatureName: True}

    def enable(feature: int):
        features[feature] = True

    if version >= 770:
        enable(GameFeature.GameLooktypeU16)
        enable(GameFeature.GameMessageStatements)
        enable(GameFeature.GameLoginPacketEncryption)
    if version >= 780:
        enable(GameFeature.GamePlayerAddons)
        enable(GameFeature.GamePlayerStamina)
        enable(GameFeature.GameNewFluids)
        enable(GameFeature.GameMessageLevel)
        enable(GameFeature.GamePlayerStateU16)
        enable(GameFeature.GameNewOutfitProtocol)
    if version >= 790:
        enable(GameFeature.GameWritableDate)
    if version >= 840:
        enable(GameFeature.GameProtocolChecksum)
        enable(GameFeature.GameAccountNames)
        enable(GameFeature.GameDoubleFreeCapacity)
    if version >= 841:
        enable(GameFeature.GameChallengeOnLogin)
        enable(GameFeature.GameMessageSizeCheck)
    if version >= 854:
        enable(GameFeature.GameCreatureEmblems)
    if version >= 860:
        enable(GameFeature.GameAttackSeq)
    if version >= 862:
        enable(GameFeature.GamePenalityOnDeath)
    if version >= 870:
        enable(GameFeature.GameDoubleExperience)
        enable(GameFeature.GamePlayerMounts)
        enable(GameFeature.GameSpellList)
    if version >= 910:
        enable(GameFeature.GameNameOnNpcTrade)
        enable(GameFeature.GameTotalCapacity)
        enable(GameFeature.GameSkillsBase)
        enable(GameFeature.GamePlayerRegenerationTime)
        enable(GameFeature.GameChannelPlayerList)
        enable(GameFeature.GameEnvironmentEffect)
        enable(GameFeature.GameItemAnimationPhase)
    if version >= 940:
        enable(GameFeature.GamePlayerMarket)
    if version >= 953:
        enable(GameFeature.GamePurseSlot)
        enable(GameFeature.GameClientPing)
    if version >= 960:
        enable(GameFeature.GameSpritesU32)
        enable(GameFeature.GameOfflineTrainingTime)
    if version >= 963:
        enable(GameFeature.GameAdditionalVipInfo)
    if version >= 980:
        enable(GameFeature.GamePreviewState)
        enable(GameFeature.GameClientVersion)
    if version >= 981:
        enable(GameFeature.GameLoginPending)
        enable(GameFeature.GameNewSpeedLaw)
    if version >= 984:
        enable(GameFeature.GameContainerPagination)
        enable(GameFeature.GameBrowseField)
    if version >= 1000:
        enable(GameFeature.GameThingMarks)
        enable(GameFeature.GamePVPMode)
    if version >= 1035:
        enable(GameFeature.GameDoubleSkills)
        enable(GameFeature.GameBaseSkillU16)
    if version >= 1036:
        enable(GameFeature.GameCreatureIcons)
        enable(GameFeature.GameHideNpcNames)
    if version >= 1038:
        enable(GameFeature.GamePremiumExpiration)
    if version >= 1050:
        enable(GameFeature.GameEnhancedAnimations)
    if version >= 1053:
        enable(GameFeature.GameUnjustifiedPoints)
    if version >= 1054:
        enable(GameFeature.GameExperienceBonus)
    if version >= 1055:
        enable(GameFeature.GameDeathType)
    if version >= 1057:
        enable(GameFeature.GameIdleAnimations)
    if version >= 1061:
        enable(GameFeature.GameOGLInformation)
    if version >= 1071:
        enable(GameFeature.GameContentRevision)
    if version >= 1072:
        enable(GameFeature.GameAuthenticator)
    if version >= 1074:
        enable(GameFeature.GameSessionKey)
    if version >= 1080:
        enable(GameFeature.GameIngameStore)
    if version >= 1092:
        enable(GameFeature.GameIngameStoreServiceType)
    if version >= 1093:
        enable(GameFeature.GameIngameStoreHighlights)
    if version >= 1094:
        enable(GameFeature.GameAdditionalSkills)

    return features


class Client:
    def __init__(self, version: int):
        self.version = version
        self.features = client_update_features(version)

    def get_feature(self, feature: int) -> bool:
        return self.features.get(feature, False)
