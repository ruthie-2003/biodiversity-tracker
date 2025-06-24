<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ref, computed } from 'vue'

const router = useRouter()

// User authentication state management
const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))
const token = ref(localStorage.getItem('token'))

// Computed properties for checking auth state
const isAuthenticated = computed(() => !!token.value)
const isAdmin = computed(() => user.value?.roles?.includes('admin'))

// Handles user logout - clears auth data and redirects
const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  token.value = null
  user.value = {}
  router.push('/auth/login')
}

// Handles new observation click - checks auth first
const handleNewObservation = () => {
  if (!isAuthenticated.value) {
    // Redirects to login if not authenticated
    router.push('/auth/login')
  } else {
    router.push('/upload')
  }
}
</script>

<template>
  <div class="app-container">
    <header class="main-header">
      <meta http-equiv="Content-Language" content="en-GB">
      <div class="header-content">
        <div class="logo">
          <h1>BioDiversity Tracker</h1>
        </div>
        <nav class="main-nav">
          <RouterLink to="/" class="nav-link">🏠 Home</RouterLink>
          <span @click.prevent="handleNewObservation" class="nav-link nav-action">⬆ New Observation</span>
          <RouterLink to="/visualizations" class="nav-link">📊 Visualizations</RouterLink>
          <RouterLink to="/profile" class="nav-link">👤 Profile</RouterLink>
          <RouterLink v-if="isAdmin" to="/admin/dashboard" class="nav-link">Dashboard</RouterLink>

          <RouterLink v-if="!isAuthenticated" to="/auth/login" class="nav-link login-link">Login</RouterLink>
          <button v-else class="nav-link logout-button" @click="handleLogout">Logout</button>
        </nav>
      </div>
    </header>
    
    <main>
      <RouterView v-slot="{ Component }">
        <Transition name="fade" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>

    <footer class="main-footer">
      <div class="footer-content">
        <div class="footer-section">
          <h3>BioDiversity Tracker</h3>
          <p>Citizen science platform for global biodiversity monitoring and conservation.</p>
        </div>
        <div class="footer-section">
          <h3>Quick Links</h3>
          <ul>
            <li><RouterLink to="/">Home</RouterLink></li>
            <li><RouterLink to="/upload" @click.prevent="handleNewObservation">New Observation</RouterLink></li>
            <li><RouterLink to="/visualizations">Visualizations</RouterLink></li>
            <li><RouterLink to="/profile">Profile</RouterLink></li>
          </ul>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; 2025 BioDiversity Tracker. All rights reserved.</p>
      </div>
    </footer>
  </div>
</template>

<style>
/* Global styles will be applied from style.css */
</style>
