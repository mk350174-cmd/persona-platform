import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

const DOMAIN_COLORS = {
  Philosophy: 0x8b5cf6,
  Science: 0x06b6d4,
  Ethics: 0x3b82f6,
  Leadership: 0xf59e0b,
  Arts: 0xf97316,
  Literature: 0x34d399,
  Fiction: 0xec4899,
  Mythology: 0xa78bfa,
};

export default function PersonaExplorer3D({ personas = [], onSelect }) {
  const containerRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const spheresRef = useRef([]);
  const [hoveredId, setHoveredId] = useState(null);

  useEffect(() => {
    if (!containerRef.current || personas.length === 0) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x12121d);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(
      75,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.z = 15;
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0xffffff, 0.8);
    pointLight.position.set(10, 10, 10);
    scene.add(pointLight);

    // Create persona spheres
    const spheres = [];
    const sphereGeometry = new THREE.IcosahedronGeometry(0.5, 4);

    personas.forEach((persona, index) => {
      const color = DOMAIN_COLORS[persona.domain] || 0x8b5cf6;
      const material = new THREE.MeshPhongMaterial({ color });

      const sphere = new THREE.Mesh(sphereGeometry, material);

      // Position in sphere pattern
      const phi = Math.acos(-1 + (2 * index) / personas.length);
      const theta = Math.sqrt(personas.length * Math.PI) * phi;
      const radius = 8;

      sphere.position.x = radius * Math.cos(theta) * Math.sin(phi);
      sphere.position.y = radius * Math.sin(theta) * Math.sin(phi);
      sphere.position.z = radius * Math.cos(phi);

      sphere.userData = { personaId: persona.id, personaName: persona.name };
      sphere.originalColor = color;
      spheres.push(sphere);
      scene.add(sphere);
    });
    spheresRef.current = spheres;

    // Mouse interaction
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onMouseMove = (event) => {
      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(spheres);

      spheres.forEach((sphere) => {
        if (intersects.length > 0 && intersects[0].object === sphere) {
          sphere.material.color.setHex(0xffffff);
          sphere.scale.set(1.3, 1.3, 1.3);
          setHoveredId(sphere.userData.personaId);
        } else {
          sphere.material.color.setHex(sphere.originalColor);
          sphere.scale.set(1, 1, 1);
        }
      });
    };

    const onClick = (event) => {
      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(spheres);

      if (intersects.length > 0) {
        const selected = intersects[0].object;
        onSelect?.(selected.userData.personaId);
      }
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('click', onClick);

    // Animation loop
    let animationId;
    const animate = () => {
      animationId = requestAnimationFrame(animate);

      spheres.forEach((sphere) => {
        sphere.rotation.x += 0.002;
        sphere.rotation.y += 0.003;
      });

      renderer.render(scene, camera);
    };
    animate();

    // Handle window resize
    const onWindowResize = () => {
      if (!containerRef.current) return;
      const width = containerRef.current.clientWidth;
      const height = containerRef.current.clientHeight;

      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener('resize', onWindowResize);

    // Cleanup
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('click', onClick);
      window.removeEventListener('resize', onWindowResize);
      cancelAnimationFrame(animationId);
      containerRef.current?.removeChild(renderer.domElement);
      renderer.dispose();
      sphereGeometry.dispose();
    };
  }, [personas, onSelect]);

  return (
    <div
      ref={containerRef}
      className="w-full h-96 rounded-xl overflow-hidden border border-border-glass"
      style={{ position: 'relative' }}
    >
      {hoveredId && (
        <div className="absolute top-4 left-4 z-10 glass-panel rounded-lg px-4 py-2 text-sm">
          <p className="text-on-surface">{hoveredId}</p>
        </div>
      )}
    </div>
  );
}
