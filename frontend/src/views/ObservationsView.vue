<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import type { DetailedObservation, Observation } from '../types'
import MapView from '../components/MapView.vue'
import ImageGallery from '../components/ImageGallery.vue'
import CommentSection from '../components/CommentSection.vue'

const error = ref('')
const loading = ref(true)
const observation = ref<DetailedObservation | null>(null)
const activeImage = ref(0)
const mapObservations = ref<Observation[]>([])

const route = useRoute()
const router = useRouter()

const rawId = computed(() => route.params.source_id)

const observationId = computed(() => {
  const raw = rawId.value?.toString().trim()
  const id = Number(raw)
  return isNaN(id) ? null : id
})

// Converts the detailed observation to a simplified format for the map component
function convertToMapObservation(obs: DetailedObservation): Observation {
  return {
    type: 'Feature',
    location: {
      type: 'Point',
      coordinates: obs.location.coordinates, // GeoJSON format
      latitude: obs.location.latitude,
      longitude: obs.location.longitude,
    },
    properties: {
      species: obs.species_name, 
      genus: obs.properties.genus,
      family: obs.properties.family,
      timestamp: obs.properties.timestamp,
      location_name: obs.properties.location_name || '',
      region: obs.properties.region || '',
      country: obs.properties.country || '',
      photo: obs.properties.photo || [],
      external_link: obs.properties.external_link || ''
    }
  }
}

// Fetches the full observation details from the API
const fetchObservationDetail = async () => {
  if (observationId.value == null) {
    error.value = 'Invalid observation ID.'
    loading.value = false
    return
  }
  
  try {
    // Gets auth token from localStorage (if exists)
    const token = localStorage.getItem('token')

    const response = await axios.get(`http://localhost:8000/api/observations/${observationId.value}/`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )

    observation.value = response.data
    
    // Ensures comments array exists even if empty
    if (!observation.value?.comments) {
      observation.value && (observation.value.comments = [])
    }

    // Prepares map data if we have coordinates
    if (observation.value?.location?.coordinates) {
      mapObservations.value = [convertToMapObservation(observation.value)]
    } else {
      // If no location, clears the map data.
      mapObservations.value = []
    }
  } catch (err: unknown) {
    if (axios.isAxiosError(err)) {
      const data = err.response?.data
      error.value = data?.error || data?.message || 'Error fetching data.'
    } else {
      error.value = 'Unexpected error occurred.'
    }
    console.error('Fetch error:', err)
  } finally {
    loading.value = false
  }
}

// Checks if current user can edit this observation
const canEdit = computed(() => {
  if (!observation.value) return false
  return observation.value.is_current_user || observation.value.is_admin
})


// Navigates to edit page with observation ID as query param
const goToEditPage = () => {
  if (!observation.value) return;

  router.push({
    path: '/upload', 
    query: {
      edit: 'true',
      source_id: observation.value.source_id,
    },
  });
};

onMounted(async () => {
    await fetchObservationDetail()
})
</script>

<template v-if="observation && observation._id">
  <div class="observation-detail-container">
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>Loading observation details...</p>
    </div>
    
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="fetchObservationDetail" class="retry-button">
        Try Again
      </button>
    </div>
    
    <template v-else-if="observation">
      <!-- Species Header -->
      <header class="observation-header">
        <h1>
          <template v-if="observation.species_name !== 'All'">
            <router-link 
              :to="`/species/${encodeURIComponent(observation.species_name)}`"
              class="species-link"
              title="View species details"
            >
              {{ observation.user_title }}
            </router-link>
          </template>
          <template v-else>
            <span class="species-link-disabled">{{ observation.user_title }}</span>
          </template>
        </h1>

        <!-- Edit Button -->
        <div class="edit-observation-button" v-if="canEdit">
          <button @click="goToEditPage" class="edit-button">
            ✏️ Edit Observation
          </button>
        </div>
      </header>
      
      <!-- Info Cards Section -->
      <div class="info-cards">
        <div class="info-card taxonomy-card">
          <div class="info-card-icon">
            <span class="material-icon">🧬</span>
          </div>
          <div class="info-card-content">
            <h3>Taxonomy</h3>
            <p v-if="observation.properties"><strong>Family:</strong> {{ observation.properties.family }}</p>
            <p v-if="observation.properties"><strong>Genus:</strong> {{ observation.properties.genus }}</p>
            <p><strong>Species:</strong> {{ observation.species_name }}</p>
          </div>
        </div>
        
        <div class="info-card status-card">
          <div class="info-card-icon">
            <span class="material-icon">✓</span>
          </div>
          <div class="info-card-content">
            <h3>Status</h3>
            <p>{{ observation.status === 'verified' ? 'Verified' : 'Pending' }}</p>
          </div>
        </div>
        
        <div class="info-card location-card">
          <div class="info-card-icon">
            <span class="material-icon">📍</span>
          </div>
          <div class="info-card-content">
            <h3>Location</h3>
            <p>  
              {{
                observation.properties.location_name
                  ? observation.properties.location_name
                  : observation.properties.region
                  ? observation.properties.region
                  : ''
              }}
            </p>
            <p>{{ observation.properties.country || 'N/A' }}</p>
          </div>
        </div>
        
        <div class="info-card observer-card">
          <div class="info-card-icon">
            <img
              v-if="observation.user_id && observation.user_profile_picture"
              :src="observation.user_profile_picture"
              alt="Observer profile"
              class="observer-avatar"
            />
            <span v-else class="material-icon">👤</span>
          </div>
          <div class="info-card-content">
            <h3>Observer</h3>
            <p>{{ observation.user_name }}</p>
          </div>
        </div>
      </div>
      
      <!-- Image Gallery -->
      <section 
        class="gallery-section" 
        :class="{
          'single-image': observation?.properties?.photo?.length === 1,
          'multiple-images': observation?.properties?.photo?.length > 1
        }"
        v-if="observation?.properties?.photo?.length"
      >
        <h2>Image Gallery</h2>
        <ImageGallery :images="observation.properties.photo" />
      </section>
      
      <!-- Audio Section -->
      <section class="audio-section" v-if="observation.properties.audio && observation.properties.audio.length > 0">
        <h2>Audio Recordings</h2>
        <div class="audio-player-list">
          <div v-for="(audioUrl, index) in observation.properties.audio" :key="index" class="audio-item">
            <p>Recording {{ index + 1 }}</p>
            <audio controls :src="audioUrl">
              Your browser does not support the audio element.
            </audio>
          </div>
        </div>
      </section>
      
      <!-- Map Visualization -->
      <section class="map-section">
        <h2>Data Visualization</h2>
        <div class="map-container">
          <MapView :observations="mapObservations" :showEmptyState="mapObservations.length === 0" />
        </div>
      </section>
      
      <!-- Comments Section -->
      <section class="comments-section">
        <h2>Comments ({{ observation.comments_count || 0 }})</h2>
        <CommentSection
          v-if="observationId !== null"
          :observationId="observationId"
          :comments="observation.comments || []"
          @commentAdded="fetchObservationDetail"
        />
      </section>
    </template>
    
    <div v-else class="empty-state">
      <p>No observation found</p>
    </div>
  </div>
</template>

<style scoped>

.species-link-disabled {
  color: var(--color-primary-900);
  cursor: default;
}

.species-link {
  color: inherit;
  text-decoration: none;
  transition: color var(--transition-fast);
}

.species-link:hover {
  color: var(--color-primary-600);
  text-decoration: underline;
}

.observation-detail-container {
  max-width: none;
  width: 100%;
  margin: 0 auto;
  padding: 3rem 2rem;
}

.observation-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-neutral-200);
}

.observation-header h1 {
  font-size: var(--font-size-3xl);
  color: var(--color-primary-900);
  margin: 0;
  font-weight: 600;
  line-height: 1.2;
  animation: fadeIn 0.5s ease-in-out;
}

.info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1.75rem;
  margin-bottom: 1rem;
}

.info-card {
  background: white;
  border-radius: var(--radius-lg);
  padding: 2rem;
  box-shadow: var(--shadow-sm);
  display: flex;
  align-items: flex-start;
  transition: all var(--transition-normal) ease;
  animation: slideIn 0.4s ease-out;
  border: 1px solid var(--color-neutral-100);
}

.info-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary-100);
}

.info-card-icon {
  margin-right: 1.25rem;
  font-size: 1.75rem;
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-50);
  border-radius: 50%;
  color: var(--color-primary-700);
  flex-shrink: 0;
}

.info-card-content h3 {
  margin-bottom: 0.75rem;
  font-size: var(--font-size-lg);
  color: var(--color-primary-800);
  font-weight: 600;
}

.info-card-content p {
  margin-bottom: 0.5rem;
  color: var(--color-neutral-700);
  line-height: 1.5;
}

.observer-avatar {
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--color-primary-100); /* optional border for visual consistency */
}

.edit-observation-button {
  margin-top: 1rem;
  text-align: right;
}

.edit-button {
  background-color: var(--color-primary-600);
  color: white;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: var(--radius-md);
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
}

.edit-button:hover {
  background-color: var(--color-primary-700);
}

.audio-section,
.map-section,
.comments-section {
  margin-bottom: 1rem;
  animation: fadeIn 0.6s ease-in-out;
}

.gallery-section h2,
.audio-section h2,
.map-section h2,
.comments-section h2 {
  font-size: var(--font-size-2xl);
  margin-bottom: 2rem;
  padding-top: 1rem;
  color: var(--color-primary-800);
  border-bottom: 2px solid var(--color-primary-100);
  padding-bottom: 1rem;
  font-weight: 600;
}

.gallery-section {
  margin-bottom: 1rem;
  animation: fadeIn 0.6s ease-in-out;
  width: 100%;
}

/* Force images to fill container */
.gallery-section :deep(img) {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  transition: transform 0.3s ease;
}

/* Single image treatment */
.gallery-section.single-image :deep(img) {
  width: 100%;
  object-fit: contain;
  margin: 0;
}


.gallery-section :deep(.image-gallery-wrapper) {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  justify-content: stretch;
}

.gallery-section :deep(.image-gallery-wrapper img) {
  flex: 1 1 100%;
}


.map-container {
  height: 350px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-neutral-100);
}

.audio-player {
  background: white;
  padding: 1.5rem;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-neutral-100);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.audio-player audio {
  width: 100%;
}

.audio-section {
  margin-bottom: 2rem;
  animation: fadeIn 0.6s ease-in-out;
  background: var(--color-neutral-50);
  border-radius: var(--radius-lg);
  padding: 1.5rem 2rem;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-neutral-200);
}

.audio-section h2 {
  font-size: var(--font-size-2xl);
  margin-bottom: 1.5rem;
  color: var(--color-primary-800);
  font-weight: 700;
  border-bottom: 2px solid var(--color-primary-200);
  padding-bottom: 0.5rem;
}

.audio-player-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.audio-item {
  background: white;
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-150);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  transition: box-shadow 0.3s ease, border-color 0.3s ease;
}

.audio-item:hover {
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary-300);
}

.audio-item p {
  font-weight: 600;
  color: var(--color-primary-700);
  margin: 0;
  font-size: var(--font-size-md);
}

.audio-item audio {
  width: 100%;
  outline: none;
  border-radius: var(--radius-sm);
  box-shadow: inset 0 0 5px rgba(0,0,0,0.1);
  cursor: pointer;
  transition: box-shadow 0.2s ease-in-out;
}

.audio-item audio:focus,
.audio-item audio:hover {
  box-shadow: 0 0 8px var(--color-primary-400);
}

.play-button {
  background-color: var(--color-primary-600);
  color: white;
  border: none;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.play-button:hover {
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

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .observation-detail-container {
    padding: 2rem 1.25rem;
  }

  .info-cards {
    grid-template-columns: 1fr;
    gap: 1.25rem;
  }

  .info-card {
    padding: 1.5rem;
  }
  
  .observation-header h1 {
    font-size: var(--font-size-2xl);
  }
  
  .gallery-section.single-image :deep(img) {
    max-height: 50vh;
  }
  
  .gallery-section h2,
  .audio-section h2,
  .map-section h2,
  .comments-section h2 {
    font-size: var(--font-size-xl);
    margin-bottom: 1.5rem;
  }

  .map-container {
    height: 350px;
  }
}
</style>