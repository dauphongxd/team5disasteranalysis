import React, { useEffect } from "react";
import * as THREE from "three";

const Scene = () => {
  useEffect(() => {
    const container = document.getElementById("background-container"); // Target the background container

    // Scene, Camera, and Renderer
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000); // Black background

    const camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    );
    camera.position.z = 30; // Position the camera to view the stars

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true, // Transparent background
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement); // Attach the renderer to the background container

    // Particles (Stars)
    const particlesCount = 2000;
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesPositions = new Float32Array(particlesCount * 3);

    for (let i = 0; i < particlesCount * 3; i++) {
      particlesPositions[i] = (Math.random() - 0.5) * 50; // Spread particles over a larger area
    }

    particlesGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(particlesPositions, 3)
    );

    const particlesMaterial = new THREE.PointsMaterial({
      size: 0.1, // Size of the stars
      sizeAttenuation: true,
      color: 0xffffff, // Bright white stars
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending, // Additive blending for a glowing effect
    });

    const particles = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particles);

    // Animation Loop
    function animate() {
      requestAnimationFrame(animate);

      // Rotate the stars for a dynamic effect
      particles.rotation.y += 0.001;

      renderer.render(scene, camera);
    }

    // Handle Window Resize
    window.addEventListener("resize", () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    });

    animate();

    // Cleanup on Component Unmount
    return () => {
      container.removeChild(renderer.domElement);
    };
  }, []);

  return <div id="background-container"></div>; // Render the background container
};

export default Scene;
