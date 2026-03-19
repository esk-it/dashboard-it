<script>
  import { onMount, onDestroy } from 'svelte';

  let canvas;
  let ctx;
  let animationId;
  let width = 0;
  let height = 0;
  let mouseX = 0.5;
  let mouseY = 0.5;
  let targetMouseX = 0.5;
  let targetMouseY = 0.5;
  let startTime = Date.now();
  let isLightTheme = false;

  function checkTheme() {
    isLightTheme = document.documentElement.getAttribute('data-theme') === 'glass-light';
  }

  // --- Particle Network ---
  const PARTICLE_COUNT = 38;
  const CONNECTION_DIST = 160;
  const CONNECTION_DIST_SQ = CONNECTION_DIST * CONNECTION_DIST;
  let particles = [];

  function initParticles() {
    particles = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        phase: Math.random() * Math.PI * 2,
        freq: 0.0005 + Math.random() * 0.001,
        ampX: 0.2 + Math.random() * 0.4,
        ampY: 0.2 + Math.random() * 0.4,
        radius: 1 + Math.random() * 1.2,
        alpha: 0.3 + Math.random() * 0.4
      });
    }
  }

  // --- Orbes ---
  const orbes = [
    { // Blue accent - top-left
      color: [75, 139, 255],
      baseX: 0.2, baseY: 0.18,
      radius: 400,
      alpha: 0.10,
      phaseX: 0, phaseY: Math.PI * 0.5,
      freqX: 0.00015, freqY: 0.0002,
      ampX: 0.06, ampY: 0.05,
      parallaxFactor: 0.025
    },
    { // Violet/indigo - bottom-right
      color: [99, 102, 241],
      baseX: 0.78, baseY: 0.8,
      radius: 500,
      alpha: 0.09,
      phaseX: Math.PI * 0.7, phaseY: Math.PI * 1.3,
      freqX: 0.00012, freqY: 0.00018,
      ampX: 0.05, ampY: 0.06,
      parallaxFactor: 0.03
    },
    { // Teal/cyan - center-right
      color: [6, 182, 212],
      baseX: 0.7, baseY: 0.45,
      radius: 350,
      alpha: 0.08,
      phaseX: Math.PI * 1.2, phaseY: Math.PI * 0.3,
      freqX: 0.0002, freqY: 0.00015,
      ampX: 0.04, ampY: 0.05,
      parallaxFactor: 0.02
    },
    { // Saturated violet - bottom-left
      color: [124, 58, 237],
      baseX: 0.22, baseY: 0.75,
      radius: 450,
      alpha: 0.11,
      phaseX: Math.PI * 0.4, phaseY: Math.PI * 1.8,
      freqX: 0.00018, freqY: 0.00013,
      ampX: 0.05, ampY: 0.04,
      parallaxFactor: 0.028
    }
  ];

  // --- Time-based ambient color ---
  function getAmbientColor(hour) {
    // Returns [r, g, b, alpha] for ambient overlay
    // Smooth interpolation through the day
    const phases = [
      { h: 0,   color: [30, 20, 80],   a: 0.08 },  // Midnight: deep indigo
      { h: 5,   color: [30, 20, 80],   a: 0.07 },  // Late night: deep indigo
      { h: 6,   color: [180, 100, 40],  a: 0.06 },  // Dawn: warm orange
      { h: 8,   color: [120, 100, 60],  a: 0.03 },  // Morning transition
      { h: 10,  color: [60, 70, 80],    a: 0.02 },  // Morning: neutral
      { h: 14,  color: [20, 80, 120],   a: 0.03 },  // Afternoon: cyan
      { h: 17,  color: [180, 120, 30],  a: 0.05 },  // Sunset: amber gold
      { h: 19,  color: [160, 100, 40],  a: 0.05 },  // Late sunset
      { h: 21,  color: [80, 40, 130],   a: 0.06 },  // Evening: violet
      { h: 23,  color: [40, 25, 100],   a: 0.07 },  // Late evening
      { h: 24,  color: [30, 20, 80],    a: 0.08 }   // Midnight wrap
    ];

    // Find surrounding phases
    let lower = phases[0];
    let upper = phases[phases.length - 1];
    for (let i = 0; i < phases.length - 1; i++) {
      if (hour >= phases[i].h && hour < phases[i + 1].h) {
        lower = phases[i];
        upper = phases[i + 1];
        break;
      }
    }

    const t = (hour - lower.h) / (upper.h - lower.h);
    const smooth = t * t * (3 - 2 * t); // smoothstep
    return {
      r: lower.color[0] + (upper.color[0] - lower.color[0]) * smooth,
      g: lower.color[1] + (upper.color[1] - lower.color[1]) * smooth,
      b: lower.color[2] + (upper.color[2] - lower.color[2]) * smooth,
      a: lower.a + (upper.a - lower.a) * smooth
    };
  }

  function handleResize() {
    width = window.innerWidth;
    height = window.innerHeight;
    if (canvas) {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = width + 'px';
      canvas.style.height = height + 'px';
      if (ctx) {
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }
    }
    if (particles.length === 0) {
      initParticles();
    }
  }

  function handleMouseMove(e) {
    targetMouseX = e.clientX / width;
    targetMouseY = e.clientY / height;
  }

  function draw() {
    if (!ctx) return;

    const now = Date.now();
    const elapsed = now - startTime;

    // Smooth mouse tracking
    mouseX += (targetMouseX - mouseX) * 0.03;
    mouseY += (targetMouseY - mouseY) * 0.03;

    // Check theme each frame (cheap operation)
    checkTheme();

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Light theme base fill
    if (isLightTheme) {
      ctx.fillStyle = '#E8ECF2';
      ctx.fillRect(0, 0, width, height);
    }

    // --- Draw Orbes ---
    for (const orb of orbes) {
      const ox = (orb.baseX + Math.sin(elapsed * orb.freqX + orb.phaseX) * orb.ampX) * width;
      const oy = (orb.baseY + Math.cos(elapsed * orb.freqY + orb.phaseY) * orb.ampY) * height;

      // Mouse parallax offset
      const px = (mouseX - 0.5) * orb.parallaxFactor * width;
      const py = (mouseY - 0.5) * orb.parallaxFactor * height;

      const cx = ox + px;
      const cy = oy + py;

      const orbAlpha = isLightTheme ? orb.alpha * 0.5 : orb.alpha;
      const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, orb.radius);
      gradient.addColorStop(0, `rgba(${orb.color[0]}, ${orb.color[1]}, ${orb.color[2]}, ${orbAlpha})`);
      gradient.addColorStop(0.4, `rgba(${orb.color[0]}, ${orb.color[1]}, ${orb.color[2]}, ${orbAlpha * 0.5})`);
      gradient.addColorStop(1, `rgba(${orb.color[0]}, ${orb.color[1]}, ${orb.color[2]}, 0)`);

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(cx, cy, orb.radius, 0, Math.PI * 2);
      ctx.fill();
    }

    // --- Ambient overlay ---
    const date = new Date();
    const hourFrac = date.getHours() + date.getMinutes() / 60;
    const ambient = getAmbientColor(hourFrac);
    ctx.fillStyle = `rgba(${Math.round(ambient.r)}, ${Math.round(ambient.g)}, ${Math.round(ambient.b)}, ${ambient.a})`;
    ctx.fillRect(0, 0, width, height);

    // --- Update & Draw Particles ---
    for (const p of particles) {
      p.x += p.vx + Math.sin(elapsed * p.freq + p.phase) * p.ampX;
      p.y += p.vy + Math.cos(elapsed * p.freq + p.phase + 1.5) * p.ampY;

      // Wrap around edges
      if (p.x < -20) p.x = width + 20;
      if (p.x > width + 20) p.x = -20;
      if (p.y < -20) p.y = height + 20;
      if (p.y > height + 20) p.y = -20;
    }

    // Draw connections
    ctx.lineWidth = 0.4;
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const distSq = dx * dx + dy * dy;

        if (distSq < CONNECTION_DIST_SQ) {
          const dist = Math.sqrt(distSq);
          const alpha = (1 - dist / CONNECTION_DIST) * 0.15;
          ctx.strokeStyle = isLightTheme
            ? `rgba(80, 100, 140, ${alpha})`
            : `rgba(180, 200, 240, ${alpha})`;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }

    // Draw particles
    for (const p of particles) {
      ctx.fillStyle = isLightTheme
        ? `rgba(80, 100, 140, ${p.alpha * 0.6})`
        : `rgba(180, 200, 240, ${p.alpha})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fill();
    }

    // --- Vignette (dark only) ---
    if (!isLightTheme) {
      const vignetteGradient = ctx.createRadialGradient(
        width * 0.5, height * 0.5, Math.min(width, height) * 0.25,
        width * 0.5, height * 0.5, Math.max(width, height) * 0.75
      );
      vignetteGradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
      vignetteGradient.addColorStop(0.7, 'rgba(0, 0, 0, 0.05)');
      vignetteGradient.addColorStop(1, 'rgba(0, 0, 0, 0.35)');
      ctx.fillStyle = vignetteGradient;
      ctx.fillRect(0, 0, width, height);
    }

    animationId = requestAnimationFrame(draw);
  }

  onMount(() => {
    ctx = canvas.getContext('2d');
    handleResize();
    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);
    animationId = requestAnimationFrame(draw);
  });

  onDestroy(() => {
    if (animationId) cancelAnimationFrame(animationId);
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
    }
  });
</script>

<canvas bind:this={canvas} class="glass-bg"></canvas>

<style>
  .glass-bg {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: 0;
    pointer-events: none;
  }
</style>
