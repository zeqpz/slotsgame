import type { Spine } from '@esotericsoftware/spine-pixi-v8';

export type CharacterClip = 'idle' | 'anticipation' | 'win' | 'big_win' | 'lose'
  | 'ash_break' | 'enter' | 'exit';

export function createSmokeSkullController(actor: Spine) {
  actor.state.data.defaultMix = 0.18;
  const loops = new Set<CharacterClip>(['idle', 'anticipation']);

  function startEffects() {
    if (actor.state.getCurrent(1)?.animation?.name !== 'smoke_loop') {
      actor.state.setAnimation(1, 'smoke_loop', true);
    }
    if (actor.state.getCurrent(2)?.animation?.name !== 'ember_loop') {
      actor.state.setAnimation(2, 'ember_loop', true);
    }
  }

  function play(name: CharacterClip) {
    if (name === 'exit') {
      actor.state.setEmptyAnimation(1, 0.1);
      actor.state.setEmptyAnimation(2, 0.1);
    } else {
      startEffects();
    }
    const entry = actor.state.setAnimation(0, name, loops.has(name));
    if (!loops.has(name) && name !== 'exit') {
      actor.state.addAnimation(0, 'idle', true, 0);
    }
    return entry;
  }

  // Hook sounds or game effects into these events, without changing game outcomes.
  // actor.state.addListener({ event: (_entry, event) => {
  //   if (event.data.name === 'ash_split') playAshSound();
  // } });

  play('idle');
  return { play, startEffects };
}
