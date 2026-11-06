"""Execute collections on the shared automation worker (cooperative)."""

from __future__ import annotations

from typing import Any, Callable

from idle_lab.automations.schema import Collection, Event, resolve_branch
from idle_lab.automations.store import AutomationStore


LogFn = Callable[[str, str], None]
RunEventFn = Callable[[Event], None]
StopFn = Callable[[], bool]


def should_stop_collection(collection: Collection, variables: dict[str, Any], states: dict[str, bool]) -> bool:
    stop_when = (collection.stop_when or "").strip().lower()
    if not stop_when:
        return False
    if stop_when in {"game_over", "game-over"}:
        if states.get("game_over"):
            return True
        value = str(variables.get("game_over") or "").strip().upper()
        return value in {"GAME_OVER", "TRUE", "1", "YES"}
    # Generic: stop when variable name is truthy / matches itself as flag
    if stop_when in variables:
        value = variables.get(stop_when)
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        return text in {"1", "true", "yes", "game_over"} or text == stop_when
    return False


def expand_collection_children(
    collection: Collection,
    store: AutomationStore,
    variables: dict[str, Any],
) -> list[str]:
    """Return ordered child ids for this pass (branch wins when set)."""

    branched = resolve_branch(collection, variables)
    if branched:
        return [branched]
    return list(collection.children)


def run_collection(
    collection: Collection,
    *,
    store: AutomationStore,
    variables: dict[str, Any],
    states: dict[str, bool],
    run_event: RunEventFn,
    log: LogFn,
    should_abort: StopFn,
    max_loops: int = 1000,
) -> None:
    """Run children serially. Nested collections recurse. Honors loop + stop_when."""

    loops_done = 0
    while True:
        if should_abort():
            log(f"collection {collection.id} aborted", "warn")
            return
        if should_stop_collection(collection, variables, states):
            log(f"collection {collection.id} stop_when={collection.stop_when!r} met", "ok")
            return

        child_ids = expand_collection_children(collection, store, variables)
        if not child_ids:
            log(f"collection {collection.id} has no children to run", "warn")
            return

        log(f"▶ collection {collection.title} ({collection.id}) children={child_ids}", "run")
        for child_id in child_ids:
            if should_abort():
                return
            if should_stop_collection(collection, variables, states):
                log(f"collection {collection.id} stop_when met mid-pass", "ok")
                return
            if child_id in store.events:
                event = store.events[child_id]
                # ``enabled`` only gates the global interval pool; packs always run children.
                run_event(event)
            elif child_id in store.collections:
                nested = store.collections[child_id]
                run_collection(
                    nested,
                    store=store,
                    variables=variables,
                    states=states,
                    run_event=run_event,
                    log=log,
                    should_abort=should_abort,
                    max_loops=max_loops,
                )
            else:
                log(f"collection child missing: {child_id}", "error")

        loops_done += 1
        if not collection.loop:
            log(f"✔ collection {collection.id} finished", "ok")
            return
        if loops_done >= max_loops:
            log(f"collection {collection.id} hit max_loops={max_loops}", "warn")
            return
        log(f"collection {collection.id} looping (pass {loops_done})", "info")
