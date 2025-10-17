"""Reference data for ability feature templates and UI pickers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional
import copy


@dataclass(frozen=True)
class FeatureScope:
    key: str
    label: str
    description: str


@dataclass(frozen=True)
class FeatureBlock:
    key: str
    label: str
    description: str


@dataclass
class AbilityTemplate:
    template_id: str
    target_type: str
    label: str
    description: str
    scope_key: str
    block_sequence: List[str]
    body: str
    placeholders: Mapping[str, str]
    example: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "template_id": self.template_id,
            "target_type": self.target_type,
            "label": self.label,
            "description": self.description,
            "scope_key": self.scope_key,
            "block_sequence": list(self.block_sequence),
            "body": self.body,
            "placeholders": dict(self.placeholders),
            "example": self.example,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "AbilityTemplate":
        return cls(
            template_id=str(data.get("template_id", "custom")),
            target_type=str(data.get("target_type", "")),
            label=str(data.get("label", "Unnamed template")),
            description=str(data.get("description", "")),
            scope_key=str(data.get("scope_key", "Ability")),
            block_sequence=list(data.get("block_sequence", [])),
            body=str(data.get("body", "")),
            placeholders=dict(data.get("placeholders", {})),
            example=data.get("example"),
            notes=data.get("notes"),
        )


ABILITY_TYPES: Mapping[str, Dict[str, str]] = {
    "SA": {
        "label": "Support Ability (SA)",
        "tooltip": (
            "Standard support ability learned via gear. Matches the entries in "
            "Memoria's Supporting Ability wiki."),
        "example": (
            "EXAMPLE:\n"
            ">SA 0 ~~ Auto-Shell or Auto-Protect ~~\n"
            "StatusInit [code=Condition] Defence <= MagicDefence [/code] AutoStatus Protect\n"
            "StatusInit [code=Condition] MagicDefence <= Defence [/code] AutoStatus Shell\n"
            "# Applies whichever auto-status best matches the current defences."),
    },
    "SA_GLOBAL": {
        "label": "Support Ability Global (SA Global+)",
        "tooltip": (
            "Global hook that always runs once per character. Often used for "
            "equipment or chain logic."),
        "example": (
            "EXAMPLE:\n"
            ">SA Global+ ~~ Weapon-based effects bundle ~~\n"
            "StatusInit [code=Condition] WeaponId == RegularItem_Avenger [/code] InitialStatus Doom\n"
            "Ability AsTarget\n"
            "[code=Condition] TargetWeaponId == RegularItem_Defender && CheckAnyStatus(TargetCurrentStatus, BattleStatus_Defend) && IsCounterableCommand && CasterIsPlayer != TargetIsPlayer && (AbilityCategory & 8) != 0 [/code]\n"
            "[code=Counter] BattleAbilityId_Attack [/code]\n"
            "# Layers weapon passives regardless of the equipped support ability."),
    },
    "SA_GLOBAL_LAST": {
        "label": "Support Ability Global Last (SA GlobalLast+)",
        "tooltip": (
            "Runs after all other SA Global entries. Ideal for final stat overrides "
            "like armour bonuses."),
        "example": (
            "EXAMPLE:\n"
            ">SA GlobalLast+ ~~ Lapiz Lazuli MP bonus ~~\n"
            "Ability EvenImmobilized\n"
            "[code=Condition] AccessoryId == 610 [/code]\n"
            "[code=MaxMP] MaxMP + 30 [/code]\n"
            "# Runs after other global hooks to enforce the final MP bonus."),
    },
    "SA_GLOBAL_ENEMY": {
        "label": "Support Ability Global Enemy (SA GlobalEnemy+)",
        "tooltip": (
            "Applies global hooks to enemy actors. Useful for damage scaling or global debuffs."),
        "example": (
            "EXAMPLE:\n"
            ">SA GlobalEnemy+ ~~ Player damage taken scaler ~~\n"
            "Ability WhenCalcDamage EvenImmobilized\n"
            "[code=AttackPower] Min((AttackPower * 2), (AttackPower * (1 + (TargetLevel/50)))) [/code]\n"
            "# Increases damage enemies deal based on the player's level."),
    },
    "AA": {
        "label": "Active Ability (AA)",
        "tooltip": (
            "Battle commands (spells, skills, summons). Individual ability IDs."),
        "example": (
            "EXAMPLE:\n"
            ">AA 11 ~~ Shell upgrades with Concentrate ~~\n"
            "[code=Patch] HasSA(33) ? BattleAbilityId_MightyGuard : -1 [/code]\n"
            "# Concentrate swaps Shell into Mighty Guard."),
    },
    "AA_GLOBAL": {
        "label": "Active Ability Global (AA Global+)",
        "tooltip": (
            "Global hook for every active ability. Use for system-wide tweaks like "
            "MP discounts."),
        "example": (
            "EXAMPLE:\n"
            ">AA Global+ ~~ Trance MP discount ~~\n"
            "[code=Condition] CheckAnyStatus(CasterCurrentStatus, BattleStatus_Trance) [/code]\n"
            "[code=MPCost] MPCost * 0.75 [/code]\n"
            "# Lowers MP cost for command sets while in Trance."),
    },
}


SA_SCOPES: List[FeatureScope] = [
    FeatureScope(
        key="Permanent",
        label="Permanent",
        description="Applied on equipment refresh. Ideal for stat tweaks or unlock checks.",
    ),
    FeatureScope(
        key="BattleStart",
        label="BattleStart",
        description="Executes when a battle begins (preemptive/back-attack logic).",
    ),
    FeatureScope(
        key="StatusInit",
        label="StatusInit",
        description="Applies statuses right after battle initialisation.",
    ),
    FeatureScope(
        key="Ability",
        label="Ability",
        description="Runs every time the attached ability participates in battle logic.",
    ),
    FeatureScope(
        key="Command",
        label="Command",
        description="Alters command behaviour before execution (targeting, reach, etc.).",
    ),
    FeatureScope(
        key="BattleResult",
        label="BattleResult",
        description="Applies when battle rewards are calculated (bonus AP, drops, etc.).",
    ),
]

SA_GLOBAL_SCOPES: List[FeatureScope] = [
    FeatureScope(
        key="Permanent",
        label="Permanent",
        description="Initialises once per character regardless of equipped SAs.",
    ),
    FeatureScope(
        key="StatusInit",
        label="StatusInit",
        description="Applies statuses at battle start even without the SA equipped.",
    ),
    FeatureScope(
        key="Ability",
        label="Ability",
        description="Battle-time hook available to all characters for global logic.",
    ),
    FeatureScope(
        key="Command",
        label="Command",
        description="Adjusts command behaviour globally before execution.",
    ),
]

SA_GLOBAL_LAST_SCOPES: List[FeatureScope] = [
    FeatureScope(
        key="Ability",
        label="Ability",
        description="Final pass after standard SA Global; useful for overriding earlier changes.",
    ),
    FeatureScope(
        key="Command",
        label="Command",
        description="Final command tweaks after other global logic has run.",
    ),
]

SA_GLOBAL_ENEMY_SCOPES: List[FeatureScope] = [
    FeatureScope(
        key="Ability",
        label="Ability",
        description="Runs for enemy actors during ability processing.",
    ),
]

AA_SCOPES: List[FeatureScope] = [
    FeatureScope(
        key="Ability",
        label="Ability",
        description="Runs with the ability's effect (WhenCalcDamage, WhenEffectDone, etc.).",
    ),
    FeatureScope(
        key="Command",
        label="Command",
        description="Adjusts menu entry behaviour before the ability fires (MP, targeting, etc.).",
    ),
]

AA_GLOBAL_SCOPES: List[FeatureScope] = [
    FeatureScope(
        key="Ability",
        label="Ability",
        description="Global battle hook for every active ability.",
    ),
]


FEATURE_BLOCKS: Mapping[str, FeatureBlock] = {
    "Condition": FeatureBlock(
        key="Condition",
        label="Condition",
        description="Boolean gate that must be true for the other blocks to execute.",
    ),
    "HardDisable": FeatureBlock(
        key="HardDisable",
        label="Hard Disable",
        description="Hides the entry entirely while the expression is true.",
    ),
    "Disable": FeatureBlock(
        key="Disable",
        label="Disable",
        description="Greys out the command but leaves it visible.",
    ),
    "Patch": FeatureBlock(
        key="Patch",
        label="Patch",
        description="Rewrites constants such as AbilityId, Target, or MPCost.",
    ),
    "BanishSAByLvl": FeatureBlock(
        key="BanishSAByLvl",
        label="Banish SA By Lv",
        description="Hides support ability tiers until the given rank is reached.",
    ),
    "BanishAAByLvl": FeatureBlock(
        key="BanishAAByLvl",
        label="Banish AA By Lv",
        description="Active ability equivalent of BanishSAByLvl.",
    ),
    "MPCost": FeatureBlock(
        key="MPCost",
        label="MP Cost",
        description="Adjusts the ability's MP consumption on the fly.",
    ),
    "CasterTrance": FeatureBlock(
        key="CasterTrance",
        label="Caster Trance",
        description="Modifies the caster's Trance gauge when the effect ends.",
    ),
    "MaxHP": FeatureBlock(
        key="MaxHP",
        label="Max HP",
        description="Tweaks the character's maximum HP for the duration of the effect.",
    ),
    "MaxMP": FeatureBlock(
        key="MaxMP",
        label="Max MP",
        description="Tweaks the character's maximum MP for the duration of the effect.",
    ),
}


SCOPE_REGISTRY: Mapping[str, List[FeatureScope]] = {
    "SA": SA_SCOPES,
    "SA_GLOBAL": SA_GLOBAL_SCOPES,
    "SA_GLOBAL_LAST": SA_GLOBAL_LAST_SCOPES,
    "SA_GLOBAL_ENEMY": SA_GLOBAL_ENEMY_SCOPES,
    "AA": AA_SCOPES,
    "AA_GLOBAL": AA_GLOBAL_SCOPES,
}


def scopes_for(target_type: str) -> List[FeatureScope]:
    return list(SCOPE_REGISTRY.get(target_type, []))


def blocks_for(keys: List[str]) -> List[FeatureBlock]:
    return [FEATURE_BLOCKS[key] for key in keys if key in FEATURE_BLOCKS]


TEMPLATES: List[AbilityTemplate] = [
    AbilityTemplate(
        template_id="sa_auto_shell_protect",
        target_type="SA",
        label="Auto-Shell or Auto-Protect",
        description="Grants whichever auto-status is more beneficial based on current stats.",
        scope_key="StatusInit",
        block_sequence=["Condition"],
        body=(
            ">SA {sa_id} {comment}\n"
            "StatusInit [code=Condition] Defence <= MagicDefence [/code] AutoStatus Protect\n"
            "StatusInit [code=Condition] MagicDefence <= Defence [/code] AutoStatus Shell\n"
        ),
        placeholders={
            "sa_id": "Support Ability ID you are customising",
            "comment": "Clarify what the ability does",
        },
        example=(
            "##### Example use case #####\n"
            ">SA 0 Auto-Shell or Auto-Protect\n"
            "StatusInit [code=Condition] Defence <= MagicDefence [/code] AutoStatus Protect\n"
            "StatusInit [code=Condition] MagicDefence <= Defence [/code] AutoStatus Shell\n"
            "##### End example #####"
        ),
        notes="Straight from the Supporting Ability wiki page.",
    ),
    AbilityTemplate(
        template_id="sa_battlestart_preemptive",
        target_type="SA",
        label="Battle start odds",
        description="Configures preemptive/back-attack chances and command reach.",
        scope_key="BattleStart",
        block_sequence=["Condition", "Patch"],
        body=(
            ">SA {sa_id} {comment}\n"
            "BattleStart PreemptivePriority +1\n"
            "[code=Preemptive] {preemptive_value} [/code]\n"
            "[code=BackAttack] {backattack_value} [/code]\n"
            "Command EvenImmobilized\n"
            "[code=Condition] IsAllyOfCaster [/code]\n"
            "[code=IsShortRanged] false [/code]\n"
        ),
        placeholders={
            "sa_id": "Support Ability ID",
            "comment": "Describe the behaviour",
            "preemptive_value": "Chance out of 255 for preemptive (eg. 128)",
            "backattack_value": "Chance out of 255 for back attack",
        },
        example=(
            "##### Example use case #####\n"
            ">SA 2 Preemptive setup\n"
            "BattleStart PreemptivePriority +1\n"
            "[code=Preemptive] 128 [/code]\n"
            "[code=BackAttack] 128 [/code]\n"
            "Command EvenImmobilized\n"
            "[code=Condition] IsAllyOfCaster [/code]\n"
            "[code=IsShortRanged] false [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="sa_trance_guard",
        target_type="SA",
        label="Trance safety net",
        description="Consumes Trance to prevent fatal damage and apply statuses.",
        scope_key="Ability",
        block_sequence=["Condition", "CasterTrance"],
        body=(
            ">SA {sa_id} {comment}\n"
            "Ability AsTarget WhenBattleScriptEnd\n"
            "[code=Condition] {fatal_condition} [/code]\n"
            "[code=TranceIncrease] {trance_delta} [/code]\n"
            "[code=TargetPermanentStatus] {status_expression} [/code]\n"
            "[code=HPDamage] 0 [/code]\n"
        ),
        placeholders={
            "sa_id": "Support Ability ID",
            "comment": "Describe the safety behaviour",
            "fatal_condition": "Condition similar to wiki example for fatal damage",
            "trance_delta": "Amount to drain from Trance (negative value)",
            "status_expression": "CombineStatuses call to add statuses",
        },
        example=(
            "##### Example use case #####\n"
            ">SA 1 Last stand\n"
            "Ability AsTarget WhenBattleScriptEnd\n"
            "[code=Condition] HPDamage >= TargetHP && TargetTrance >= 128 && CasterIsPlayer != TargetIsPlayer\n                && (EffectTargetFlags & CalcFlag_HpDamageOrHeal) == CalcFlag_HpAlteration [/code]\n"
            "[code=TranceIncrease] -128 [/code]\n"
            "[code=TargetPermanentStatus] CombineStatuses(TargetPermanentStatus, BattleStatus_Berserk, BattleStatus_Vanish, BattleStatus_Reflect) [/code]\n"
            "[code=HPDamage] 0 [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="sa_penetrator",
        target_type="SA",
        label="Armour penetration",
        description="Reduces enemy defence when the SA holder attacks.",
        scope_key="Ability",
        block_sequence=["Condition", "DefencePower"],
        body=(
            ">SA {sa_id} {comment}\n"
            "Ability WhenCalcDamage EvenImmobilized\n"
            "[code=Condition] {penetration_condition} [/code]\n"
            "[code=DefencePower] DefencePower * {defence_multiplier} [/code]\n"
        ),
        placeholders={
            "sa_id": "Support Ability ID (ex: 12)",
            "comment": "Describe the penetration behaviour",
            "penetration_condition": "Condition for when the penetration applies",
            "defence_multiplier": "Multiplier to apply to DefencePower (ex: 0.95)",
        },
        example=(
            "##### Example use case #####\n"
            ">SA 12 Penetrator ~~All attacks ignore 5% of target defence~~\n"
            "Ability WhenCalcDamage EvenImmobilized\n"
            "[code=Condition] CasterIsPlayer && !TargetIsPlayer && (EffectFlags & (BattleCalcFlags_Miss | BattleCalcFlags_Guard)) == 0 [/code]\n"
            "[code=DefencePower] DefencePower * 0.95 [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="sa_global_weapon_effects",
        target_type="SA_GLOBAL",
        label="Weapon-based global effects",
        description="Chains multiple equipment-driven effects into a single SA Global block.",
        scope_key="Ability",
        block_sequence=["Condition", "Patch"],
        body=(
            ">SA Global+ {global_comment}\n"
            "StatusInit [code=Condition] {weapon_condition} [/code] InitialStatus {initial_status}\n"
            "Ability AsTarget\n"
            "[code=Condition] {counter_condition} [/code]\n"
            "[code=Counter] {counter_ability} [/code]\n"
        ),
        placeholders={
            "global_comment": "Summary of what this global block handles",
            "weapon_condition": "Check for the weapon/equipment ID",
            "initial_status": "Status to apply at battle start",
            "counter_condition": "Condition describing when to counter",
            "counter_ability": "Ability triggered as the counter",
        },
        example=(
            "##### Example use case #####\n"
            ">SA Global+ Weapon specials\n"
            "StatusInit [code=Condition] WeaponId == RegularItem_Avenger [/code] InitialStatus Doom\n"
            "Ability AsTarget\n"
            "[code=Condition] TargetWeaponId == RegularItem_Defender && CheckAnyStatus(TargetCurrentStatus, BattleStatus_Defend) && IsCounterableCommand && CasterIsPlayer != TargetIsPlayer && (AbilityCategory & 8) != 0 [/code]\n"
            "[code=Counter] BattleAbilityId_Attack [/code]\n"
            "##### End example #####"
        ),
        notes="Continue the block with extra weapon checks as needed (Mace of Zeus MP cost, Rosetta Ring, etc.).",
    ),
    AbilityTemplate(
        template_id="sa_global_armor_pen",
        target_type="SA_GLOBAL",
        label="Ability-based armour penetration",
        description="Reduces enemy defence for specific abilities without requiring an SA.",
        scope_key="Ability",
        block_sequence=["Condition", "DefencePower"],
        body=(
            ">SA Global+ {comment}\n"
            "Ability WhenCalcDamage EvenImmobilized\n"
            "[code=Condition] {ability_condition} [/code]\n"
            "[code=DefencePower] DefencePower * {defence_multiplier} [/code]\n"
        ),
        placeholders={
            "comment": "Summary (ex: 10% armour pen)",
            "ability_condition": "AbilityId checks or other gating logic",
            "defence_multiplier": "Multiplier to apply to DefencePower",
        },
        example=(
            "##### Example use case #####\n"
            ">SA Global+ ~~ 10% Armor Pen ~~\n"
            "Ability WhenCalcDamage EvenImmobilized\n"
            "[code=Condition] AbilityId == 123 [/code]\n"
            "[code=DefencePower] DefencePower * 0.90 [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="sa_globallast_stat_bonus",
        target_type="SA_GLOBAL_LAST",
        label="Equipment stat bonus",
        description="Applies final stat adjustments for specific accessories or armour.",
        scope_key="Ability",
        block_sequence=["Condition", "MaxHP"],
        body=(
            ">SA GlobalLast+ {label}\n"
            "Ability EvenImmobilized\n"
            "[code=Condition] {gear_condition} [/code]\n"
            "[code={stat_block}] {stat_expression} [/code]\n"
        ),
        placeholders={
            "label": "Summary of the bonus (ex: Plate Armor HP boost)",
            "gear_condition": "AccessoryId/ArmorId check",
            "stat_block": "Stat keyword (MaxHP, MaxMP, Strength, etc.)",
            "stat_expression": "Formula adding or removing value",
        },
        example=(
            "##### Example use case #####\n"
            ">SA GlobalLast+ ~~ Lapiz Lazuli Stone +30mp ~~\n"
            "Ability EvenImmobilized\n"
            "[code=Condition] AccessoryId == 610 [/code]\n"
            "[code=MaxMP] MaxMP + 30 [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="sa_global_enemy_scaler",
        target_type="SA_GLOBAL_ENEMY",
        label="Enemy damage scaling",
        description="Scales enemy damage output based on player statistics.",
        scope_key="Ability",
        block_sequence=["AttackPower"],
        body=(
            ">SA GlobalEnemy+ {comment}\n"
            "Ability WhenCalcDamage EvenImmobilized\n"
            "[code=AttackPower] {attack_formula} [/code]\n"
        ),
        placeholders={
            "comment": "Summary of the scaling behaviour",
            "attack_formula": "Expression adjusting AttackPower (ex: Min((AttackPower * 2), (AttackPower * (1 + (TargetLevel/50)))))",
        },
        example=(
            "##### Example use case #####\n"
            ">SA GlobalEnemy+ ~~ Player damage taken scaler ~~\n"
            "Ability WhenCalcDamage EvenImmobilized\n"
            "[code=AttackPower] Min((AttackPower * 2), (AttackPower * (1 + (TargetLevel/50)))) [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="sa_global_jump_scaler",
        target_type="SA_GLOBAL",
        label="Ability damage scaler",
        description="Boosts specific abilities using level/attribute based formulas.",
        scope_key="Ability",
        block_sequence=["Condition", "AttackPower"],
        body=(
            ">SA Global+ {comment}\n"
            "Ability WhenCalcDamage EvenImmobilized\n"
            "[code=Condition] {ability_condition} [/code]\n"
            "[code=AttackPower] {attack_formula} [/code]\n"
        ),
        placeholders={
            "comment": "Summary of the scaling (ex: Jump DMG scaler)",
            "ability_condition": "AbilityId checks",
            "attack_formula": "Formula boosting AttackPower",
        },
        example=(
            "##### Example use case #####\n"
            ">SA Global+ ~~ Jump DMG Scaler ~~\n"
            "Ability WhenCalcDamage EvenImmobilized\n"
            "[code=Condition] AbilityId == 185 || AbilityId == 186 [/code]\n"
            "[code=AttackPower] AttackPower + ((AttackPower * (CasterLevel * 3 + CasterStrength)) / 200) [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="sa_global_regen_application",
        target_type="SA_GLOBAL",
        label="Reapply status after effect changes",
        description="Reapplies statuses after switching a spell's effect script.",
        scope_key="Ability",
        block_sequence=["Condition", "CasterCurrentStatus"],
        body=(
            ">SA Global+ {comment}\n"
            "Ability WhenBattleScriptEnd EvenImmobilized\n"
            "[code=Condition] {ability_condition} [/code]\n"
            "[code=CasterCurrentStatus] {status_expression} [/code]\n"
        ),
        placeholders={
            "comment": "Description (ex: Reis Wind Regen Application)",
            "ability_condition": "AbilityId checks",
            "status_expression": "CombineStatuses/RemoveStatuses expression",
        },
        example=(
            "##### Example use case #####\n"
            ">SA Global+ ~~ Reis Wind Regen Application ~~\n"
            "Ability WhenBattleScriptEnd EvenImmobilized\n"
            "[code=Condition] AbilityId == 118 [/code]\n"
            "[code=CasterCurrentStatus] CombineStatuses(CasterCurrentStatus, BattleStatus_Regen) [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="sa_global_life_leech",
        target_type="SA_GLOBAL",
        label="Convert damage to healing",
        description="Heals the caster for a portion of HP damage dealt by specified abilities.",
        scope_key="Ability",
        block_sequence=["Condition", "EffectCasterFlags", "CasterHPDamage"],
        body=(
            ">SA Global+ {comment}\n"
            "Ability WhenBattleScriptEnd EvenImmobilized\n"
            "[code=Condition] {ability_condition} [/code]\n"
            "[code=EffectCasterFlags] CalcFlag_HpDamageOrHeal [/code]\n"
            "[code=CasterHPDamage] {hp_expression} [/code]\n"
        ),
        placeholders={
            "comment": "Summary (ex: Lancer HP Leech)",
            "ability_condition": "AbilityId checks and hit flags",
            "hp_expression": "Formula converting damage into healing",
        },
        example=(
            "##### Example use case #####\n"
            ">SA Global+ ~~ Lancer HP Leech ~~\n"
            "Ability WhenBattleScriptEnd EvenImmobilized\n"
            "[code=Condition] (AbilityId == 117) && CasterIsPlayer && !TargetIsPlayer && (EffectFlags & (BattleCalcFlags_Miss | BattleCalcFlags_Guard)) == 0 [/code]\n"
            "[code=EffectCasterFlags] CalcFlag_HpDamageOrHeal [/code]\n"
            "[code=CasterHPDamage] HPDamage / 5 [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="aa_upgrade_switch",
        target_type="AA",
        label="Ability upgrade switch",
        description="Swaps the executed ability ID when a condition is met.",
        scope_key="Ability",
        block_sequence=["Condition", "Patch"],
        body=(
            ">AA {ability_id} {comment}\n"
            "[code=Condition] {upgrade_condition} [/code]\n"
            "[code=Patch] {patch_expression} [/code]\n"
        ),
        placeholders={
            "ability_id": "Ability being modified",
            "comment": "Plain-language summary",
            "upgrade_condition": "Boolean check (eg. HasSA(33))",
            "patch_expression": "New ability ID or -1 to keep original",
        },
        example=(
            "##### Example use case #####\n"
            ">AA 11 Shell\n"
            "[code=Condition] HasSA(33) [/code]\n"
            "[code=Patch] HasSA(33) ? BattleAbilityId_MightyGuard : -1 [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="aa_special_effect_by_level",
        target_type="AA",
        label="Change animation by level",
        description="Chooses a different special effect depending on the caster's level.",
        scope_key="Ability",
        block_sequence=["SpecialEffect"],
        body=(
            ">AA {ability_id} {comment}\n"
            "[code=SpecialEffect] {special_effect_expression} [/code]\n"
        ),
        placeholders={
            "ability_id": "Ability ID being modified",
            "comment": "Summary (ex: Rebuke animation changer)",
            "special_effect_expression": "Ternary expression selecting the SpecialEffect ID",
        },
        example=(
            "##### Example use case #####\n"
            ">AA 35073 Rebuke - Animation changer\n"
            "[code=SpecialEffect] CasterLevel > 50 ? 436 : (CasterLevel > 25 ? 125 : -1) [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="sa_global_magical_crit",
        target_type="SA_GLOBAL",
        label="Enable magical critical hits",
        description="Allows magical abilities to crit and scales the resulting damage.",
        scope_key="Ability",
        block_sequence=["Condition", "EffectTargetFlags", "HPDamage"],
        body=(
            ">SA Global+ {comment}\n"
            "Ability WhenBattleScriptStart EvenImmobilized\n"
            "[code=Condition] {crit_condition} [/code]\n"
            "[code=EffectTargetFlags] EffectTargetFlags | CalcFlag_Critical [/code]\n"
            "Ability WhenBattleScriptEnd EvenImmobilized\n"
            "[code=Condition] {crit_confirm_condition} [/code]\n"
            "[code=HPDamage] {crit_damage_expression} [/code]\n"
        ),
        placeholders={
            "comment": "Summary (ex: Magical Crit BASE)",
            "crit_condition": "Boolean expression that determines when to flag a crit",
            "crit_confirm_condition": "Expression ensuring only magical crits are boosted",
            "crit_damage_expression": "Damage scaling formula applied on crit",
        },
        example=(
            "##### Example use case #####\n"
            ">SA Global+ ~~ Magical Crit BASE ~~\n"
            "Ability WhenBattleScriptStart EvenImmobilized\n"
            "[code=Condition] ((AbilityCategory & 16) != 0) && (GetRandom(0, 100) < (CasterSpirit / 5)) [/code]\n"
            "[code=EffectTargetFlags] EffectTargetFlags | CalcFlag_Critical [/code]\n"
            "Ability WhenBattleScriptEnd EvenImmobilized\n"
            "[code=Condition] ((AbilityCategory & 16) != 0) && (EffectTargetFlags & CalcFlag_Critical) != 0 [/code]\n"
            "[code=HPDamage] HPDamage * 1.3 [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="aa_hide_until_unlocked",
        target_type="AA",
        label="Hide ability until unlocked",
        description="Hard-disables a spell or skill until the condition is true.",
        scope_key="Ability",
        block_sequence=["HardDisable"],
        body=(
            ">AA {ability_id} {comment}\n"
            "[code=HardDisable] !({unlock_condition}) [/code]\n"
        ),
        placeholders={
            "ability_id": "Ability ID to hide",
            "comment": "Description of the lock",
            "unlock_condition": "Expression that becomes true when the ability should appear",
        },
        example=(
            "##### Example use case #####\n"
            ">AA 11001 Cure\n"
            "[code=HardDisable] !(HasSA(12000)) [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="aa_global_mp_discount",
        target_type="AA_GLOBAL",
        label="MP discount by status",
        description="Adjusts MP cost for a range of commands when a condition is met.",
        scope_key="Ability",
        block_sequence=["Condition", "MPCost"],
        body=(
            ">AA Global+ {label}\n"
            "[code=Condition] ({command_filter}) && {status_condition} [/code]\n"
            "[code=MPCost] {mp_expression} [/code]\n"
        ),
        placeholders={
            "label": "Comment summarising the discount",
            "command_filter": "CommandId checks",
            "status_condition": "Boolean status check",
            "mp_expression": "Formula changing MPCost",
        },
        example=(
            "##### Example use case #####\n"
            ">AA Global+ MP Cost reduced in Trance - Red/Wht Mag and Summons\n"
            "[code=Condition] ((CommandId == 9) || (CommandId == 16) || (CommandId == 17) || (CommandId == 18) || (CommandId == 19) || (CommandId == 20) || (CommandId == 21)) && CheckAnyStatus(CasterCurrentStatus, BattleStatus_Trance) [/code]\n"
            "[code=MPCost] MPCost * 0.75 [/code]\n"
            "##### End example #####"
        ),
    ),
    AbilityTemplate(
        template_id="aa_disable_by_scenario",
        target_type="AA",
        label="Disable ability by scenario",
        description="Turns off an ability while a scenario or story flag is active.",
        scope_key="Ability",
        block_sequence=["Disable"],
        body=(
            ">AA {ability_id} {comment}\n"
            "[code=Disable] {disable_expression} [/code]\n"
        ),
        placeholders={
            "ability_id": "Ability ID to control",
            "comment": "Narrative description",
            "disable_expression": "Expression returning 1 to disable (eg. ScenarioCounter < 11100)",
        },
        example=(
            "##### Example use case #####\n"
            ">AA 11000 Materia Void placeholder\n"
            "[code=Disable] 1 [/code]\n"
            "##### End example #####"
        ),
        notes="Use HardDisable instead if the ability should vanish completely.",
    ),
]


def templates_for(target_type: str) -> List[AbilityTemplate]:
    return [tpl for tpl in TEMPLATES if tpl.target_type == target_type]


def type_example(target_type: str) -> Optional[str]:
    info = ABILITY_TYPES.get(target_type)
    if not info:
        return None
    return info.get("example")


def default_templates_by_type() -> Dict[str, List[AbilityTemplate]]:
    mapping: Dict[str, List[AbilityTemplate]] = {}
    for tpl in TEMPLATES:
        mapping.setdefault(tpl.target_type, []).append(copy.deepcopy(tpl))
    return mapping


def templates_to_dict(name: str, template_map: Mapping[str, List[AbilityTemplate]]) -> Dict[str, object]:
    return {
        "name": name,
        "templates": {
            key: [tpl.to_dict() for tpl in value]
            for key, value in template_map.items()
        },
    }


def templates_from_dict(data: Mapping[str, object]) -> Dict[str, List[AbilityTemplate]]:
    result: Dict[str, List[AbilityTemplate]] = {}
    templates_section = data.get("templates")
    if not isinstance(templates_section, Mapping):
        return result
    for key, items in templates_section.items():
        try:
            target_type = str(key)
        except Exception:  # pragma: no cover - defensive
            continue
        result[target_type] = []
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, Mapping):
                tpl = AbilityTemplate.from_dict(item)
                tpl.target_type = target_type
                result[target_type].append(tpl)
    return result


FEATURE_TYPE_DETAILS: List[Dict[str, object]] = [
    {
        "name": "Permanent",
        "description": "Applies as soon as the ability is enabled (refreshes on equipment change).",
        "arguments": [
            "[code=Condition] {Formula} [/code] -> Require the condition before applying the change",
            "[code={Property}] {Formula} [/code] -> Modify the chosen property",
        ],
        "properties": [
            "MaxHP", "MaxMP", "Speed", "Strength", "Magic", "Spirit", "Defence", "Evade",
            "MagicDefence", "MagicEvade", "PlayerCategory", "MPCostFactor", "MaxHPLimit",
            "MaxMPLimit", "MaxDamageLimit", "MaxMPDamageLimit", "PlayerPermanentStatus",
        ],
    },
    {
        "name": "BattleStart",
        "description": "Runs when a battle is triggered, letting you alter preemptive/back-attack odds.",
        "arguments": [
            "[code=Condition] {Formula} [/code] -> Require the condition before applying the change",
            "[code={Property}] {Formula} [/code] -> Modify the chosen property",
            "PreemptivePriority {DELTA} -> Use 'PreemptivePriority +1' to give preemptive higher priority",
        ],
        "properties": [
            "BackAttack (0-255 chance)", "Preemptive (0-255 chance)",
        ],
    },
    {
        "name": "StatusInit",
        "description": "Applies or adjusts statuses right after battle initialisation.",
        "arguments": [
            "[code=Condition] {Formula} [/code] -> Gate the status change",
            "AutoStatus {Status} -> Add a permanent status",
            "InitialStatus {Status} -> Start the battle with the status",
            "ResistStatus {Status} -> Increase resistance to a status",
            "InitialATB {Percent} -> Fill the ATB gauge (100 = full)",
        ],
        "properties": [],
    },
    {
        "name": "Ability",
        "description": "Executes during ability calculation to tweak power, targeting, counters, etc.",
        "arguments": [
            "EvenImmobilized -> Force execution even if the actor is immobilised",
            "AsTarget -> Apply when the owner is targeted",
            "When(Moment) -> Choose the timing (WhenCalcDamage, WhenEffectDone, etc.)",
            "DisableSA {IDs...} -> Disable other SA features dynamically",
            "[code=Condition] {Formula} [/code] -> Require the condition before applying the change",
            "[code={Property}] {Formula} [/code] -> Modify the chosen property",
        ],
        "properties": [
            "CasterHP", "CasterMP", "CasterMaxHP", "CasterMaxMP", "CasterATB", "CasterTrance",
            "CasterCurrentStatus", "CasterResistStatus", "CasterHalfElement", "CasterGuardElement",
            "CasterAbsorbElement", "CasterWeakElement", "CasterBonusElement", "CasterRow",
            "CasterSpeed", "CasterStrength", "CasterMagic", "CasterSpirit", "CasterDefence",
            "CasterEvade", "CasterMagicDefence", "CasterMagicEvade", "CasterCriticalRateBonus",
            "CasterCriticalRateWeakening", "CasterMaxDamageLimit", "CasterMaxMPDamageLimit",
            "CasterBonusExp", "CasterBonusGil", "CasterBonusCard", "EffectCasterFlags",
            "CasterHPDamage", "CasterMPDamage", "EffectTargetFlags", "HPDamage", "MPDamage",
            "Power", "AbilityStatus", "AbilityElement", "AbilityElementForBonus", "IsShortRanged",
            "AbilityCategory", "AbilityFlags", "Attack", "AttackPower", "DefencePower",
            "StatusRate", "HitRate", "Evade", "EffectFlags", "DamageModifierCount",
            "TranceIncrease", "ItemSteal", "Gil", "BattleBonusAP", "Counter", "ReturnMagic",
            "AutoItem",
        ],
    },
    {
        "name": "Command",
        "description": "Runs when a battle command is prepared, letting you adjust targeting or costs.",
        "arguments": [
            "EvenImmobilized -> Apply even if the user is immobilised",
            "[code=Condition] {Formula} [/code] -> Require the condition before applying the change",
            "[code={Property}] {Formula} [/code] -> Modify the chosen property",
        ],
        "properties": [
            "Power", "AbilityStatus", "AbilityElement", "AbilityElementForBonus", "IsShortRanged",
            "AbilityCategory", "AbilityFlags", "IsReflectNull", "IsMeteorMiss", "IsShortSummon",
            "TryCover", "ScriptId", "HitRate", "CommandTargetId", "BattleBonusAP", "Counter",
            "(+ same as Ability properties for caster/target)",
        ],
    },
    {
        "name": "BattleResult",
        "description": "Executes when battle rewards are tallied.",
        "arguments": [
            "When(Moment) -> Pick the reward stage (WhenBattleEnd, WhenRewardAll, WhenRewardSingle)",
            "[code=Condition] {Formula} [/code] -> Gate the reward change",
            "[code={Property}] {Formula} [/code] -> Modify the reward property",
        ],
        "properties": [
            "HP", "MP", "Trance", "Status", "BonusAP", "BonusCard", "BonusEXP", "BonusGil",
            "BonusItemAdd", "EachBonusItem", "EachBonusItemCount", "BonusItem1..BonusItem6",
            "BonusItemCount1..BonusItemCount6", "FleeGil",
        ],
    },
]


NCALC_LINKS: List[Dict[str, str]] = [
    {"label": "Shared informations", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#shared-informations"},
    {"label": "Variables and properties", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#variables-and-properties"},
    {"label": "Player character informations", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#player-character-informations"},
    {"label": "Battle unit informations", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#battle-unit-informations"},
    {"label": "Command informations", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#command-informations"},
    {"label": "Ability effect informations", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#ability-effect-informations"},
    {"label": "Battle bonus informations", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#battle-bonus-informations"},
    {"label": "World Map informations", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#world-map-informations"},
    {"label": "Item property names", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#item-property-names"},
    {"label": "Unit property names", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#unit-property-names"},
    {"label": "INI options", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#ini-options"},
    {"label": "Ability features", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#ability-features"},
    {"label": "SFX Sequence", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#sfx-sequence"},
    {"label": "Battle voice", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#battle-voice"},
    {"label": "Other usage", "url": "https://github.com/Albeoris/Memoria/wiki/NCalc-formulas#other-usage"},
]


def feature_type_details() -> List[Dict[str, object]]:
    return FEATURE_TYPE_DETAILS


def ncalc_links() -> List[Dict[str, str]]:
    return list(NCALC_LINKS)
