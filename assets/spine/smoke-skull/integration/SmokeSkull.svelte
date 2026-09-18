<script lang="ts">
  import { SpineProvider, SpineTrack } from 'pixi-svelte';

  // The parent game chooses the reaction and returns it to idle after completion.
  let { animationName = 'idle', x = 0, y = 0, width = 400, showSmoke = true } = $props<{
    animationName?: string;
    x?: number;
    y?: number;
    width?: number;
    showSmoke?: boolean;
  }>();
  const loop = $derived(animationName === 'idle' || animationName === 'anticipation');
</script>

<SpineProvider key="smokeSkull" {width} anchor={{ x: 0.5, y: 1 }} {x} {y}>
  <SpineTrack trackIndex={0} {animationName} {loop} />
  {#if showSmoke && animationName !== 'exit'}
    <SpineTrack trackIndex={1} animationName="smoke_loop" loop={true} />
    <SpineTrack trackIndex={2} animationName="ember_loop" loop={true} />
  {/if}
</SpineProvider>
