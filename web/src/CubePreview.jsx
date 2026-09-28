import { useEffect, useRef } from "react";
import { HEX, PREVIEW } from "./constants.js";

const PLASTIC = 0x2a3038;
const SPACING = 1.04;

function hexNum(name) {
  return name ? Number.parseInt(HEX[name].slice(1), 16) : PLASTIC;
}

function stickerColor(colors, face, x, y, z) {
  if (!colors) return null;
  let index;
  if (face === "U") index = (z + 1) * 3 + (x + 1);
  if (face === "D") index = (1 - z) * 3 + (x + 1);
  if (face === "F") index = (1 - y) * 3 + (x + 1);
  if (face === "B") index = (1 - y) * 3 + (1 - x);
  if (face === "R") index = (1 - y) * 3 + (1 - z);
  if (face === "L") index = (1 - y) * 3 + (z + 1);
  return colors[index];
}

export default function CubePreview({ faces, liveColors, previewFace }) {
  const mountRef = useRef(null);
  const apiRef = useRef(null);
  const viewRef = useRef({ colors: {}, face: "iso" });

  useEffect(() => {
    const mount = mountRef.current;
    let disposed = false;
    let frame = 0;

    (async () => {
      const THREE = await import("three");
      const { OrbitControls } = await import("three/addons/controls/OrbitControls.js");
      if (disposed) return;
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x141820);
      const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
      camera.position.set(...PREVIEW.iso);
      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      if ("outputColorSpace" in renderer) renderer.outputColorSpace = THREE.SRGBColorSpace;
      mount.appendChild(renderer.domElement);
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.enablePan = false;
      controls.minDistance = 5;
      controls.maxDistance = 12;
      controls.target.set(0, 0, 0);
      camera.lookAt(0, 0, 0);

      // Even lighting so bottom and back faces stay readable while orbiting.
      scene.add(new THREE.AmbientLight(0xffffff, 0.72));
      scene.add(new THREE.HemisphereLight(0xffffff, 0x6a7588, 1.1));
      const key = new THREE.DirectionalLight(0xffffff, 0.85);
      key.position.set(4, 9, 6);
      scene.add(key);
      const fillFront = new THREE.DirectionalLight(0xffffff, 0.55);
      fillFront.position.set(0, 1, 10);
      scene.add(fillFront);
      const fillBottom = new THREE.DirectionalLight(0xe8eef8, 0.75);
      fillBottom.position.set(0, -9, 3);
      scene.add(fillBottom);
      const rim = new THREE.DirectionalLight(0xffffff, 0.35);
      rim.position.set(-6, 2, -5);
      scene.add(rim);

      function stickerMaterial(name) {
        const color = hexNum(name);
        // Basic material shows sticker colors faithfully on every face.
        return new THREE.MeshBasicMaterial({ color });
      }

      const cubelets = [];
      let geometry = null;
      let aimed = "";

      function resize() {
        const w = Math.max(1, mount.clientWidth);
        const h = Math.max(1, mount.clientHeight);
        renderer.setSize(w, h, true);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
      }
      function paint(colorMap, face) {
        cubelets.forEach((mesh) => {
          scene.remove(mesh);
          mesh.material.forEach((material) => material.dispose());
        });
        cubelets.length = 0;
        if (geometry) geometry.dispose();
        geometry = new THREE.BoxGeometry(0.96, 0.96, 0.96);
        for (let x = -1; x <= 1; x += 1) {
          for (let y = -1; y <= 1; y += 1) {
            for (let z = -1; z <= 1; z += 1) {
              if (!x && !y && !z) continue;
              const mesh = new THREE.Mesh(geometry, [
                stickerMaterial(x === 1 ? stickerColor(colorMap.R, "R", x, y, z) : null),
                stickerMaterial(x === -1 ? stickerColor(colorMap.L, "L", x, y, z) : null),
                stickerMaterial(y === 1 ? stickerColor(colorMap.U, "U", x, y, z) : null),
                stickerMaterial(y === -1 ? stickerColor(colorMap.D, "D", x, y, z) : null),
                stickerMaterial(z === 1 ? stickerColor(colorMap.F, "F", x, y, z) : null),
                stickerMaterial(z === -1 ? stickerColor(colorMap.B, "B", x, y, z) : null),
              ]);
              mesh.position.set(x * SPACING, y * SPACING, z * SPACING);
              scene.add(mesh);
              cubelets.push(mesh);
            }
          }
        }
        if (face !== aimed) {
          aimed = face;
          camera.position.set(...(PREVIEW[face] || PREVIEW.iso));
          controls.target.set(0, 0, 0);
          controls.update();
        }
      }
      function tick() {
        controls.update();
        renderer.render(scene, camera);
        frame = requestAnimationFrame(tick);
      }
      apiRef.current = { paint };
      resize();
      paint(viewRef.current.colors, viewRef.current.face);
      const observer = new ResizeObserver(resize);
      observer.observe(mount);
      tick();
      apiRef.current.cleanup = () => {
        cancelAnimationFrame(frame);
        observer.disconnect();
        cubelets.forEach((mesh) => mesh.material.forEach((material) => material.dispose()));
        if (geometry) geometry.dispose();
        renderer.dispose();
        mount.removeChild(renderer.domElement);
      };
    })();

    return () => {
      disposed = true;
      apiRef.current?.cleanup?.();
      apiRef.current = null;
    };
  }, []);

  useEffect(() => {
    const colors = { ...faces };
    if (liveColors) colors[liveColors.face] = liveColors.colors;
    viewRef.current = { colors, face: previewFace };
    apiRef.current?.paint?.(colors, previewFace);
  }, [faces, liveColors, previewFace]);

  return <div className="preview" ref={mountRef} />;
}
