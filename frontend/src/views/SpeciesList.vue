<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import type { Species, Observation } from '../types'
import MapView from '../components/MapView.vue'
import LineChart from '../components/LineChart.vue'
import ImageGallery from '../components/ImageGallery.vue'
import PieChartView from '../components/PieChartView.vue'

const error = ref('')
const loading = ref(true)
const species = ref<Species | null>(null)
const recentObservations = ref<Observation[]>([])
const allSpeciesObservations = ref<Observation[]>([]) // For the chart

const route = useRoute()
const speciesName = computed(() => route.params.species_name?.toString())

// Calculates map center from first observation's coordinates
const mapCenter = computed(() => {
  if (allSpeciesObservations.value.length === 0) return [0, 0]
  return allSpeciesObservations.value[0].location.coordinates
})

// Fetches species details and related observations
const fetchSpeciesData = async () => {
  if (!speciesName.value) {
    error.value = 'Invalid species name.'
    loading.value = false
    return
  }

  try {
    const response = await axios.get(`http://localhost:8000/api/species/${speciesName.value}/`)
    species.value = response.data.species

    // Formats recent observations for map component
    recentObservations.value = response.data.recent_observations.map((obs: any) => ({
      ...obs,
      _id: obs._id,
      type: 'Point',
      location: {
        type: 'Point',
        coordinates: obs.location.coordinates,
        latitude: obs.location.latitude,
        longitude: obs.location.longitude
      },
      properties: {
        status: obs.status || 'pending',
        timestamp: obs.timestamp,
        location_name: obs.properties.location_name || 
                      obs.properties.region || 
                      obs.properties.country || 
                      'Unknown location',
        country: obs.properties.country,
        user_name: obs.properties.user_name || 'Unknown observer',
        user_profile_picture: obs.properties.user_profile_picture,
        photo: obs.photo,
        external_link: obs.external_link,
        source_id: obs.properties.source_id
      }
    }))

    // Fetches all observations for this species for the chart
    const allObsResponse = await axios.get(`http://localhost:8000/api/species/${speciesName.value}/observations/`)
    allSpeciesObservations.value = allObsResponse.data.features || []
    
  } catch (err: any) {
    error.value = 'Failed to fetch species data.'
    console.error(err)
  } finally {
    loading.value = false
  }
}

// Formats timestamp into readable date (DD/MM/YYYY)
const formatObservationDate = (timestamp: string) => {
  try {
    const date = new Date(timestamp);
    return isNaN(date.getTime()) 
      ? 'Invalid date' 
      : date.toLocaleDateString('en-GB', { 
          year: 'numeric', 
          month: 'short', 
          day: 'numeric' 
        });
  } catch {
    return 'Invalid date';
  }
};

onMounted(() => {
  fetchSpeciesData()
})
</script>

<template>
  <div class="species-detail-container">
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>Loading species details...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="fetchSpeciesData" class="retry-button">
        Try Again
      </button>
    </div>

    <template v-else-if="species">
      <!-- Species Header -->
      <header class="species-header">
        <h1>
          Species Information
        </h1>
      </header>

      <!-- Main Content -->
      <div class="species-content">
        <!-- Left Column - Species Info -->
        <div class="species-info">
          <!-- Species Photo -->
          <div class="species-photo" v-if="species.image_url">
            <img :src="species.image_url" :alt="species.species" class="species-image" />
          </div>

          <!-- Taxonomy Info -->
          <div class="info-section taxonomy-section">
            <h2>Taxonomy</h2>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">Family:</span>
                <span class="info-value">{{ species.family }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Genus:</span>
                <span class="info-value">{{ species.genus }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Species:</span>
                <span class="info-value">{{ species.species }}</span>
              </div>
            </div>
          </div>

          <!-- Distribution & Habitat -->
          <div class="info-section distribution-section">
            <h2>Distribution & Habitat</h2>
            <div class="map-container">
              <MapView :observations="allSpeciesObservations" :showEmptyState="allSpeciesObservations.length === 0" :center="mapCenter" />
            </div>
          </div>
        </div>

        <!-- Right Column - Data Visualization -->
        <div class="species-visualization">
          <div class="stats-section">
            <div class="name-card scientific-name">
              <h3>Scientific Name</h3>
              <p class="name-value">{{ species.species }}</p>
            </div>
            
            <div class="name-card common-name" v-if="species.common_name">
              <h3>Common Name</h3>
              <p class="name-value">{{ species.common_name}}</p>
            </div>
          </div>

          <!-- Observation Distribution Chart -->
          <div class="chart-section">
            <h2>Observation Statistics</h2>
            <LineChart :observations="allSpeciesObservations" />
          </div>

          <!-- Recent Observations -->
          <div class="recent-observations-section" v-if="recentObservations.length > 0">
            <h2>Recent Observations</h2>
            <ul class="observation-list">
              <li v-for="obs in recentObservations" :key="obs._id" class="observation-item">
                <router-link :to="`/observations/${obs.source_id}`">
                  <div class="observation-date">
                    {{ formatObservationDate(obs.properties.timestamp) }}
                  </div>
                  <div class="observation-location">
                    {{ obs.properties.location_name || obs.properties.region || obs.properties.country || 'Unknown location' }}
                  </div>
                  <div class="observation-status">
                    <span :class="['status-badge', obs.properties.status === 'verified' ? 'verified' : 'pending']">
                      {{ obs.properties.status || 'pending' }}
                    </span>
                  </div>
                  <div class="observation-users">
                    <span>
                      <img 
                        v-if="obs.properties.user_profile_picture" 
                        :src="obs.properties.user_profile_picture"
                        alt="User avatar"
                        class="user-avatar"
                      />
                      <span 
                        v-else 
                        class="inline-block h-6 w-6 text-xl align-middle"
                      >👤</span>
                    </span>
                    <span class="user-badge">
                      {{ obs.properties.user_name }}
                    </span>
                  </div>
                </router-link>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Back Link -->
      <div class="back-link">
        <button class="back-button" @click="$router.back()">
          &larr; Back
        </button>
      </div>
    </template>

    <div v-else class="empty-state">
      <p>No species found</p>
    </div>
  </div>
</template>

<style scoped>
.species-detail-container {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem;
}

.species-header {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-neutral-200);
}

.species-header h1 {
  font-size: var(--font-size-3xl);
  color: var(--color-primary-900);
  margin: 0;
  font-weight: 600;
  line-height: 1.2;
}

.common-name {
  font-weight: normal;
  color: var(--color-neutral-600);
}

.species-content {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 2rem;
  margin-bottom: 2rem;
}

.species-info {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.species-visualization {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.species-photo {
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.species-image {
  width: 100%;
  height: auto;
  display: block;
}

.info-section {
  background: white;
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-100);
}

.info-section h2 {
  font-size: var(--font-size-xl);
  color: var(--color-primary-800);
  margin-bottom: 1rem;
  font-weight: 600;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-neutral-100);
}

.info-label {
  font-weight: 600;
  color: var(--color-neutral-700);
}

.info-value {
  color: var(--color-neutral-800);
}

.description {
  color: var(--color-neutral-700);
  line-height: 1.6;
}

.map-section {
  width: 100%;
}

.map-container {
  height: 400px;
  width: 100%;
  position: relative;
  display: flex;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-neutral-100);
}

.map-container > * {
  flex-grow: 1;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.name-card {
  background: white;
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-100);
  transition: all 0.2s ease;
}

.name-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.name-card h3 {
  font-size: var(--font-size-lg);
  color: var(--color-primary-800);
  margin-bottom: 0.75rem;
  font-weight: 600;
}

.name-value {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-primary-900);
  margin-bottom: 0.5rem;
}

.name-details {
  font-size: var(--font-size-sm);
  color: var(--color-neutral-600);
  display: flex;
  gap: 0.75rem;
}

.name-details span {
  background: var(--color-primary-50);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
}

.scientific-name {
  border-left: 4px solid var(--color-primary-500);
}

.common-name {
  border-left: 4px solid var(--color-success-500);
}

.recent-observations-section {
  background: white;
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-100);
}

.observation-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.observation-item {
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--color-neutral-100);
}

.observation-item:last-child {
  border-bottom: none;
}

.observation-item a {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  width: 100%;
  gap: 1rem;
  text-decoration: none;
  color: inherit;
  padding: 0.5rem;
  border-radius: var(--radius-md);
}

.observation-item a:hover {
  background-color: var(--color-neutral-50);
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.status-badge.verified {
  background-color: var(--color-success-500);
  color: white;
}

.status-badge.pending {
  background-color: var(--color-warning-500);
  color: white;
}

.user-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 600;
  background-color: var(--color-neutral-100);
  color: var(--color-neutral-700);
}

.user-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
}

.back-link {
  margin-top: 2rem;
  text-align: center;
}

.back-button {
  display: inline-block;
  padding: 0.5rem 1rem;
  background-color: var(--color-primary-600);
  color: white;
  border-radius: var(--radius-md);
  text-decoration: none;
  transition: background-color var(--transition-fast);
}

.back-button:hover {
  background-color: var(--color-primary-700);
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 5px solid var(--color-neutral-100);
  border-top: 5px solid var(--color-primary-600);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1.5rem;
}

.retry-button {
  margin-top: var(--space-2);
}

.chart-section {
  background: white;
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-100);
  margin-bottom: 2rem;
}

.chart-section h2 {
  font-size: var(--font-size-xl);
  color: var(--color-primary-800);
  margin-bottom: 1rem;
  font-weight: 600;
}
 
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Responsive adjustments */
@media (max-width: 1024px) {
  .species-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .species-detail-container {
    padding: 1.5rem;
  }

  .species-header h1 {
    font-size: var(--font-size-2xl);
  }

  .observation-item {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto;
    gap: 0.5rem;
  }

  .observation-date {
    grid-column: 1 / 2;
  }

  .observation-location {
    grid-column: 2 / 3;
  }

  .observation-status {
    grid-column: 1 / 2;
    grid-row: 2 / 3;
  }

  .observation-users {
    grid-column: 2 / 3;
    grid-row: 2 / 3;
    text-align: right;
  }
}
</style>