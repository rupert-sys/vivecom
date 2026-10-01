import type { CapacitorConfig } from '@capacitor/cli'

// Empaqueta el panel (React, ya compilado a dist/) como un APK real con Capacitor — el mismo código de
// panel.vivecom.com.mx, sin reescribir nada, a diferencia de mobile/ y caseta/ que sí son apps Flutter nativas.
// webDir: 'dist' (no server.url): los archivos estáticos viajan DENTRO del APK, así que la app abre aunque el
// dispositivo tenga mala señal — solo las llamadas a la API (VITE_API_URL, fijo en build time como en
// build-panel.sh) necesitan red real.
const config: CapacitorConfig = {
  appId: 'mx.vivecom.panel',
  appName: 'Panel Vivecom',
  webDir: 'dist',
}

export default config
