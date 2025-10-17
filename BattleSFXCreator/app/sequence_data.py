"""Reference data and templates for Battle SFX sequences."""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional
import copy
import json
import re


@dataclass
class SequenceTemplate:
    template_id: str
    category: str
    label: str
    description: str
    body: str
    placeholders: Mapping[str, str]
    example: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "template_id": self.template_id,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "body": self.body,
            "placeholders": dict(self.placeholders),
            "example": self.example,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SequenceTemplate":
        return cls(
            template_id=str(data.get("template_id", "custom")),
            category=str(data.get("category", "General")),
            label=str(data.get("label", "Unnamed template")),
            description=str(data.get("description", "")),
            body=str(data.get("body", "")),
            placeholders=dict(data.get("placeholders", {})),
            example=data.get("example"),
            notes=data.get("notes"),
        )


GENERIC_TEMPLATES: List[SequenceTemplate] = [
    SequenceTemplate(
        template_id="single_target_spell",
        category="Casting",
        label="Single target spell flow",
        description="Channels, loads, plays and cleans up a single-target spell animation.",
        body=(
            "// {comment}\n"
            "StartThread: Condition=IsSingleTarget ; Sync=True\n"
            "\tLoadSFX: SFX={sfx_name} ; Reflect={reflect} ; UseCamera={use_camera}\n"
            "\tWaitSFXLoaded: SFX={sfx_name} ; Reflect={reflect}\n"
            "\tPlaySFX: SFX={sfx_name} ; Reflect={reflect}\n"
            "\tWaitSFXDone: SFX={sfx_name} ; Reflect={reflect}\n"
            "EndThread\n"
        ),
        placeholders={
            "comment": "Describe the effect",
            "sfx_name": "Memoria SFX identifier",
            "reflect": "True or False depending on reflect support",
            "use_camera": "True to use packaged camera data",
        },
        example=(
            "Example (AlternateFantasy-ef089)\n"
            "StartThread: Condition=IsSingleTarget ; Sync=True\n"
            "\tStartThread: Condition=AreCasterAndSelectedTargetsEnemies ; Sync=True\n"
            "\t\tLoadSFX: SFX=Slow ; Reflect=True ; UseCamera=False\n"
            "\t\tWaitSFXLoaded: SFX=Slow ; Reflect=True\n"
            "\t\tPlaySFX: SFX=Slow ; Reflect=True\n"
            "\t\tWaitSFXDone: SFX=Slow ; Reflect=True\n"
            "\tEndThread\n"
            "EndThread"
        ),
    ),
    SequenceTemplate(
        template_id="item_cast_split",
        category="Casting",
        label="Different animation for items",
        description="Split the sequence depending on whether the command comes from an item or ability.",
        body=(
            "StartThread: Condition=ItemUseId == 255 ; Sync=True\n"
            "\tPlayAnimation: Char=Caster ; Anim={ability_anim}\n"
            "\tWaitAnimation: Char=Caster\n"
            "EndThread\n"
            "StartThread: Condition=ItemUseId != 255 ; Sync=True\n"
            "\tPlayAnimation: Char=Caster ; Anim={item_anim}\n"
            "\tWaitAnimation: Char=Caster\n"
            "EndThread\n"
        ),
        placeholders={
            "ability_anim": "Animation when casting as an ability",
            "item_anim": "Animation when casting via an item",
        },
        example=(
            "Example (AlternateFantasy-ef089)\n"
            "StartThread: Condition=ItemUseId == 255 ; Sync=True\n"
            "\tPlayAnimation: Char=Caster ; Anim=MP_IDLE_TO_CHANT\n"
            "\tWaitAnimation: Char=Caster\n"
            "\tPlayAnimation: Char=Caster ; Anim=MP_CHANT ; Loop=True\n"
            "EndThread\n"
            "StartThread: Condition=ItemUseId != 255 ; Sync=True\n"
            "\tPlayAnimation: Char=Caster ; Anim=MP_ITEM1\n"
            "\tWaitAnimation: Char=Caster\n"
            "EndThread"
        ),
    ),
    SequenceTemplate(
        template_id="target_loop",
        category="Threads",
        label="Per-target loop thread",
        description="Iterates over all targets to apply a repeated effect with spacing.",
        body=(
            "StartThread: TargetLoop=True ; Chain=True ; Sync=True\n"
            "\tLoadSFX: SFX={sfx_name} ; Reflect={reflect}\n"
            "\tWaitSFXLoaded: SFX={sfx_name} ; Reflect={reflect}\n"
            "\tPlaySFX: SFX={sfx_name} ; Reflect={reflect}\n"
            "\tWait: Time={wait_ticks}\n"
            "EndThread\n"
        ),
        placeholders={
            "sfx_name": "Memoria SFX identifier",
            "reflect": "True or False",
            "wait_ticks": "Number of frames (1/30th seconds) to wait between targets",
        },
        example=(
            "Example (AlternateFantasy-ef089)\n"
            "StartThread: TargetLoop=True ; Chain=True ; Sync=True\n"
            "\tLoadSFX: SFX=Haste ; Reflect=True ; UseCamera=False\n"
            "\tWaitSFXLoaded: SFX=Haste ; Reflect=True\n"
            "\tPlaySFX: SFX=Haste ; Reflect=True\n"
            "\tWait: Time=10\n"
            "EndThread"
        ),
    ),
    SequenceTemplate(
        template_id="position_swap",
        category="Movement",
        label="Caster step in/out",
        description="Moves the caster forward for animations then retreats.",
        body=(
            "StartThread: Condition=CasterRow == 0 && AreCasterAndSelectedTargetsEnemies ; Sync=True\n"
            "\tMoveToPosition: Char=Caster ; RelativePosition=(0, 0, {forward_z}) ; Anim={forward_anim}\n"
            "\tWaitMove: Char=Caster\n"
            "EndThread\n"
            "// ... play your effect threads here ...\n"
            "StartThread: Condition=CasterRow == 0 && AreCasterAndSelectedTargetsEnemies ; Sync=True\n"
            "\tMoveToPosition: Char=Caster ; RelativePosition=(0, 0, {back_z}) ; Anim={back_anim}\n"
            "\tWaitMove: Char=Caster\n"
            "EndThread\n"
        ),
        placeholders={
            "forward_z": "Positive Z offset to step forward",
            "back_z": "Negative Z offset returning to idle spot",
            "forward_anim": "Animation to use when stepping forward",
            "back_anim": "Animation to use when stepping back",
        },
        example=(
            "Example (AlternateFantasy-ef089)\n"
            "StartThread: Condition=CasterRow == 0 && AreCasterAndSelectedTargetsEnemies ; Sync=True\n"
            "\tMoveToPosition: Char=Caster ; RelativePosition=(0, 0, 400) ; Anim=MP_STEP_FORWARD\n"
            "\tWaitMove: Char=Caster\n"
            "EndThread\n"
            "...\n"
            "StartThread: Condition=CasterRow == 0 && AreCasterAndSelectedTargetsEnemies ; Sync=True\n"
            "\tMoveToPosition: Char=Caster ; RelativePosition=(0, 0, -400) ; Anim=MP_STEP_BACK\n"
            "\tWaitMove: Char=Caster\n"
            "EndThread"
        ),
    ),
    SequenceTemplate(
        template_id="setup_reflect_bundle",
        category="Reflect",
        label="Setup reflect and cleanup",
        description="Initialises reflect, plays a mirrored SFX, and resolves the channel.",
        body=(
            "SetupReflect: Delay={reflect_delay}\n"
            "StartThread: Condition={condition} ; Sync=True\n"
            "\tLoadSFX: SFX={sfx_name} ; Reflect=True\n"
            "\tWaitSFXLoaded: SFX={sfx_name} ; Reflect=True\n"
            "\tPlaySFX: SFX={sfx_name} ; Reflect=True\n"
            "\tWaitSFXDone: SFX={sfx_name} ; Reflect=True\n"
            "EndThread\n"
            "ActivateReflect\n"
            "WaitReflect\n"
        ),
        placeholders={
            "reflect_delay": "Use SFXLoaded or a Wait expression to delay reflect activation",
            "condition": "Thread condition, e.g. IsSingleTarget",
            "sfx_name": "Memoria SFX identifier to mirror",
        },
        example=(
            "Example (AlternateFantasy-ef089)\n"
            "SetupReflect: Delay=SFXLoaded\n"
            "StartThread: Condition=IsSingleTarget ; Sync=True\n"
            "\tLoadSFX: SFX=Slow ; Reflect=True ; UseCamera=False\n"
            "\tWaitSFXLoaded: SFX=Slow ; Reflect=True\n"
            "\tPlaySFX: SFX=Slow ; Reflect=True\n"
            "\tWaitSFXDone: SFX=Slow ; Reflect=True\n"
            "EndThread\n"
            "ActivateReflect\n"
            "WaitReflect"
        ),
    ),
    SequenceTemplate(
        template_id="caster_turn_and_return",
        category="Movement",
        label="Turn, engage, and reset",
        description="Turns the caster toward the targets, closes distance, then returns to idle position.",
        body=(
            "Turn: Char=Caster ; BaseAngle=AllTargets ; Time={turn_time}\n"
            "WaitTurn: Char=Caster\n"
            "MoveToTarget: Char=Caster ; Target=AllTargets ; Time={move_time} ; Distance={distance}\n"
            "WaitMove: Char=Caster\n"
            "// ... perform attack actions here ...\n"
            "Turn: Char=Caster ; BaseAngle=Default ; Time={return_turn}\n"
            "MoveToPosition: Char=Caster ; AbsolutePosition=Default ; Time={return_time}\n"
            "WaitMove: Char=Caster\n"
        ),
        placeholders={
            "turn_time": "Frames to align with the target",
            "move_time": "Frames to close the gap",
            "distance": "Forward offset in world units",
            "return_turn": "Frames to face forward again",
            "return_time": "Frames to return to home position",
        },
        example=(
            "Example (AlternateFantasy-ef089)\n"
            "StartThread: Condition=CasterRow == 0 && AreCasterAndSelectedTargetsEnemies ; Sync=True\n"
            "\tMoveToPosition: Char=Caster ; RelativePosition=(0, 0, 400) ; Anim=MP_STEP_FORWARD\n"
            "\tWaitMove: Char=Caster\n"
            "EndThread\n"
            "...\n"
            "StartThread: Condition=CasterRow == 0 && AreCasterAndSelectedTargetsEnemies ; Sync=True\n"
            "\tMoveToPosition: Char=Caster ; RelativePosition=(0, 0, -400) ; Anim=MP_STEP_BACK\n"
            "\tWaitMove: Char=Caster\n"
            "EndThread"
        ),
    ),
    SequenceTemplate(
        template_id="status_message",
        category="Messaging",
        label="Battle log status message",
        description="Displays a message banner with the caster and waits before continuing.",
        body=(
            "Message: Text={text} ; Priority=1 ; Title=True ; Reflect={reflect}\n"
            "Wait: Time={wait_ticks}\n"
        ),
        placeholders={
            "text": "e.g. [CastName] or a literal string",
            "reflect": "True to mirror for reflect targets",
            "wait_ticks": "Duration to leave the banner visible",
        },
        example=(
            "Example (AlternateFantasy-ef089)\n"
            "Message: Text=[CastName] ; Priority=1 ; Title=True ; Reflect=True\n"
            "Wait: Time=10"
        ),
        notes="Use literal strings in quotes to show custom text, or a token like [ItemName].",
    ),
]


PLACEHOLDER_DESCRIPTIONS: Mapping[str, str] = {
    "SFX": "SFX identifier",
    "Anim": "Animation identifier",
    "Text": "Message text",
}

BUILT_IN_TEMPLATE_FILES: Mapping[str, str] = {
    "Default": "default.json",
    "Alternate Fantasy": "alternate_fantasy.json",
    "Trance Seek": "trance_seek.json",
    "Ferny Fantasy": "ferny_fantasy.json",
    "Playable Character Pack": "playable_character_pack.json",
}


INSTRUCTION_HELP_HTML = """<h2>Instruction reference</h2>
<h3><code>Wait</code></h3>
<ul><li><code>Time</code> (number): the frames to wait</li></ul>
<h3><code>WaitAnimation</code></h3>
<ul><li><code>Char</code> (character): the character(s) to wait for the animation to end.</li></ul>
<h3><code>WaitMove</code></h3>
<ul><li><code>Char</code> (character): the character(s) to wait for the movement to end.</li></ul>
<h3><code>WaitTurn</code></h3>
<ul><li><code>Char</code> (character): the character(s) to wait for the turning movement to end.</li></ul>
<h3><code>WaitSize</code></h3>
<ul><li><code>Char</code> (character): the character(s) to wait for the size change to end.</li></ul>
<h3><code>WaitSFXLoaded</code></h3>
<ul><li><code>SFX</code> (SFX): the SFX to wait the loading for.</li><li><code>Instance</code> (SFX instance): an ID in case several SFX of the same kind are used.</li></ul>
<h3><code>WaitSFXDone</code></h3>
<ul><li><code>SFX</code> (SFX): the SFX to wait the execution for.</li><li><code>Instance</code> (SFX instance): an ID in case several SFX of the same kind are used.</li></ul>
<h3><code>WaitReflect</code></h3>
<ul><li>No argument</li></ul>
<h3><code>Channel</code></h3>
<ul><li><code>Type</code> (channel name): the name of the channel type.</li><li><code>Char</code> (character): the channeling character.</li><li><code>SkipFlute</code> (boolean): by default, the flute sounds (<code>1501</code>, <code>1507</code> and <code>1508</code>) are played when Eiko channels wearing a flute; this behaviour can be deactivated.</li></ul>
<h3><code>StopChannel</code></h3>
<ul><li><code>Char</code> (character): the channeling character.</li></ul>
<h3><code>LoadSFX</code></h3>
<ul><li><code>SFX</code> (SFX): the SFX to load.</li><li><code>Char</code> (character): the caster of the visual effect.</li><li><code>Target</code> (character): the target(s) of the visual effect.</li><li><code>TargetPosition</code> (position): a custom position for visual effects allowing it.</li><li><code>UseCamera</code> (boolean): force the usage or not of camera movements.</li><li><code>FirstBone</code> (bone): bone of the caster, for the visual effect usage.</li><li><code>SecondBone</code> (bone): bone of the caster, for the visual effect usage.</li><li><code>Args</code> (number): unknown.</li><li><code>MagicCaster</code> (character): the magic caster of the visual effect for Magic Sword-like effects.</li></ul>
<h3><code>PlaySFX</code></h3>
<ul><li><code>SFX</code> (SFX): the SFX to play.</li><li><code>Instance</code> (SFX instance): an ID in case several SFX of the same kind are used.</li><li><code>JumpToFrame</code> (number): add a delay to the SFX execution when negative; skip the start of the effect when positive.</li><li><code>SkipSequence</code> (boolean): do not run the corresponding <code>Sequence.seq</code> file.</li><li><code>HideMeshes</code> (SFX mesh list): prevent the rendering of SFX meshes.</li><li><code>MeshColors</code> (SFX mesh colors): multiply SFX mesh RGB color channels with a custom color.</li></ul>
<h3><code>CreateVisualEffect</code></h3>
<ul><li><code>SPS</code> (number) or <code>SHP</code> (number) or <code>SFXModel</code> (file path): the ID or path of the visual effect to use.</li><li><code>Char</code> (character): to show the visual effect on each of these characters.</li><li><code>Bone</code> (bone): the attachment point of the effect.</li><li><code>Offset</code> (position): an offset to add to the effect's position (or the "average position" in case of SFX Model).</li><li><code>Size</code> (decimal): the scaling factor of the visual effect.</li><li><code>Time</code> (number): the duration of the visual effect.</li><li><code>Speed</code> (decimal): the speed factor for the effect's animation.</li><li><code>UseSHP</code> (boolean) or <code>UseSFXModel</code>: specify that the first argument provided is a SHP ID or a SFX model path.</li></ul>
<h3><code>Turn</code></h3>
<ul><li><code>Char</code> (character): the character(s) to turn.</li><li><code>BaseAngle</code> (base angle): the base angle to turn to.</li><li><code>Angle</code> (angle): the offset to the base angle.</li><li><code>Time</code> (number): the duration of the turning movement.</li><li><code>UsePitch</code> (boolean): interpret the angle offset as a pitch instead of an orientation.</li></ul>
<h3><code>PlayAnimation</code></h3>
<ul><li><code>Char</code> (character): the character(s) to play the animation of.</li><li><code>Anim</code> (animation): the animation to play.</li><li><code>Speed</code> (decimal): the speed ratio of the animation.</li><li><code>Loop</code> (boolean): make the animation loop.</li><li><code>Palindrome</code> (boolean): make the animation play back and forth.</li><li><code>Frame</code> (number): the frame to start the animation at.</li></ul>
<h3><code>PlayTextureAnimation</code></h3>
<ul><li><code>Char</code> (character): the character(s) to play the texture animation of.</li><li><code>Anim</code> (number): the ID of the texture animation to play.</li><li><code>Once</code> (boolean): play it once.</li><li><code>Stop</code> (boolean): stop it instead of playing it.</li></ul>
<h3><code>ToggleStandAnimation</code></h3>
<ul><li><code>Char</code> (character): the character(s) to change the default animations of (it should be an enemy).</li><li><code>Alternate</code> (boolean): use the alternate animations.</li></ul>
<h3><code>MoveToTarget</code></h3>
<ul><li><code>Char</code> (character): the character(s) to move.</li><li><code>Target</code> (character): the character(s) to move to.</li><li><code>Offset</code> (position): the offset to the target position.</li><li><code>Distance</code> (decimal): the distance offset toward the target.</li><li><code>Time</code> (number): the duration of the movement.</li><li><code>Anim</code> (animation): the animation to play during the movement (setup the duration).</li><li><code>MoveHeight</code> (boolean): also move the height of the character.</li><li><code>UseCollisionRadius</code> (boolean): add the target's radius to the distance (single-target only).</li><li><code>IsRelativeDistance</code> (boolean): use the moving character's position as a basis instead of the target's position.</li></ul>
<h3><code>MoveToPosition</code></h3>
<ul><li><code>Char</code> (character): the character(s) to move.</li><li><code>AbsolutePosition</code> (position): the position to move to.</li><li><code>RelativePosition</code> (position): the offset added to the absolute position.</li><li><code>Time</code> (number): the duration of the movement.</li><li><code>Anim</code> (animation): the animation to play during the movement (setup the duration).</li><li><code>MoveHeight</code> (boolean): also move the height of the character.</li></ul>
<h3><code>ChangeSize</code></h3>
<ul><li><code>Char</code> (character): the character(s) to rescale.</li><li><code>Size</code> (size): the new size.</li><li><code>Time</code> (number): the duration of the rescale.</li><li><code>ScaleShadow</code> (boolean): also rescale the shadow.</li><li><code>IsRelative</code> (boolean): the new size is relative to the current size.</li></ul>
<h3><code>ShowMesh</code></h3>
<ul><li><code>Char</code> (character): the character(s) to show/hide.</li><li><code>Enable</code> (boolean): either show or hide.</li><li><code>Mesh</code> (mesh list): the meshes to show/hide.</li><li><code>Time</code> (number): the fading duration.</li><li><code>IsDisappear</code> (boolean): make the character completly disappear.</li></ul>
<h3><code>ShowShadow</code></h3>
<ul><li><code>Char</code> (character): the character(s) to show/hide the shadow of.</li><li><code>Enable</code> (boolean): either show or hide.</li></ul>
<h3><code>ChangeCharacterProperty</code></h3>
<ul><li><code>Char</code> (character): the character(s) to change the property of.</li><li><code>Property</code> (property type): the property to change.</li><li><code>Value</code> (property value): the updated value.</li></ul>
<h3><code>PlaySound</code></h3>
<ul><li><code>Sound</code> (sound): the sound ID or name.</li><li><code>SoundType</code> (sound type): the sound type.</li><li><code>Volume</code> (decimal): the sound's volume.</li><li><code>Pitch</code> (decimal): the sound's pitch.</li><li><code>Panning</code> (decimal): the sound's panning.</li></ul>
<h3><code>StopSound</code></h3>
<ul><li><code>Sound</code> (sound): the sound ID or name.</li><li><code>SoundType</code> (sound type): the sound type.</li></ul>
<h3><code>EffectPoint</code></h3>
<ul><li><code>Char</code> (character): the character(s) to apply the ability's effect on.</li><li><code>Type</code> (effect type): either the damage point, the figure point or both.</li></ul>
<h3><code>Message</code></h3>
<ul><li><code>Text</code> (message): the text to display. The arguments <code>TextUS</code>, <code>TextJP</code> etc. can be used for language-dependant messages.</li><li><code>Title</code> (boolean): whether the message is a title or a dialog (influences the message box's appearance).</li><li><code>Priority</code> (number): the priority of the message over other messages.</li></ul>
<h3><code>SetBackgroundIntensity</code></h3>
<ul><li><code>Intensity</code> (decimal): the intensity ratio.</li><li><code>Time</code> (number): the fading time.</li><li><code>HoldDuration</code> (number): the duration of the intensity drop.</li></ul>
<h3><code>ShiftWorld</code></h3>
<ul><li><code>Offset</code> (position): the offset by which the world is moved (characters and background, but not camera nor SFX).</li><li><code>Angle</code> (angle): the angle(s) by which the world is rotated.</li></ul>
<h3><code>SetVariable</code></h3>
<ul><li><code>Variable</code> (variable type): the variable to change.</li><li><code>Index</code> (depends on variable type): either the array index or a string key.</li><li><code>Value</code> (variable value): the updated value.</li></ul>
<h3><code>SetupReflect</code></h3>
<ul><li><code>Delay</code> (reflect delay): the delay to wait before the reflect visual effect gets displayed.</li></ul>
<h3><code>ActivateReflect</code></h3>
<ul><li>No argument</li></ul>
<h3><code>StartThread</code></h3>
<ul><li><code>Condition</code> (formula): see Conditional threads.</li><li><code>LoopCount</code> (number): see Looping threads.</li><li><code>Target</code> (character): see Target swap.</li><li><code>TargetLoop</code> (boolean): see Target swap.</li><li><code>Chain</code> (boolean): see Looping threads.</li><li><code>Sync</code> (boolean): see Sync and async threads.</li></ul>
<h3><code>EndThread</code></h3>
<ul><li>No argument</li></ul>
<h3><code>MOVE_WATER</code></h3>
<ul><li><code>Char</code> (character): the character(s) to move.</li><li><code>Type</code> (Single/Multi/Sword): the type of Water-spell movement.</li><li><code>Time</code> (number): the duration of the movement.</li></ul>"""


ARGUMENT_HELP_HTML = """<h2>Argument types</h2>
<h3>character</h3>
<ul><li><code>AllTargets</code>: the targets of the thread, subject to target swap or reflect bounce.</li><li><code>AllNonTargets</code>: all the units except those in <code>AllTargets</code>.</li><li><code>RandomTarget</code>: a random target amongst <code>AllTargets</code>.</li><li><code>Caster</code>: the user of the command.</li><li><code>AllPlayers</code>: the player's team.</li><li><code>AllEnemies</code>: the enemy team.</li><li><code>Everyone</code>: both teams.</li><li><code>Zidane</code>, <code>Vivi</code>, <code>Dagger</code>, <code>Steiner</code>, <code>Freya</code>, <code>Quina</code>, <code>Eiko</code>, <code>Amarant</code>, <code>Cinna</code>, <code>Marcus</code>, <code>Blank</code>, <code>Beatrix</code>: the corresponding player character if present.</li><li><code>FirstTarget</code>, <code>SecondTarget</code> etc.: the corresponding target amongst <code>AllTargets</code> if there are at least that many.</li><li>A number: the character(s) as a bit flag.</li><li><code>MatchingCondition({Condition})</code>: a NCalc formula specifying a custom condition.</li></ul>
<h3>bone</h3>
<ul><li><code>Target</code>: the bone that is used for target selection.</li></ul>
<h3>animation</h3>
<ul><li><code>Current</code>: the current character's animation.</li></ul>
<h3>position</h3>
<ul><li>A vector in <code>(x, height, y)</code> format: the vector position or offset.</li></ul>
<h3>base angle</h3>
<ul><li><code>Current</code>: the current character's angle.</li></ul>
<h3>angle</h3>
<ul><li>A decimal: the angle value in degrees.</li></ul>
<h3>size</h3>
<ul><li><code>Reset</code>: the default size <code>(1, 1, 1)</code>.</li></ul>
<h3>mesh list</h3>
<ul><li><code>All</code>: all the meshes, including the weapon meshes and the shadow.</li></ul>
<h3>sound</h3>
<ul><li><code>WeaponAttack</code>: for player characters, the sound effect of swinging the weapon.</li></ul>
<h3>sound type</h3>
<ul><li>A sound type: see the Memoria sound profile docs (default is <code>SoundEffect</code>).</li></ul>
<h3>effect type</h3>
<ul><li><code>Effect</code>: run the battle script to apply damage, statuses or other effects.</li><li><code>Figure</code>: show the damage number(s) and/or effect messages.</li><li><code>Both</code>: apply the effect point then the figure point.</li></ul>
<h3>reflect delay</h3>
<ul><li><code>SFXLoaded</code>: wait for any SFX to have loaded (NYI).</li><li><code>SFXPlay</code>: wait for any SFX to have started playing (NYI).</li><li><code>SFXDone</code>: wait for any SFX to have finished playing (NYI).</li><li>A number: the time to wait.</li></ul>
<h3>property type</h3>
<ul><li><code>base_pos</code>: the base position of the character.</li><li><code>tar_bone</code>: the target bone ID of the character.</li></ul>
<h3>property value</h3>
<ul><li><code>Original</code> (for <code>base_pos</code>): the original battle position.</li><li><code>Current</code> (for <code>base_pos</code>): the current position.</li><li>A vector (for <code>base_pos</code>): the absolute position to use.</li><li>A value (for <code>tar_bone</code>): the new value.</li></ul>
<h3>variable type</h3>
<ul><li><code>_ZWrite</code>: the battle background's ground opacity value.</li><li><code>btl_seq</code>: the battle sub-phase.</li><li><code>cmd_status</code>: the battle command status.</li><li><code>gEventGlobal</code>: the array of event variables; modifications are bytewise.</li><li><code>local</code>: dictionary associating numbers to string keys; accessible via <code>local_{Index}</code>.</li></ul>
<h3>variable value</h3>
<ul><li>A number: the new value.</li><li><code>+N</code>: add to the current value.</li><li><code>&N</code>: keep only these bit flags.</li><li><code>|N</code>: add these bit flags.</li><li><code>Formula({Formula})</code>: an expression that can reference the previous value via <code>Current</code>.</li></ul>"""


def _game_root() -> Path:
    # sequence_data.py -> app -> BattleSFXCreator -> <game root>
    return Path(__file__).resolve().parents[2]


def _normalise_text(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def _apply_placeholders(text: str) -> tuple[str, Mapping[str, str]]:
    placeholders: "OrderedDict[str, str]" = OrderedDict()
    counters: Dict[str, int] = defaultdict(int)

    def substitute(token: str, content: str) -> str:
        pattern = re.compile(rf"(?P<prefix>{token}\s*=\s*)(?P<value>[^;\n]+)")

        def _replace(match: re.Match[str]) -> str:
            value = match.group("value").strip()
            counters[token] += 1
            placeholder_name = f"{token.lower()}_{counters[token]}"
            description = PLACEHOLDER_DESCRIPTIONS.get(token, f"{token} value")
            if placeholder_name not in placeholders:
                placeholders[placeholder_name] = f"{description} (was {value})"
            return f"{match.group('prefix')}{{{placeholder_name}}}"

        return pattern.sub(_replace, content)

    mutable = text
    for token in ("SFX", "Anim", "Text"):
        mutable = substitute(token, mutable)

    return mutable, placeholders


def individual_templates_by_category() -> Dict[str, List[SequenceTemplate]]:
    mapping: Dict[str, List[SequenceTemplate]] = {}
    for tpl in GENERIC_TEMPLATES:
        mapping.setdefault(tpl.category, []).append(copy.deepcopy(tpl))
    for templates in mapping.values():
        templates.sort(key=lambda tpl: tpl.label.lower())
    return mapping


def built_in_template_paths() -> Dict[str, Path]:
    template_dir = Path(__file__).resolve().parent / "templates"
    return {name: template_dir / filename for name, filename in BUILT_IN_TEMPLATE_FILES.items()}

def built_in_template_sets() -> Dict[str, Dict[str, List[SequenceTemplate]]]:
    sets: Dict[str, Dict[str, List[SequenceTemplate]]] = {}

    sets["Individuals"] = individual_templates_by_category()

    template_dir = Path(__file__).resolve().parent / "templates"

    for name, filename in BUILT_IN_TEMPLATE_FILES.items():
        path = template_dir / filename
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            print(f"Failed to load built-in template set {name}: {exc}")
            continue
        mapping = templates_from_dict(data)
        if mapping:
            sets[name] = mapping

    return sets


def templates_to_dict(name: str, template_map: Mapping[str, List[SequenceTemplate]]) -> Dict[str, object]:
    return {
        "name": name,
        "templates": {
            category: [tpl.to_dict() for tpl in templates]
            for category, templates in template_map.items()
        },
    }


def templates_from_dict(data: Mapping[str, object]) -> Dict[str, List[SequenceTemplate]]:
    result: Dict[str, List[SequenceTemplate]] = {}
    templates_section = data.get("templates")
    if not isinstance(templates_section, Mapping):
        return result
    for category, items in templates_section.items():
        if not isinstance(items, list):
            continue
        group: List[SequenceTemplate] = []
        for item in items:
            if isinstance(item, Mapping):
                tpl = SequenceTemplate.from_dict(item)
                tpl.category = str(category)
                group.append(tpl)
        if group:
            result[str(category)] = group
    return result
