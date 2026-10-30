"""Events specific to Smukiez Tag Run: the Multi booster, the wall events, the line drops,
and the Extreme Bonus trigger."""

from copy import deepcopy

BOOSTER = "booster"
WALL_DROP = "wallDrop"
LINE_MULTS = "lineMults"
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


def wall_drop_event(gamestate, kind: str, positions: list) -> None:
    """A wall event on the board just revealed: "line" (3 or 4 walls in a row or column) or
    "cover" (every cell but a scatter). The walls themselves are in the reveal; this names
    them so the client can announce the event. Positions carry the +1 padding offset."""
    pad = 1 if gamestate.config.include_padding else 0
    event = {
        "index": len(gamestate.book.events),
        "type": WALL_DROP,
        "kind": kind,
        "positions": [{"reel": r, "row": c + pad} for r, c in positions],
    }
    gamestate.book.add_event(event)


def line_mults_event(gamestate, drops: list) -> None:
    """The small multipliers the clusters just paid have dropped on their own cells: each drop's
    cell (+1 padding offset) and value, and the whole grid after them (visible rows, no
    padding, as in the booster event) - what the client draws under the tiles as they leave."""
    pad = 1 if gamestate.config.include_padding else 0
    event = {
        "index": len(gamestate.book.events),
        "type": LINE_MULTS,
        "drops": [{"reel": r, "row": c + pad, "mult": v} for r, c, v in drops],
        "gridMults": [[round(v, 2) for v in column] for column in gamestate.grid_mults],
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
