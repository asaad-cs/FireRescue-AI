import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Dark background layers
        'bg-base': '#080b10',
        'bg-surface': '#0f1520',
        'bg-raised': '#17202e',
        'bg-overlay': '#1e2a3a',

        // Borders
        'border-subtle': '#1a2435',
        'border-default': '#253347',
        'border-strong': '#35485e',

        // Text
        'text-primary': '#dde6f0',
        'text-secondary': '#8097b0',
        'text-muted': '#445566',
        'text-dim': '#2d3d50',

        // Hazard zone fills
        hazard: {
          unobserved: '#0d1520',
          clear: '#081e14',
          low: '#0d2a1a',
          moderate: '#2e1e00',
          high: '#351000',
          critical: '#420a0a',
          // Hazard text colors
          'unobserved-text': '#2a3f55',
          'clear-text': '#22c55e',
          'low-text': '#4ade80',
          'moderate-text': '#f59e0b',
          'high-text': '#f97316',
          'critical-text': '#ef4444',
        },

        // Alert level fills and borders
        alert: {
          'info-bg': '#071828',
          'info-border': '#1e4d7a',
          'info-text': '#60a5fa',
          'warning-bg': '#1e1200',
          'warning-border': '#7a4d00',
          'warning-text': '#fbbf24',
          'critical-bg': '#200808',
          'critical-border': '#7a1818',
          'critical-text': '#f87171',
          'emergency-bg': '#2a0000',
          'emergency-border': '#cc0000',
          'emergency-text': '#ffffff',
        },

        // Mission status indicator colors
        status: {
          active: '#22c55e',
          idle: '#64748b',
          ended: '#475569',
          error: '#ef4444',
          paused: '#f59e0b',
          connecting: '#60a5fa',
          lost: '#ef4444',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
    },
  },
  plugins: [],
} satisfies Config;
