import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'
import router from './router'

// Import global styles
import './assets/css/main.css'

// Create Vue app
const app = createApp(App)

// Create and configure Pinia store
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

// Install plugins
app.use(pinia)
app.use(router)

// Mount app
app.mount('#app')
