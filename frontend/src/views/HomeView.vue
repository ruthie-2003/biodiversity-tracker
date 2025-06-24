<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import SearchBar from '../components/SearchBar.vue'
import { RouterLink } from 'vue-router'

const search = ref('')

// These control the scroll animations for each section
// We'll reveal them when the user scrolls to that part of the page
const statsVisible = ref(false)
const featuredVisible = ref(false)
const uploadsVisible = ref(false)

// Stores the stats we fetch from the backend
// Initialized with zeros that will be replaced after API call
const stats = ref({
  speciesCount: 0,
  contributorCount: 0,
  observationCount: 0
})

const uploads = ref<any[]>([])

// Fetches the summary stats for the homepage counters
const fetchHomepageStats = async () => {
  try {
    const res = await axios.get('/api/homepage/stats/')
    stats.value = res.data
  } catch (error) {
    console.error('Failed to fetch homepage stats', error)
  }
}

// Gets the most recent observations to display in the gallery
const fetchRecentUploads = async () => {
  try {
    const res = await axios.get('/api/homepage/uploads/')
    uploads.value = res.data
    console.log('Fetched uploads:', res.data)
  } catch (error) {
    console.error('Failed to fetch recent uploads', error)
  }
}

onMounted(() => {
  fetchHomepageStats()
  fetchRecentUploads()

  const observerOptions = {
    threshold: 0.2,
    rootMargin: '0px 0px -100px 0px'
  }

  // This observer handles all our scroll-triggered animations
  // It checks which section is coming into view and updates the corresponding ref
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        if (entry.target.id === 'stats-section') statsVisible.value = true
        else if (entry.target.id === 'featured-section') featuredVisible.value = true
        else if (entry.target.id === 'uploads-section') uploadsVisible.value = true
      }
    })
  }, observerOptions)

  const sections = document.querySelectorAll('.animate-on-scroll')
  sections.forEach(section => observer.observe(section))
})
</script>

<template>
  <div class>
    <section class="intro">
      <div class="intro-content">
        <h2>Track and Visualize Biodiversity Data</h2>
        <p class="intro-description">Join our citizen science platform to contribute to global biodiversity monitoring and conservation</p>
        <SearchBar v-model:search="search" />
      </div>
    </section>

    <section id="stats-section" class="stats animate-on-scroll" :class="{ 'visible': statsVisible }">
      <div class="stat-box">
        <div class="stat-number">{{ stats.speciesCount }}</div>
        <div class="stat-label">Species Recorded</div>
      </div>
      <div class="stat-box">
        <div class="stat-number">{{ stats.contributorCount }}</div>
        <div class="stat-label">Active Contributors</div>
      </div>
      <div class="stat-box">
        <div class="stat-number">{{ stats.observationCount }}</div>
        <div class="stat-label">Observations</div>
      </div>
    </section>

    <section id="uploads-section" class="uploads animate-on-scroll" :class="{ 'visible': uploadsVisible }">
      <h3>Recent Observations</h3>
      <div class="upload-grid">
        <RouterLink class="upload-card" v-for="upload in uploads" :key="upload.source_id" :to="`/observations/${upload.source_id}`">
          <div class="photo-placeholder">
            <template v-if="upload.photos && upload.photos.length > 0">
              <img 
                :src="upload.photos[0]" 
                :alt="upload.species"
              />
            </template>
            <span v-else>Species Photo</span>
          </div>
          <div class="upload-info">
            <div class="upload-header">
              <span class="upload-species">{{ upload.species }}</span>
              <span class="upload-date">{{ upload.date }}</span>
            </div>
            <p class="upload-description">{{ upload.description }}</p>
            <div class="upload-footer">
              <div class="upload-user">
                <span>👤 {{ upload.user }}</span>
              </div>
              <div class="upload-location">
                <span>📍 {{ upload.location }}</span>
              </div>
            </div>
          </div>
        </RouterLink>
      </div>
    </section>

    <section id="featured-section" class="featured animate-on-scroll" :class="{ 'visible': featuredVisible }">
      <h3>Featured Visualizations</h3>
      <div class="viz-container">
        <div class="viz-box">
          <strong>Interactive Map View</strong>
          <p>Species Distribution Map<br>Geographic visualization of recorded species</p>
        </div>
        <div class="viz-box">
          <strong>Chart View</strong>
          <p>Species Trends<br>Population trends over time</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>

.intro {
  background: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.7)), url('https://images.pexels.com/photos/1287075/pexels-photo-1287075.jpeg?auto=compress&cs=tinysrgb&w=1920');
  background-size: cover;
  background-position: center;
  color: white;
  text-align: center;
  padding: var(--space-6) var(--space-2);
  margin-bottom: var(--space-4);
  width: 100%;
}

.intro-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-2);
}

.intro h2 {
  color: white;
  font-size: var(--font-size-3xl);
  margin-bottom: var(--space-2);
}

.intro-description {
  font-size: var(--font-size-lg);
  margin-bottom: var(--space-3);
  opacity: 0.9;
}

.stats {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  opacity: 0;
  transform: translateY(30px);
  transition: opacity var(--transition-slow), transform var(--transition-slow);
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
  padding: 0 var(--space-2);
}

.stats.visible {
  opacity: 1;
  transform: translateY(0);
}

.stat-box {
  flex: 1;
  background: white;
  padding: var(--space-3);
  text-align: center;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border-bottom: 4px solid var(--color-primary-600);
  transition: transform var(--transition-normal);
}

.stat-box:hover {
  transform: translateY(-5px);
}

.stat-number {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-primary-700);
  margin-bottom: var(--space-1);
}

.stat-label {
  font-size: var(--font-size-md);
  color: var(--color-neutral-700);
}

.featured {
  margin-bottom: var(--space-4);
  opacity: 0;
  transform: translateY(30px);
  transition: opacity var(--transition-slow), transform var(--transition-slow);
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
  padding: 0 var(--space-2);
}

.featured.visible {
  opacity: 1;
  transform: translateY(0);
}

.featured h3 {
  text-align: center;
  margin-bottom: var(--space-3);
  color: var(--color-neutral-900);
  font-size: var(--font-size-2xl);
}

.viz-container {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
}

.viz-box {
  flex: 1;
  padding: var(--space-3);
  background: white;
  border-radius: var(--radius-lg);
  text-align: center;
  text-decoration: none;
  color: var(--color-neutral-900);
  box-shadow: var(--shadow-md);
  transition: transform var(--transition-normal);
}

.viz-box:hover {
  transform: translateY(-5px);
}

.viz-box strong {
  display: block;
  font-size: var(--font-size-xl);
  margin-bottom: var(--space-2);
  color: var(--color-primary-700);
}

.viz-box p {
  color: var(--color-neutral-600);
  line-height: 1.5;
}

.uploads {
  margin-bottom: var(--space-4);
  opacity: 0;
  transform: translateY(30px);
  transition: opacity var(--transition-slow), transform var(--transition-slow);
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
  padding: 0 var(--space-2);
}

.uploads.visible {
  opacity: 1;
  transform: translateY(0);
}

.uploads h3 {
  text-align: center;
  margin-bottom: var(--space-3);
  color: var(--color-neutral-900);
  font-size: var(--font-size-2xl);
}

.upload-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.upload-card {
  background: white;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  transition: transform var(--transition-normal);
}

.upload-card:hover {
  transform: translateY(-5px);
}

.photo-placeholder {
  height: 200px;
  background: var(--color-neutral-200);
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

.photo-placeholder img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}


.upload-info {
  padding: var(--space-2);
}

.upload-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.upload-species {
  font-weight: 600;
  color: var(--color-primary-700);
}

.upload-date {
  font-size: var(--font-size-sm);
  color: var(--color-neutral-500);
}

.upload-description {
  color: var(--color-neutral-700);
  margin-bottom: var(--space-2);
  line-height: 1.5;
}

.upload-footer {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-sm);
  color: var(--color-neutral-600);
}

@media (max-width: 1024px) {
  .viz-container {
    flex-direction: column;
  }

  .upload-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats {
    flex-direction: column;
  }

  .upload-grid {
    grid-template-columns: 1fr;
  }

  .intro h2 {
    font-size: var(--font-size-2xl);
  }
}
</style>