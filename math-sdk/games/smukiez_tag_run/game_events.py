"""Events specific to Smukiez Tag Run: paint drips, wall progress, character multipliers,
tag meter, and the Full Wall award."""

from copy import deepcopy

PAINT_DRIPS = "paintDrips"
PAINTED_WALL = "paintedWall"
CHARACTER_MULTS = "characterMults"
TAG_METER = "tagMeter"
TAG_METER_FULL = "tagMeterFull"
FULL_WALL = "fullWall"
EXTREME_TRIGGER = "extremeTrigger"


def paint_drips_event(gamestate, new_drips: list) -> None:
    """Origin cells of Paint Drips that landed (or were injected) on this reveal."""
    drips = deepcopy(new_drips)
    if gamestate.config.include_padding:
        for d in drips:
            d["row"] += 1

    event = {"index": len(gamestate.book.events), "type": PAINT_DRIPS, "drips": drips}
    gamestate.book.add_event(event)


def painted_wall_event(gamestate) -> None:
    """Current wall state: which reels are painted and the color bonus per painted reel."""
    event = {
        "index": len(gamestate.book.events),
        "type": PAINTED_WALL,
        "paintedReels": sorted(gamestate.painted_reels),
        "paintLevel": gamestate.paint_level,
        "sections": len(gamestate.painted_reels),
        "totalSections": gamestate.config.num_reels,
    }
    gamestate.book.add_event(event)


def character_mults_event(gamestate) -> None:
    """Character symbols on the board and the combined multiplier applied to the spin win."""
    characters = deepcopy(gamestate.char_mult_details)
    if gamestate.config.include_padding:
        for char in characters:
            for pos in char["positions"]:
                pos["row"] += 1

    event = {
        "index": len(gamestate.book.events),
        "type": CHARACTER_MULTS,
        "characters": characters,
        "totalMult": int(gamestate.active_char_mult),
    }
    gamestate.book.add_event(event)


def tag_meter_event(gamestate) -> None:
    """Tag Meter progress after a winning free spin."""
    event = {
        "index": len(gamestate.book.events),
        "type": TAG_METER,
        "tags": gamestate.tag_meter,
        "target": gamestate.tag_target,
    }
    gamestate.book.add_event(event)


def tag_meter_full_event(gamestate, extra_spins: int) -> None:
    """Tag Meter filled: extra spins awarded and/or paint bonus upgraded."""
    event = {
        "index": len(gamestate.book.events),
        "type": TAG_METER_FULL,
        "extraSpins": extra_spins,
        "paintLevel": gamestate.paint_level,
        "totalFs": gamestate.tot_fs,
    }
    gamestate.book.add_event(event)


def full_wall_event(gamestate) -> None:
    """All five reels painted: the mural is complete and the max win is awarded."""
    event = {
        "index": len(gamestate.book.events),
        "type": FULL_WALL,
        "amount": int(round(gamestate.config.wincap * 100, 0)),
    }
    gamestate.book.add_event(event)


def extreme_trigger_event(gamestate) -> None:
    """Phantom (extreme scatter) positions responsible for an Extreme Bonus entry."""
    positions = deepcopy(gamestate.special_syms_on_board["scatter_extreme"])
    if gamestate.config.include_padding:
        for pos in positions:
            pos["row"] += 1

    event = {
        "index": len(gamestate.book.events),
        "type": EXTREME_TRIGGER,
        "positions": positions,
        "reason": gamestate.bonus_type,
    }
    gamestate.book.add_event(event)
