<script>
  import { onMount } from 'svelte';
  import { createEventDispatcher } from 'svelte';
  import logoUrl from '../../assets/logo.png';

  const dispatch = createEventDispatcher();

  let progress = 0;
  let statusText = 'Initialisation...';
  let visible = true;
  let fadeOut = false;

  const steps = [
    { pct: 15, text: 'Chargement des modules...' },
    { pct: 35, text: 'Connexion au backend...' },
    { pct: 55, text: 'Chargement des donn\u00e9es...' },
    { pct: 75, text: 'Pr\u00e9paration de l\'interface...' },
    { pct: 90, text: 'Presque pr\u00eat...' },
    { pct: 100, text: 'Bienvenue !' },
  ];

  onMount(() => {
    let stepIdx = 0;
    const interval = setInterval(() => {
      if (stepIdx < steps.length) {
        progress = steps[stepIdx].pct;
        statusText = steps[stepIdx].text;
        stepIdx++;
      } else {
        clearInterval(interval);
        setTimeout(() => {
          fadeOut = true;
          setTimeout(() => {
            visible = false;
            dispatch('done');
          }, 600);
        }, 300);
      }
    }, 400);

    return () => clearInterval(interval);
  });
</script>

{#if visible}
  <div class="splash" class:fade-out={fadeOut}>
    <div class="splash-content">
      <!-- Logo / Icon -->
      <div class="splash-logo">
        <img src={logoUrl} alt="Logo" class="splash-logo-img" />
        <div class="splash-rings">
          <div class="ring ring-1"></div>
          <div class="ring ring-2"></div>
          <div class="ring ring-3"></div>
        </div>
      </div>

      <!-- Title -->
      <h1 class="splash-title">ITManager</h1>
      <p class="splash-subtitle">Dashboard</p>

      <!-- Progress bar -->
      <div class="splash-progress-container">
        <div class="splash-progress-bar" style="width:{progress}%"></div>
      </div>

      <!-- Status text -->
      <p class="splash-status">{statusText}</p>
    </div>
  </div>
{/if}

<style>
  .splash {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 999999;
    background: #070B14;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: opacity 0.6s ease, transform 0.6s ease;
  }

  .splash.fade-out {
    opacity: 0;
    transform: scale(1.05);
  }

  .splash-content {
    text-align: center;
    animation: splashIn 0.8s ease-out;
  }

  .splash-logo {
    position: relative;
    width: 100px;
    height: 100px;
    margin: 0 auto 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .splash-logo-img {
    width: 72px;
    height: 72px;
    object-fit: contain;
    z-index: 2;
    position: relative;
    filter: drop-shadow(0 0 20px rgba(6, 166, 201, 0.4));
    animation: iconPulse 2s ease-in-out infinite;
  }
  .splash-icon {
    font-size: 48px;
    z-index: 2;
    position: relative;
    filter: drop-shadow(0 0 20px rgba(6, 166, 201, 0.5));
    animation: iconPulse 2s ease-in-out infinite;
  }

  .splash-rings {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
  }

  .ring {
    position: absolute;
    border: 2px solid rgba(6, 166, 201, 0.3);
    border-radius: 50%;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    animation: ringExpand 2.5s ease-out infinite;
  }

  .ring-1 { width: 70px; height: 70px; animation-delay: 0s; }
  .ring-2 { width: 70px; height: 70px; animation-delay: 0.8s; }
  .ring-3 { width: 70px; height: 70px; animation-delay: 1.6s; }

  .splash-title {
    font-size: 32px;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.5px;
    margin-bottom: 4px;
  }

  .splash-subtitle {
    font-size: 14px;
    color: rgba(148, 163, 184, 0.7);
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-bottom: 32px;
  }

  .splash-progress-container {
    width: 240px;
    height: 4px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 2px;
    margin: 0 auto 16px;
    overflow: hidden;
  }

  .splash-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #06A6C9, #7c3aed);
    border-radius: 2px;
    transition: width 0.4s ease;
    box-shadow: 0 0 12px rgba(6, 166, 201, 0.4);
  }

  .splash-status {
    font-size: 12px;
    color: rgba(148, 163, 184, 0.5);
    min-height: 18px;
    transition: opacity 0.2s;
  }

  @keyframes splashIn {
    from {
      opacity: 0;
      transform: translateY(20px) scale(0.95);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  @keyframes iconPulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.08); }
  }

  @keyframes ringExpand {
    0% {
      width: 70px;
      height: 70px;
      opacity: 0.6;
      border-color: rgba(6, 166, 201, 0.4);
    }
    100% {
      width: 140px;
      height: 140px;
      opacity: 0;
      border-color: rgba(6, 166, 201, 0);
    }
  }
</style>
