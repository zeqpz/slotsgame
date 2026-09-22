"""Events specific to Smukiez Tag Run: the Multi booster, the Tag Meter, and the Extreme
Bonus trigger."""

from copy import deepcopy

BOOSTER = "booster"
TAG_METER = "tagMeter"
TAG_METER_FULL = "tagMeterFull"
EXTREME_TRIGGER = "extremeTrigger"


def booster_event(gamestate) -> None:
    """Every Multi that just blew out: where it sat, what it was worth, which cells it hit.

    Positions carry the +1 padding offset every positional event in this game uses. The
    gridMults snapshot does not: it is the whole board, reel-major, visible rows only, and
    it is the state AFTER these Multis have been added in - what the client should draw
    behind the tiles once the refill lands.
    """
    boosters = deepcopy(gamestate.booster_details)
    if gamestate.config.include_padding:
        for b in boosters:
            b["row"] += 1
            for cell in b["cells"]:
                cell["row"] += 1

    event = {
        "index": len(gamestate.book.events),
        "type": BOOSTER,
        "boosters": boosters,
        "gridMults": [[round(v, 2) for v in column] for column in gamestate.grid_mults],
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
    """Tag Meter filled: extra spins awarded."""
    event = {
        "index": len(gamestate.book.events),
        "type": TAG_METER_FULL,
        "extraSpins": extra_spins,
        "totalFs": gamestate.tot_fs,
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
