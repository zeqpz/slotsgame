# Artwork preparation

Original body parts were separated from the supplied 5000 × 5000 PNG at a 1600 × 1600 working scale. Original cutouts remain in images/. The final rig contains five facial variants.

The built-in image-generation tool supplied reconstructed expressions, a clean cigar, secondary wisps, and ash fragments. Transparent alpha was retained; sprites were cropped, disconnected stray pixels removed, and the atlas packed. This was not the API/CLI fallback.

## Prompt briefs for retained artwork

**Reconstruction:** Preserve the character's identity, monochrome graffiti linework, knit cap, clothing, lettering, white outline, and brown lit cigar. Separate body, head, jaw, shoes, cigar, plume, and wisps on transparent alpha. Reconstruct hidden overlaps. No labels, backdrop, shadows, clipping, or touching pieces. The final rig uses the clean cigar and secondary wisp alongside original body pixels.

**Expressions:** Preserve the three-quarter skull, larger viewer-right socket, dark beanie, gray/white bone, thick ink, and white outline. Keep camera, scale, and registration consistent. Retained variants: calm tough idle, alert anticipation, confident happy win, ecstatic big-win laughter with small gold eye sparkles, disappointed lose. Keep the cigar separate. No torso, smoke, grid, labels, or backdrop.

**Alpha refinement:** Remove exterior backdrop and shadows while preserving heads, hat geometry, outlines, proportions, and placement.

**Ash:** An intact short gray/off-white ash cap and four smaller irregular fragments, with dark cracks and cartoon outlines, spaced apart on transparent alpha. No cigar body, flame, character, labels, or backdrop. Rig the fragments to split and fall.

Expression changes use attachments. Breathing, jaw, leg, and shoe movements use bones. Shoes are scaled to 90% in the rig. No audio is supplied.
