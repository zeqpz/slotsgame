// The two characters as live 2D rigs (2026-11-09; they were pre-rendered WebP frames, 40-150 MB a figure).
// Everything here replays what Blender computed - no motion is made in the browser: tools/blender/pack_chars.py
// packs, off each figure's .blend, every part's image into one small atlas per density and every distinct pose
// once (each rigid part's 2D map, each bone's deform map for the skinned cloth, cords and bills; which parts show
// and in what depth order), and per clip, frame -> pose. A pose is drawn by placing each part's vertices (linear
// blend skinning for the skinned ones, as Blender's Armature modifier does) and drawing the parts back to front.
//
// Blender lays the semi-transparent parts over each other in linear light, then writes the picture in sRGB. Where
// it can (WebGL 2: every current browser), the rig does the same: the atlas is an sRGB texture (sampled into linear
// light), the parts are blended into an sRGB render texture (blended in linear light, stored in sRGB), and one
// quad puts that on the canvas as sRGB premultiplied - what the frames were. All the parts are ONE mesh there (one
// vertex buffer, the triangles in draw order: one draw call per picture - 34 meshes cost a slow phone ~3 ms a
// pose). The atlas is sampled a little finer than the picture (CharRig.SUPER, the mip level biased to match):
// bilinear filtering at 1:1 softened the ink next to Blender's frames. Without WebGL 2 the parts are drawn straight
// onto the canvas, one mesh each, blended there as the frames were (and the light's mask is left empty).
//
// What a rig cannot be - the Grease Pencil effects (the boy's dust and glints, the skull's ember glow and ash) -
// comes as small frame tracks, decoded by the page (charFrames) and laid over the parts here, in linear light too.
// The skull's smoke stays where it was: on the canvas over the figure, as before.
//
// CharRig.create(app, base, man, dd) -> rig (dd: the atlas density):
//   rig.frame          the figure, in master frame px (y down): place it with rig.place(x, y, scale)
//   rig.view           what goes on the stage (the quad showing the render texture, or the figure itself)
//   rig.pose(clip, i)  -> true if the picture changed (a new pose)
//   rig.fxSlot(kind, clip, i), rig.setFx(kind, bitmap | null, clip, slot) -> true if changed
//   rig.redraw()       draws the figure into its render texture (call after a change)
//   rig.mask(target)   the light's mask into target: in its red channel, how much of each pixel is an unlit part
//                      (shoes, cigar, laces, ash) not covered by a part in front - neonRim reads .r
//   rig.resize()       follows the canvas's size
(function () {
  "use strict";
  const SRGB = "rgba8unorm-srgb";
  const SUPER = 1.4;
  const MVP = `uniform mat3 uProjectionMatrix;
uniform mat3 uWorldTransformMatrix;
uniform mat3 uTransformMatrix;`;
  const VERT = `in vec2 aPosition;
in vec2 aUV;
out vec2 vUV;
${MVP}
void main() {
  mat3 mvp = uProjectionMatrix * uWorldTransformMatrix * uTransformMatrix;
  gl_Position = vec4((mvp * vec3(aPosition, 1.0)).xy, 0.0, 1.0);
  vUV = aUV;
}`;
  // the render texture holds linear light, premultiplied (sRGB-encoded storage, decoded as it is read): back to
  // sRGB, premultiplied in sRGB - Blender's PNG frames as the page drew them
  const QUAD_FRAG = `in vec2 vUV;
out vec4 finalColor;
uniform sampler2D uTexture;
vec3 enc(vec3 c) {
  c = clamp(c, 0.0, 1.0);
  return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}
void main() {
  vec4 c = texture(uTexture, vUV);
  finalColor = c.a > 0.0 ? vec4(enc(c.rgb / c.a) * c.a, c.a) : vec4(0.0);
}`;
  // all the parts: aFlags = (unlit, atlas page). Colour: the texel in linear light, premultiplied. Mask: the unlit
  // parts' coverage in rgb, every part's in alpha - with premultiplied blending a part over an unlit one covers it
  const RIG_VERT = `in vec2 aPosition;
in vec2 aUV;
in vec2 aFlags;
out vec2 vUV;
out vec2 vFlags;   // (constant over each part)
${MVP}
void main() {
  mat3 mvp = uProjectionMatrix * uWorldTransformMatrix * uTransformMatrix;
  gl_Position = vec4((mvp * vec3(aPosition, 1.0)).xy, 0.0, 1.0);
  vUV = aUV;
  vFlags = aFlags;
}`;
  const RIG_FRAG = `in vec2 vUV;
in vec2 vFlags;
out vec4 finalColor;
uniform sampler2D uTexture;
uniform sampler2D uTexture2;
uniform float uBias;
uniform float uMask;
void main() {
  vec4 c = mix(texture(uTexture, vUV, uBias), texture(uTexture2, vUV, uBias), vFlags.y);
  if (uMask > 0.5) { float u = c.a * vFlags.x; finalColor = vec4(u, u, u, c.a); }
  else finalColor = vec4(c.rgb * c.a, c.a);
}`;
  const get = async (url, kind) => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url} -> HTTP ${r.status}`);
    return kind === "blob" ? r.blob() : r.arrayBuffer();
  };

  async function create(app, base, man, dd) {
    const R = man.rig, A = R.atlas[dd];
    if (!A) throw new Error("rig: no atlas at " + dd);
    const renderer = app.renderer;
    const linear = linearOK(app);
    if (linear && A.pages.length > 2) throw new Error("rig: more than two atlas pages");
    const [bin, uvb, ...pages] = await Promise.all([
      get(`${base}/${R.file}`), get(`${base}/${dd}/${A.uv.file}`),
      ...A.pages.map(p => get(`${base}/${dd}/${p.file}`, "blob").then(b => createImageBitmap(b, bitmapOptions(linear)))),
    ]);
    const tex = pages.map(bmp => new PIXI.Texture({
      source: new PIXI.ImageSource({
        resource: bmp, autoGenerateMipmaps: true, scaleMode: "linear",
        // linear: an sRGB texture, read into linear light; straight alpha (premultiplied 8-bit sRGB would decode wrong)
        ...(linear ? { format: SRGB, alphaMode: "no-premultiply-alpha" } : { alphaMode: "premultiply-alpha-on-upload" }),
      }),
    }));
    // trilinear, and anisotropic: a part squashed edge-on (the big win's tumbling bills) would otherwise take a far
    // too coarse mip level and go soft
    for (const t of tex) { const st = t.source.style; st.mipmapFilter = "linear"; st.minFilter = "linear"; st.magFilter = "linear"; st.maxAnisotropy = 8; st.update && st.update(); }
    const NORMAL = linear ? "normal-npm" : "normal";

    const frame = new PIXI.Container();           // master frame px
    const root = new PIXI.Container();            // what is drawn into the render texture: the frame, placed
    root.addChild(frame);
    const P = new Int16Array(bin, R.poses.off, R.poses.n * R.items * 6);
    const VIS = new Uint8Array(bin, R.vis, R.poses.n * R.parts.length);
    const maps = {};
    for (const c in R.maps) maps[c] = new Uint16Array(bin, R.maps[c], man.clips[c].frames);
    const uv16 = new Uint16Array(uvb);
    const nR = R.rigid, nB = R.bones.length, items = R.items, im = 1 / R.qm, it = 1 / R.qt;
    const NP = R.parts.length;

    // ---- the parts (their vertices: one shared buffer in the linear path, a mesh each otherwise)
    const NV = R.parts.reduce((s, p) => s + p.nv, 0);
    let all = null, allPos = null;
    if (linear) { allPos = new Float32Array(NV * 2); }
    let vo = 0;
    const parts = R.parts.map((p, k) => {
      const Pt = { k, name: p.name, unlit: p.unlit, skin: p.skin, nv: p.nv, src: new Float32Array(bin, p.pos, p.nv * 2), v0: vo };
      Pt.idx = p.idx32 ? new Uint32Array(bin, p.idx, p.nt * 3) : new Uint16Array(bin, p.idx, p.nt * 3);
      if (linear) Pt.out = allPos.subarray(vo * 2, (vo + p.nv) * 2);
      else {
        const uvs = new Float32Array(p.nv * 2);
        for (let j = 0; j < p.nv * 2; j++) uvs[j] = uv16[vo * 2 + j] / 65535;
        const geometry = new PIXI.MeshGeometry({ positions: new Float32Array(p.nv * 2), uvs, indices: new Uint32Array(Pt.idx) });
        Pt.mesh = new PIXI.Mesh({ geometry, texture: tex[A.page_of[k]] });
        Pt.mesh.blendMode = NORMAL; Pt.mesh.visible = false;
        frame.addChild(Pt.mesh);
        Pt.out = geometry.positions; Pt.buf = geometry.getBuffer("aPosition");
      }
      if (p.skin) {
        const wi = new Uint8Array(bin, p.wi, p.nv * 4), ww = new Uint16Array(bin, p.ww, p.nv * 4);
        Pt.wo = new Int32Array(p.nv * 4); Pt.ww = new Float32Array(p.nv * 4);
        const used = new Set();
        for (let j = 0; j < p.nv * 4; j++) { Pt.wo[j] = wi[j] * 6; Pt.ww[j] = ww[j] / 65535; if (ww[j]) used.add(wi[j]); }
        Pt.bones = Int32Array.from(used);
      } else Pt.item = p.item;
      vo += p.nv;
      return Pt;
    });
    let rigShader = null;
    if (linear) {
      const uvs = new Float32Array(NV * 2), flags = new Float32Array(NV * 2);
      for (let j = 0; j < NV * 2; j++) uvs[j] = uv16[j] / 65535;
      for (const Pt of parts) for (let v = Pt.v0; v < Pt.v0 + Pt.nv; v++) { flags[v * 2] = Pt.unlit ? 1 : 0; flags[v * 2 + 1] = A.page_of[Pt.k]; }
      const geometry = new PIXI.Geometry({
        attributes: { aPosition: { buffer: allPos, format: "float32x2" }, aUV: { buffer: uvs, format: "float32x2" }, aFlags: { buffer: flags, format: "float32x2" } },
        indexBuffer: new Uint32Array(3),
      });
      rigShader = PIXI.Shader.from({
        gl: { vertex: RIG_VERT, fragment: RIG_FRAG, name: "char-rig-parts" },
        resources: { uTexture: tex[0].source, uTexture2: (tex[1] || tex[0]).source,
                     rig: { uBias: { value: -Math.log2(SUPER), type: "f32" }, uMask: { value: 0, type: "f32" } } },
      });
      all = new PIXI.Mesh({ geometry, shader: rigShader });
      all.blendMode = "normal";                  // premultiplied (the shader premultiplies, in linear light)
      all.posBuf = geometry.getBuffer("aPosition");
      frame.addChild(all);
    }
    // the effect tracks, over the parts: the boy's Grease Pencil, the skull's ember + ash (fx); the skull's ash in
    // the light's mask (fxmask, drawn only there)
    const FX = (R.fx && R.fx.tracks) || {};
    const fxMaskMode = R.fx && R.fx.mask;        // how the art track touches the mask: "erase" (it covers) or none
    const fx = {};
    for (const kind of ["fx", "fxmask"]) {
      const s = new PIXI.Sprite(); s.visible = false; s.blendMode = NORMAL; s._bmp = null; s._src = null; s._clip = null; s._slot = -1;
      fx[kind] = s;
    }
    frame.addChild(fx.fx);
    const maskRoot = new PIXI.Container();       // fxmask is drawn only into the mask
    maskRoot.visible = false;
    maskRoot.addChild(fx.fxmask);
    frame.addChild(maskRoot);

    // ---- poses
    const B = new Float32Array(nB * 6);
    let cur = -1, lastVis = -1;
    const order = new Array(NP).fill(null);
    const place = (Pt, base) => {
      const s = Pt.src, o = Pt.out;
      if (!Pt.skin) {
        const q = base + Pt.item * 6;
        const a = P[q] * im, b = P[q + 1] * im, c = P[q + 2] * im, d = P[q + 3] * im, tx = P[q + 4] * it, ty = P[q + 5] * it;
        for (let j = 0, n = Pt.nv * 2; j < n; j += 2) { const x = s[j], z = s[j + 1]; o[j] = a * x + c * z + tx; o[j + 1] = b * x + d * z + ty; }
      } else {
        const wo = Pt.wo, ww = Pt.ww;
        for (let v = 0, n = Pt.nv; v < n; v++) {
          const x = s[v * 2], z = s[v * 2 + 1];
          let X = 0, Y = 0;
          for (let k = v * 4, e = k + 4; k < e; k++) {
            const w = ww[k];
            if (w === 0) break;
            const q = wo[k];
            X += w * (B[q] * x + B[q + 2] * z + B[q + 4]);
            Y += w * (B[q + 1] * x + B[q + 3] * z + B[q + 5]);
          }
          o[v * 2] = X; o[v * 2 + 1] = Y;
        }
      }
      if (Pt.buf) Pt.buf.update();
    };
    const same = (p, q, item) => { const a = p * items * 6 + item * 6, b = q * items * 6 + item * 6; for (let j = 0; j < 6; j++) if (P[a + j] !== P[b + j]) return false; return true; };
    // the draw order changed (a face swap, a bill tossed): the triangles again, farthest part first (Eevee's
    // order); in the fallback, the meshes' order
    const reorder = vo_ => {
      for (const Pt of parts) { const r = VIS[vo_ + Pt.k]; if (r) order[r - 1] = Pt; }
      if (all) {
        let n = 0;
        for (let r = 0; r < NP; r++) if (order[r]) n += order[r].idx.length;
        const ix = new Uint32Array(Math.max(3, n));
        let w = 0;
        for (let r = 0; r < NP; r++) { const Pt = order[r]; if (!Pt) continue; const src = Pt.idx, off = Pt.v0; for (let j = 0; j < src.length; j++) ix[w++] = src[j] + off; }
        all.geometry.indexBuffer.data = ix;
        all.geometry.indexBuffer.update();
      } else {
        let n = 0;
        for (let r = 0; r < NP; r++) if (order[r]) frame.setChildIndex(order[r].mesh, n++);
        for (const Pt of parts) if (!Pt.mesh.visible) frame.setChildIndex(Pt.mesh, n++);
      }
      order.fill(null);
    };
    const pose = (clip, i) => {
      const m = maps[clip];
      if (!m) return false;
      const p = m[Math.max(0, Math.min(i, m.length - 1))];
      if (p === cur) return false;
      const base = p * items * 6, prev = cur;
      for (let b = 0; b < nB; b++) {
        const q = base + (nR + b) * 6, o = b * 6;
        B[o] = P[q] * im; B[o + 1] = P[q + 1] * im; B[o + 2] = P[q + 2] * im; B[o + 3] = P[q + 3] * im; B[o + 4] = P[q + 4] * it; B[o + 5] = P[q + 5] * it;
      }
      const vo_ = p * NP, pvo = prev * NP;
      let changedVis = lastVis < 0, moved = false;
      for (const Pt of parts) {
        const r = VIS[vo_ + Pt.k], was = prev >= 0 ? VIS[pvo + Pt.k] : 0;
        if (r !== was) changedVis = true;
        if (Pt.mesh) Pt.mesh.visible = r > 0;
        if (!r) continue;
        // a part is placed again only if what moves it changed (or it was hidden)
        let dirty = prev < 0 || !was;
        if (!dirty) {
          if (!Pt.skin) dirty = !same(p, prev, Pt.item);
          else for (let j = 0; j < Pt.bones.length && !dirty; j++) dirty = !same(p, prev, nR + Pt.bones[j]);
        }
        if (dirty) { place(Pt, base); moved = true; }
      }
      if (all && moved) all.posBuf.update();
      if (changedVis) { reorder(vo_); lastVis = p; }
      cur = p;
      return true;
    };

    // ---- the effect tracks
    const trackOf = (kind, clip) => FX[clip] && FX[clip][kind];
    const fxSlot = (kind, clip, i) => { const t = trackOf(kind, clip); return t && i < t.frames.length ? t.frames[i] : -1; };
    const setFx = (kind, bmp, clip, slot) => {
      const s = fx[kind];
      if (!bmp) { const was = s.visible; s.visible = false; return was; }
      if (s.visible && s._clip === clip && s._slot === slot && s._bmp === bmp) return false;
      if (s._bmp !== bmp) {
        const src = s._src;
        if (src && src.width === bmp.width && src.height === bmp.height) { src.resource = bmp; src.update(); }
        else {
          const t = new PIXI.Texture({ source: new PIXI.ImageSource({ resource: bmp, autoGenerateMipmaps: true,
            ...(linear ? { format: SRGB, alphaMode: "no-premultiply-alpha" } : {}) }) });
          t.source.style.minFilter = "linear"; t.source.style.mipmapFilter = "linear";
          const old = s.texture;
          s.texture = t; s._src = t.source;
          if (src && old) old.destroy(true);
        }
        s._bmp = bmp;
      }
      const b = trackOf(kind, clip).boxes[slot];
      s.position.set(b[0], b[1]); s.scale.set((b[2] - b[0]) / bmp.width); s.visible = true;
      s._clip = clip; s._slot = slot;
      return true;
    };

    // ---- on the stage
    let rt = null, view = frame, quad = null;
    if (linear) {
      rt = PIXI.RenderTexture.create({ width: app.screen.width, height: app.screen.height, resolution: renderer.resolution, format: SRGB });
      rt.source.style.scaleMode = "nearest";
      const geo = new PIXI.MeshGeometry({ positions: new Float32Array(8), uvs: new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]), indices: new Uint32Array([0, 1, 2, 0, 2, 3]) });
      quad = new PIXI.Mesh({ geometry: geo, shader: PIXI.Shader.from({ gl: { vertex: VERT, fragment: QUAD_FRAG, name: "char-rig-quad" }, resources: { uTexture: rt.source } }) });
      view = quad;
    }
    const resize = () => {
      if (!rt) return;
      const w = app.screen.width, h = app.screen.height;
      if (rt.width !== w || rt.height !== h || rt.source.resolution !== renderer.resolution) rt.resize(w, h, renderer.resolution);
      const p = quad.geometry.positions;
      p[0] = 0; p[1] = 0; p[2] = w; p[3] = 0; p[4] = w; p[5] = h; p[6] = 0; p[7] = h;
      quad.geometry.getBuffer("aPosition").update();
    };
    resize();
    const placeAt = (x, y, scale) => {
      frame.pivot.set(man.size[0] / 2, man.ground_y);
      frame.scale.set(scale);
      frame.position.set(x, y);
    };
    const redraw = () => {
      if (rt) renderer.render({ container: root, target: rt, clear: true, clearColor: [0, 0, 0, 0] });
    };
    const ru = rigShader && rigShader.resources.rig.uniforms;
    const mask = target => {
      if (!linear) { renderer.render({ container: new PIXI.Container(), target, clear: true, clearColor: [0, 0, 0, 0] }); return; }
      ru.uMask = 1;
      const fxWas = fx.fx.visible;
      if (fxMaskMode === "erase") fx.fx.blendMode = "erase"; else fx.fx.visible = false;
      maskRoot.visible = true;
      renderer.render({ container: root, target, clear: true, clearColor: [0, 0, 0, 0] });
      maskRoot.visible = false;
      fx.fx.visible = fxWas; fx.fx.blendMode = NORMAL;
      ru.uMask = 0;
    };
    return {
      linear, frame, view, pose, fxSlot, setFx, redraw, mask, resize, place: placeAt,
      invalidate: () => { cur = -1; lastVis = -1; },
      showing: () => cur,
    };
  }

  // how a texture's bitmap must be decoded for it (WebGL ignores its unpack settings for an ImageBitmap): straight
  // alpha for the linear path's sRGB textures, premultiplied otherwise
  const bitmapOptions = linear => linear ? { premultiplyAlpha: "none", colorSpaceConversion: "none" } : { premultiplyAlpha: "premultiply" };
  const linearOK = app => !!(typeof WebGL2RenderingContext !== "undefined" && app.renderer.gl instanceof WebGL2RenderingContext) && !/[?&]riglinear=0/.test(location.search);
  window.CharRig = { create, bitmapOptions, linearOK, SUPER };
})();
