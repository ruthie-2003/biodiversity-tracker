<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'
import FilterPanel from '../components/FilterPanel.vue'
import MapView from '../components/MapView.vue'
import PieChartView from '../components/PieChartView.vue'
import LineChartView from '../components/LineChart.vue'
import type { Observation, FilterOptions } from '../types'

const observations = ref<Observation[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)
const hasActiveFilters = ref<boolean>(false)

// Default filter values
const filterOptions = ref<FilterOptions>({
  family: 'All',
  genus: 'All',
  species: 'All',
  continent: 'All Continents',
  startDate: '2025-01-01',
  endDate: '2025-12-31',
  showOnlyMyObservations: false,
})

// Handles filter changes from the FilterPanel component
const handleFilterChange = async (newFilters: FilterOptions) => {
  filterOptions.value = newFilters
  // Determines if any meaningful filters are active (not just defaults)
  hasActiveFilters.value = newFilters.family !== 'All' || 
                          newFilters.genus !== 'All' || 
                          newFilters.species !== 'All' ||
                          newFilters.continent !== 'All Continents' ||
                          (newFilters.showOnlyMyObservations ?? false)
  await loadObservations()
}

// Fetches observations based on current filters
const loadObservations = async () => {
  try {
    isLoading.value = true
    error.value = null
    
    // Skips API call if no meaningful filters are set
    if (!hasActiveFilters.value) {
      observations.value = []
      return
    }

    const params: Record<string, any> = {
      start_date: filterOptions.value.startDate,
      end_date: filterOptions.value.endDate
    }

    // Only includes non-default filters in the API call
    if (filterOptions.value.family !== 'All') params.family = filterOptions.value.family
    if (filterOptions.value.genus !== 'All') params.genus = filterOptions.value.genus
    if (filterOptions.value.species !== 'All') params.species = filterOptions.value.species
    if (filterOptions.value.continent !== 'All Continents') {
      params.continent = filterOptions.value.continent
    }
    if (filterOptions.value.showOnlyMyObservations) {
      params.show_only_my_observations = true
    }

    const response = await axios.get('http://localhost:8000/api/filter_observations/', { 
      params,
      timeout: 10000,
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token') || ''}`
      }
    })
    
    if (response.status === 200) {
      observations.value = response.data.features || response.data || []
    }
  } catch (err) {
    if (axios.isAxiosError(err)) {
      if (err.response?.status === 400) {
        error.value = 'Invalid filters provided'
      } else if (err.response?.status === 500) {
        error.value = 'Server error - please try again later'
      } else {
        error.value = 'Failed to load data'
      }
    } else {
      error.value = 'Network error'
    }
    observations.value = []
  } finally {
    isLoading.value = false
  }
}


onMounted(() => {
  loadObservations()
})

// Watches for filter changes and automatically reloads data
watch(filterOptions, loadObservations, { deep: true })

</script>

<template>
  <div class="page-container">
    <h1>Biodiversity Visualizations</h1>

    <FilterPanel 
      :filterOptions="filterOptions"
      @filter-changed="handleFilterChange"
    />

    <div v-if="isLoading" class="loading-container">
      <p>Loading observation data...</p>
    </div>

    <div v-else-if="error" class="error-container">
      <p>{{ error }}</p>
      <button @click="loadObservations">Retry</button>
    </div>

    <div v-else class="visualizations-container">
      <!-- First Column: Map -->
      <div class="main-visualization">
        <div class="map-container">
          <h2>Species Distribution Map</h2>
          <MapView :observations="observations" :show-empty-state="!hasActiveFilters"/>
        </div>

        <!-- Moved Observation Trends here -->
        <div class="chart-card">
          <h2>Observation Trends</h2>
          <LineChartView :observations="observations" />
        </div>
      </div>

      <!-- Second Column: Other Charts -->
      <div class="side-charts">
        <div class="chart-card">
          <h2>Species Distribution</h2>
          <PieChartView :observations="observations" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-2);
  font-family: var(--font-family-base);
}

.loading-container,
.error-container {
  text-align: center;
  padding: 2rem;
}

.visualizations-container {
  display: grid;
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.main-visualization {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.map-container,
.chart-card {
  background-color: var(--color-surface);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 1.5rem;
  transition: box-shadow 0.3s ease;
}

.map-container:hover,
.chart-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

h1 {
  color: var(--color-primary);
  margin-bottom: 1.5rem;
}

h2 {
  color: var(--color-secondary);
  margin-top: 0;
  margin-bottom: 1rem;
}

@media (min-width: 768px) {
  .visualizations-page {
    padding: 2rem;
  }

  .visualizations-container {
    grid-template-columns: 1fr;
  }

  .charts-container {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .chart-card {
    flex: 1 1 45%;
  }
}

@media (min-width: 1024px) {
  .visualizations-container {
    grid-template-columns: 2fr 1fr;
  }

  .map-container {
    flex: 3;
  }

  .charts-container {
    flex: 2;
    flex-direction: column;
  }

  .chart-card {
    flex: 1;
  }
}
</style>