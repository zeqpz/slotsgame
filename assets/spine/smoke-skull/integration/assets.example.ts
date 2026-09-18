// Merge this entry into your Stake/engine.io game's asset manifest.
// Copy the JSON, atlas, and the atlas PNG to public/assets/smoke-skull/.
export const smokeSkullAssets = {
  smokeSkull: {
    type: 'spine',
    src: {
      atlas: '/assets/smoke-skull/smoke-skull.atlas',
      skeleton: '/assets/smoke-skull/smoke-skull.json',
      scale: 1,
    },
    preload: true,
  },
} as const;
