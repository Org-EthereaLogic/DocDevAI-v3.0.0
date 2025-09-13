import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedState from 'pinia-plugin-persistedstate'
import router from './router'
import App from './App.vue'
import './style.css'

// Create Pinia instance
const pinia = createPinia()
pinia.use(piniaPluginPersistedState)

// Create Vue app
const app = createApp(App)

// Use plugins
app.use(pinia)
app.use(router)

// Mount app
app.mount('#app')
