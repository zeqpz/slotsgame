/** Pass your engine's existing Spine 4.2 AnimationState. */
export function createSmukiezController(state, onCue = () => {}) {
  state.data.defaultMix = 0.18;
  const listener = { event: (_entry, event) => onCue(event.data.name, event) };
  state.addListener(listener);
  const once = name => {
    state.setAnimation(0, name, false);
    state.addAnimation(0, 'idle', true, 0);
  };
  const controller = {
    enter: () => { const e = state.setAnimation(0, 'enter', false); e.mixDuration = 0; state.addAnimation(0, 'idle', true, 0); return e; },
    exit: () => { const e = state.setAnimation(0, 'exit', false); e.mixDuration = 0; return e; },
    idle: () => state.setAnimation(0, 'idle', true),
    anticipation: () => state.setAnimation(0, 'anticipation', true),
    win: () => once('win'),
    bigWin: () => once('big_win'),
    lose: () => once('lose'),
    cashShow: () => once('cash_show'),
    cashToss: () => once('cash_toss'),
    cashCount: (loop = false) => loop
      ? state.setAnimation(0, 'cash_count', true)
      : once('cash_count'),
    dispose: () => state.removeListener(listener),
  };
  controller.idle();
  return controller;
}
