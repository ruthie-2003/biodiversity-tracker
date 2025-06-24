
<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue';
import axios from 'axios';
import type { FilterOptions, TaxaOptions } from '../types';

const filterOptions = defineModel<FilterOptions>('filterOptions', { required: true });

const props = defineProps({
  hideUnnecessaryElements: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits<{
  (e: 'filter-changed', options: FilterOptions): void;
  (e: 'observations-updated', data: any[]): void;
}>();

// Filter state
const family = ref(filterOptions.value.family || 'All');
const genus = ref(filterOptions.value.genus || 'All');
const species = ref(filterOptions.value.species || 'All');
const continent = ref(filterOptions.value.continent || 'All Continents');
const startDate = ref(filterOptions.value.startDate || '2025-01-01');
const endDate = ref(filterOptions.value.endDate || '2025-12-31');

// Dropdown options
const familyOptions = ref<string[]>(['All']);
const genusOptions = ref<string[]>(['All']);
const speciesOptions = ref<string[]>(['All']);
const continentOptions = ref<string[]>(['All Continents'])

// Search functionality
const searchTerm = ref('');
const suggestions = ref<any[]>([]);
const isSearchSelected = ref(false);

const isUpdating = ref(false);

// User-specific filters
const showOnlyMyObservations = ref(false);
const currentUserId = ref(''); 

/**
 * Fetches all taxonomic options from API
 * Used for initial load and when resetting filters
 */
const fetchAllTaxa = async (): Promise<void> => {
  try {
    const { data } = await axios.get<TaxaOptions>('http://localhost:8000/api/get_all_taxa/');
    familyOptions.value = ['All', ...data.families];
    genusOptions.value = ['All', ...data.genera];
    speciesOptions.value = ['All', ...data.species];
  } catch (error) {
    console.error('Failed to fetch taxa:', error);
  }
};

// Fetches continent options
const fetchContinentOptions = async () => {
  try {
    const { data } = await axios.get('/api/get_continent_options')
    continentOptions.value = data.continents
  } catch (error) {
    console.error('Failed to fetch continent options:', error)

    continentOptions.value = [
      'All Continents',
      'Africa',
      'Antarctica',
      'Asia',
      'Europe',
      'North America',
      'Oceania',
      'South America'
    ]
  }
}

/**
 * Emits current filters to parent and fetches matching observations
 * This is the main function that triggers data updates
 */
const emitFilters = async (): Promise<void> => {
  const currentFilters: FilterOptions = {
    family: family.value,
    genus: genus.value,
    species: species.value,
    continent: continent.value,
    startDate: startDate.value,
    endDate: endDate.value,
    showOnlyMyObservations: showOnlyMyObservations.value
  };

  emit('filter-changed', currentFilters);
  const observations = await fetchFilteredObservations(currentFilters); // fetch observations
  emit('observations-updated', observations); // emit them to parent
};

/**
 * Fetches observations based on current filters
 * Handles all API params construction
 */

const fetchFilteredObservations = async (filters: FilterOptions) => {
  const params = new URLSearchParams();

  // Only adds filters that have values (skips 'All' options)
  if (filters.continent && filters.continent !== 'All Continents') {
    params.append("continent", filters.continent);
  }
  if (filters.family && filters.family !== 'All') {
    params.append("family", filters.family);
  }
  if (filters.genus && filters.genus !== 'All') {
    params.append("genus", filters.genus);
  }
  if (filters.species && filters.species !== 'All') {
    params.append("species", filters.species);
  }
  if (filters.startDate) {
    params.append("start_date", filters.startDate);
  }
  if (filters.endDate) {
    params.append("end_date", filters.endDate);
  }

  if (showOnlyMyObservations.value && currentUserId.value) {
    params.append("user_id", currentUserId.value);
  }

  // Adds auth token if available
  const token = localStorage.getItem('token');

  try {
    const response = await axios.get(`http://localhost:8000/api/filter_observations/?${params.toString()}`, {
      headers: {
        'Content-Type': 'application/json', 
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}) 
      }
    });

    return response.data;
  } catch (error) {
    console.error("Error fetching filtered observations:", error);
    return [];
  }
};

// Updates genus list based on selected family
const updateGenusList = async (): Promise<void> => {
  try {
    if (family.value === 'All') {
      // If "All" selected, gets full genus list
      const { data } = await axios.get<TaxaOptions>('http://localhost:8000/api/get_all_taxa/');
      genusOptions.value = ['All', ...data.genera];
    } else {
      // Otherwise gets genera just for this family
      const { data } = await axios.get<string[]>(`http://localhost:8000/api/genus-by-family/?family=${encodeURIComponent(family.value)}`);
      genusOptions.value = ['All', ...data];
    }
  } catch (error) {
    console.error('Failed to update genus list:', error);
  }
};

// Similar to above but for species
const updateSpeciesList = async (): Promise<void> => {
  try {
    const params = new URLSearchParams();
    if (family.value !== 'All') params.append('family', family.value);
    if (genus.value !== 'All') params.append('genus', genus.value);
    const { data } = await axios.get<TaxaOptions>(`http://localhost:8000/api/filter-options/?${params.toString()}`);
    speciesOptions.value = ['All', ...(data.species || [])];

    // Resets species if current selection no longer valid
    if (species.value !== 'All' && !speciesOptions.value.includes(species.value)) {
      species.value = 'All';
    }
  } catch (error) {
    console.error('Failed to update species list:', error);
  }
};

const handleFamilyChange = async (): Promise<void> => {
  if (family.value === 'All') {
    if (!isSearchSelected.value) {
      genus.value = 'All';
      species.value = 'All';
    }
    await fetchAllTaxa();
  } else {
    await updateGenusList();
    if (!isSearchSelected.value) {
      genus.value = 'All';
    }
    await updateSpeciesList();
    if (!isSearchSelected.value) {
      species.value = 'All';
    }
  }
};

const handleGenusChange = async (): Promise<void> => {
  if (genus.value === 'All') {
    if (!isSearchSelected.value) {
      species.value = 'All';
    }
    await updateSpeciesList();
    return;
  }

  try {
    const { data: families } = await axios.get<string[]>(
      `http://localhost:8000/api/family-by-genus/?genus=${encodeURIComponent(genus.value)}`
    );

    if (families.length > 0 && families[0] !== family.value) {
      family.value = families[0];
    }

    await updateSpeciesList(); 
  } catch (error) {
    console.error('Failed to handle genus change:', error);
  }
};

const handleSpeciesChange = async (): Promise<void> => {
  if (species.value === 'All') return;

  try {
    const [{ data: families }, { data: genera }] = await Promise.all([
      axios.get<string[]>(`http://localhost:8000/api/family-by-species/?species=${encodeURIComponent(species.value)}`),
      axios.get<string[]>(`http://localhost:8000/api/genus-by-species/?species=${encodeURIComponent(species.value)}`)
    ]);

    if (families.length > 0 && families[0] !== family.value) {
      family.value = families[0];
    }

    if (genera.length > 0 && genera[0] !== genus.value) {
      genus.value = genera[0];
      return;
    }

    await updateSpeciesList();
  } catch (error) {
    console.error('Failed to handle species change:', error);
  }
};

// Resets all filters to defaults
const resetFilters = (): void => {
  isUpdating.value = true;
  family.value = 'All';
  genus.value = 'All';
  species.value = 'All';
  continent.value = 'All Continents';
  startDate.value = '2025-01-01';
  endDate.value = '2025-12-31';
  showOnlyMyObservations.value = false;
  searchTerm.value = '';
  suggestions.value = [];
  
  fetchAllTaxa();
  emitFilters();
  isUpdating.value = false;
};

// Handles search input with debounce would be nice here
const onSearchInput = async (): Promise<void> => {
  if (searchTerm.value.length < 1) {
    suggestions.value = [];
    return;
  }
  try {
    const { data } = await axios.get('http://localhost:8000/api/search_species_by_name/', {
      params: { q: searchTerm.value }
    });
    suggestions.value = data;
  } catch (error) {
    console.error('Search error:', error);
  }
};

// When a search suggestion is selected
const selectSuggestion = async (s: any): Promise<void> => {
  isUpdating.value = true;
  isSearchSelected.value = true;
  
  // Updates all taxonomic levels
  family.value = s.family;
  genus.value = s.genus;
  species.value = s.species;
  searchTerm.value = s.common_name && s.common_name !== s.species ? `${s.common_name} (${s.species})` : s.species;
  suggestions.value = [];

  await updateGenusList();
  await updateSpeciesList();

  emitFilters();

  isSearchSelected.value = false;
  isUpdating.value = false;
};

watch(filterOptions, async (newOptions) => { 
  // Checks if the update is coming from the parent (edit mode population)

  isUpdating.value = true; 

  family.value = newOptions.family ?? 'All'; 
  genus.value = newOptions.genus ?? 'All';
  species.value = newOptions.species ?? 'All';
  continent.value = newOptions.continent ?? 'All Continents';
  startDate.value = newOptions.startDate ?? '2025-01-01';
  endDate.value = newOptions.endDate ?? '2025-12-31';
  showOnlyMyObservations.value = newOptions.showOnlyMyObservations ?? false; 

  // First, ensures dropdown options are loaded based on the new taxonomy
  if (family.value !== 'All') {
      await updateGenusList();
      // Only updates species list if genus is not 'All' or if a species is specifically passed in newOptions
      if (genus.value !== 'All' || (newOptions.species && newOptions.species !== 'All')) {
          await updateSpeciesList();
      }
  } else {
      await fetchAllTaxa();
  }

  // Now, attempts to populate the search term based on the final species value from newOptions
  if (newOptions.species && newOptions.species !== 'All') { 
    try {
      const { data } = await axios.get('http://localhost:8000/api/search_species_by_name/', {
        params: { q: newOptions.species } 
      });
      if (data.length > 0) {
        // Prefers common name if available, otherwise uses species name
        searchTerm.value = data[0].common_name && data[0].common_name !== data[0].species
                            ? `${data[0].common_name} (${data[0].species})`
                            : data[0].species;
      } else {
          searchTerm.value = newOptions.species;
      }
    } catch (error) {
      console.error('Error setting search term from loaded species:', error);
      searchTerm.value = newOptions.species; 
    }
  } else {
    // Clears search term if species is 'All' or undefined
      searchTerm.value = ''; 
  }

  await nextTick(); 
  isUpdating.value = false; 
}, { deep: true});

watch(family, async (newFamily, oldFamily) => {
  if (isUpdating.value) return;
  if (newFamily === oldFamily) return;

  isUpdating.value = true;
  
  if (!isSearchSelected.value) {
    // Only resets if not from search
    genus.value = 'All';
    species.value = 'All';
  }
  
  await handleFamilyChange();
  emitFilters();
  isUpdating.value = false;
});

watch(genus, async (newGenus, oldGenus) => {
  if (isUpdating.value) return;
  if (newGenus === oldGenus) return;

  isUpdating.value = true;
  
  if (!isSearchSelected.value && genus.value === 'All') {
    species.value = 'All';
  }
  
  await handleGenusChange();
  emitFilters();
  isUpdating.value = false;
});

watch(species, async (newSpecies, oldSpecies) => {
  if (isUpdating.value) return;
  if (newSpecies === oldSpecies) return;

  isUpdating.value = true;
  isSearchSelected.value = false;
  
  await handleSpeciesChange();
  emitFilters();
  isUpdating.value = false;
});

watch([family, genus, species, continent, startDate, endDate], () => {
  if (!isUpdating.value) { 
    emitFilters();
  }
});

watch([family, genus, species], ([newFamily, newGenus, newSpecies]) => {
  // Only resets search if the change didn't come from a search selection
  if (!isSearchSelected.value) {
    searchTerm.value = '';
    suggestions.value = [];
  }
});

watch([family, genus, species], async ([f, g, s]) => {
  if (isUpdating.value) return;

  if (isSearchSelected.value || f === 'All' || g === 'All' || s === 'All') return;

  try {
    const { data } = await axios.get('http://localhost:8000/api/search_species_by_name/', {
      params: { q: s }
    });
    if (data.length) {
      // Sets searchTerm only if it's different to avoid re-triggering watch unnecessarily
      const newSearchTerm = data[0].common_name && data[0].common_name !== data[0].species ? `${data[0].common_name} (${data[0].species})` : data[0].species;
      if (searchTerm.value !== newSearchTerm) {
        searchTerm.value = newSearchTerm;
      }
    }
  } catch (error) {
    console.error('Error backfilling search bar:', error);
  }
});

watch(showOnlyMyObservations, () => {
  if (!isUpdating.value) {
    emitFilters();
  }
});

// Initial load
onMounted(async () => {
  await fetchAllTaxa()
  await fetchContinentOptions()
  currentUserId.value = localStorage.getItem('token') || '';

  // If parent provided initial filters, process them
  if (filterOptions.value.species !== 'All' || filterOptions.value.family !== 'All' || filterOptions.value.genus !== 'All') {
    // Watcher will handle the rest

  } else {
      // Otherwise emit default filters to load initial data
      emitFilters();
  }
})
</script>

<template>
  <div class="filter-panel" lang="en-GB">
    <div class="filter-container">
      <div class="filter-row">
        <div class="filter-group">
          <label for="family">Family</label>
          <select id="family" v-model="family">
            <option v-for="option in familyOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </div>

        <div class="filter-group">
          <label for="genus">Genus</label>
          <select id="genus" v-model="genus" :disabled="family == 'All' && !isSearchSelected">
            <option v-for="option in genusOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </div>

        <div class="filter-group">
          <label for="species">Species</label>
          <select id="species" v-model="species" :disabled="genus == 'All' && !isSearchSelected">
            <option v-for="option in speciesOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </div>
        
        <div class="filter-group">
          <input
            v-model="searchTerm"
            @input="onSearchInput"
            placeholder="Enter an insect or species name"
            class="search-input"
          />
          <ul v-if="suggestions.length && searchTerm">
            <li v-for="s in suggestions" :key="s.species" @click="selectSuggestion(s)">
              {{ s.common_name}} ({{s.species }})
            </li>
          </ul>
        </div>

                <!-- Add this checkbox group -->
        <div v-if="!hideUnnecessaryElements" class="filter-group checkbox-group">
          <label class="checkbox-label">
            <input 
              type="checkbox" 
              v-model="showOnlyMyObservations"
              @change="emitFilters"
              :disabled="family === 'All'"
            />
            Show only my observations
          </label>
        </div>

        <div v-if="!hideUnnecessaryElements" class="filter-group">
          <label for="continent">Continent</label>
          <select 
            id="continent" 
            v-model="continent"
            :disabled="family === 'All'"
          >
            <option v-for="option in continentOptions" 
                    :key="option" 
                    :value="option">
              {{ option }}
            </option>
          </select>
        </div>

        <div v-if="!hideUnnecessaryElements" class="filter-row">
          <div class="filter-group">
            <label for="startDate">Start Date</label>
            <input type="date" id="startDate" v-model="startDate" />
          </div>

          <div class="filter-group">
            <label for="endDate">End Date</label>
            <input type="date" id="endDate" v-model="endDate" />
          </div>

          <div class="filter-actions">
            <button @click="resetFilters" class="secondary">Reset</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>

.checkbox-group {
  display: flex;
  align-items: center;
  margin-top: 1.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
}

.filter-panel {
  background-color: var(--color-surface);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.filter-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.filter-row {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.filter-group {
  flex: 1;
  position: relative;
}

.filter-group ul {
  width: 100%;
  list-style: none;
  padding: 0;
  margin-top: 0.25rem;
  background: white;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  max-height: 200px;
  overflow-y: auto;
  position: absolute;
  z-index: 10;
}

.filter-group li {
  padding: 0.5rem;
  cursor: pointer;
}

.filter-group li:hover {
  background-color: #f0f0f0;
}

label {
  display: block;
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
  color: var(--color-text-secondary);
}

select,
input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
}

.filter-actions {
  display: flex;
  align-items: flex-end;
  margin-top: 0.5rem;
}

.search-input {
  width: 100%;
  padding: 0.5rem;
  margin-top: 25px;
  box-sizing: border-box;
}

ul {
  list-style: none;
  margin: 0;
  padding: 0;
  background: #f9f9f9;
  border: 1px solid #ccc;
  max-height: 200px;
  overflow-y: auto;
  position: absolute;
  z-index: 10;
  width: 100%;
}

li {
  padding: 8px;
  cursor: pointer;
}

li:hover {
  background: #efefef;
}

button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

button.secondary {
  background-color: var(--color-surface-variant);
  color: var(--color-on-surface-variant);
  border: 1px solid var(--color-outline);
}

@media (min-width: 768px) {
  .filter-panel {
    padding: 1.5rem;
  }

  .filter-row {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .filter-group {
    flex: 1 1 calc(50% - 1rem);
  }
}

@media (min-width: 1024px) {
  .filter-group {
    flex: 1 1 calc(25% - 1rem);
  }

  .filter-actions {
    margin-top: 0;
  }
}
</style>
