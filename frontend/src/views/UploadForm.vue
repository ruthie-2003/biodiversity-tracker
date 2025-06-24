<template>
  <div class="upload-form-container">
    <h1>{{ isEditMode ? 'Edit Observation' : 'Upload Species Data' }}</h1>

    <form class="upload-form" @submit.prevent="handleSubmit">
      
      <!-- Species Name -->
      <div class="form-group">
        <label>Species Taxonomy</label>
        <FilterPanel
          v-model:filterOptions="filterOptions"
          @filter-changed="handleTaxonomyChange"
          :hide-unnecessary-elements="true"
        />
      </div>
      
      <!-- Location -->
      <div class="form-group" style="position: relative;">
        <label for="location">Location</label>
        <input
          id="location"
          v-model="location"
          @input="searchLocations"
          placeholder="Search location"
        />
        <ul v-if="locationSuggestions.length" class="suggestions-dropdown">
          <li v-for="s in locationSuggestions" :key="s.place_id" @click="selectSuggestion(s)">
            {{ s.display_name }}
          </li>
        </ul>
      </div>
      
      <!-- Map Preview -->
      <div class="form-group" >
        <label>Map Preview</label>
        <div class="map-container">
          <MapView
            ref="mapViewRef"
            :observations="[]"
            :enableLocationPicker="true"
            @location-picked="handleMapClick"
          />
        </div>

        <div class="mt-4">
          <label for="coordinates">Coordinates:</label>
          <input
            id="coordinates"
            :value="formattedCoordinates"
            readonly
            class="border rounded p-2 mt-1 w-full"
          />
        </div>
      </div>
      
      <!-- Date -->
      <div class="form-group">
        <label for="date">Observation Date</label>
        <input
          id="date"
          type="date"
          v-model="date"
          required
        />
      </div>

      <!-- Quantity -->
      <div class="form-group">
        <label for="quantity">Quantity Found</label>
        <input
          id="quantity"
          type="number"
          v-model="quantity"
          min="1"
          placeholder="Enter number of species"
          required
        />
      </div>
      
      <!-- Photo/Audio Upload -->
      <div class="form-group">
        <label>Photo/Audio Upload</label>
        <div
          style="
            border: 2px dashed var(--color-neutral-300);
            border-radius: var(--radius-sm);
            padding: 1.5rem;
            text-align: center;
            cursor: pointer;
            transition: background-color 0.2s ease;
          "
          @click="triggerFileInput"
          @dragover.prevent
          @drop.prevent="handleDrop"
        >
          <input
            type="file"
            id="file-upload"
            ref="fileInput"
            @change="handleFileChange"
            multiple
            accept="image/*,audio/*"
            style="display: none;"
          />
          <Image style="color: var(--color-neutral-400); margin-bottom: 1rem;" />
          <p style="margin-bottom: 0.5rem;">Drag and drop your photos/audio here or</p>
          <button type="button" 
            @click.stop="triggerFileInput" 
            style="background-color: var(--color-primary-50); 
            color: var(--color-primary-700); 
            padding: 0.5rem 1rem; 
            border-radius: var(--radius-sm); 
            border: none; 
            cursor: pointer;">
            Browse Files
          </button>
        </div>

        <div v-if="files.length > 0 || existingFiles.length > 0 || existingAudio.length > 0" 
            style="margin-top: 1rem; 
            display: flex; 
            flex-wrap: wrap; 
            gap: 0.5rem;">
          <!-- Existing image files -->
          <div
            v-for="(url, index) in existingFiles"
            :key="'existing-image-' + index"
            class="file-preview"
          >
            <button type="button" @click.stop="removeExistingFile(index, 'photo')" class="remove-button">&times;</button>
            <img :src="url" alt="Existing image" class="preview-image" />
          </div>

          <!-- Existing audio files -->
          <div
            v-for="(url, index) in existingAudio"
            :key="'existing-audio-' + index"
            class="file-preview"
          >
            <button type="button" @click.stop="removeExistingFile(index, 'audio')" class="remove-button">&times;</button>
            <audio controls :src="url" class="preview-audio"></audio>
          </div>

          <!-- New files -->
          <div
            v-for="(file, index) in files"
            :key="file.name + index"
            style="
              background-color: var(--color-neutral-100);
              border-radius: var(--radius-sm);
              padding: 0.25rem 0.5rem;
              font-size: var(--font-size-sm);
              display: flex;
              align-items: center;
              max-width: 200px;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            "
          >
            <button
              type="button"
              @click.stop="removeFile(index)"
              style="position: relative;
                    top: 5px;
                    right: 5px;
                    background: transparent;
                    border: 1px solid var(--color-neutral-300);
                    border-radius: 50%;
                    font-size: 1.3rem;
                    font-weight: bold;
                    color: #d32f2f;
                    width: 24px;
                    height: 24px;
                    line-height:20px;
                    text-align:center;
                    padding:0;
                    cursor: pointer;"
              aria-label="Remove file"
            >
              &times;
            </button>
            <!-- Image preview -->
            <img
              v-if="isImage(file)"
              :src="filePreviews[index]"
              alt="Image preview"
              class="preview-image"
            />
            <!-- Audio preview -->
            <audio
              v-else-if="isAudio(file)"
              controls
              :src="filePreviews[index]"
              class="preview-audio"
            ></audio>
          </div>
        </div>
      </div>
      
      <!-- Description -->
      <div class="form-group">
        <label for="description">Description</label>
        <textarea
          id="description"
          v-model="description"
          placeholder="Enter habitat description and additional details"
          rows="6"
        ></textarea>
      </div>
      
      <!-- Submit Button -->
      <div class="form-actions">
        <button type="submit">
          <Upload style="margin-right: 0.5rem;" />
          {{ isEditMode ? 'Update Observation' : 'Submit Data' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import axios from 'axios';
import debounce from 'lodash.debounce';
import { ref, watch, nextTick, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router'
import { Upload, Image } from 'lucide-vue-next';
import MapView from '@/components/MapView.vue';
import FilterPanel from '@/components/FilterPanel.vue';

// Filter options for the FilterPanel
const filterOptions = ref({
  family: 'All',
  genus: 'All',
  species: 'All',
  // These will be hidden but still in model
  continent: 'All Continents', 
  startDate: '2025-01-01',    
  endDate: '2025-12-31'      
});

// Form fields
const location = ref('');
const locationSuggestions = ref([])
const selectedCoords = ref(null)
const date = ref('');
const quantity = ref(1);
const description = ref('');
const files = ref([]);
const filePreviews = ref([]);
const fileInput = ref(null);
const mapViewRef = ref(null);

// Edit mode state
const route = useRoute()
const router = useRouter()
const isEditMode = computed(() => route.query.edit === 'true')
const sourceId = computed(() => route.query.source_id)

// Existing observation data (for edit mode)
const existingObservation = ref(null)
const existingFiles = ref([])
const existingAudio = ref([])

// Removes existing files from the edit form
const removeExistingFile = (index, type) => {
  if (type === 'photo') {
    existingFiles.value.splice(index, 1);
  } else if (type === 'audio') {
    existingAudio.value.splice(index, 1);
  }
};

// Fetches observation data when in edit mode
const fetchObservationForEdit = async () => {
  if (!isEditMode.value || !sourceId.value) return
  
  try {
    const token = localStorage.getItem('token')
    if (!token) {
        alert('Authentication required.');
        router.push('/login');
        return;
    }

    const response = await axios.get(
      `http://localhost:8000/api/observations/${sourceId.value}/`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
    existingObservation.value = response.data
    populateFormFields()
  } catch (error) {
    console.error('Failed to fetch observation for edit:', error)
    alert('Failed to load observation for editing. Please try again.');
  }
}

// Populates form with existing observation data
const populateFormFields = () => {
  if (!existingObservation.value) return
  
  const obs = existingObservation.value
  
  // Sets taxonomy filters
  filterOptions.value = {
    family: obs.properties.family,
    genus: obs.properties.genus,
    species: obs.species_name,
    // Keeping hidden filters at defaults
    continent: 'All Continents',
    startDate: '2025-01-01',
    endDate: '2025-12-31'
  }
  
  // Sets location data
  location.value = obs.properties.location_name || ''
  selectedCoords.value = {
    lat: parseFloat(obs.location.latitude),
    lng: parseFloat(obs.location.longitude)
  }
  
  // Sets other fields
  date.value = obs.properties.timestamp ? obs.properties.timestamp.split('T')[0] : '';
  quantity.value = obs.properties.quantity
  description.value = obs.properties.additional_details || ''
  
  // Tracks existing media separately from new uploads
  existingFiles.value = obs.properties.photo || []
  existingAudio.value = obs.properties.audio || []
  
  // Updates map pin
  nextTick(() => {
    if (mapViewRef.value?.addOrMovePin) {
      mapViewRef.value.addOrMovePin(
        selectedCoords.value.lat,
        selectedCoords.value.lng
      )
    }
  })
}

// Handles taxonomy changes from FilterPanel
const handleTaxonomyChange = (options) => {
  filterOptions.value = options;
};

// Formats coordinates for display
const formattedCoordinates = computed(() => {
  if (!selectedCoords.value) return '';
  const { lat, lng } = selectedCoords.value;
  return `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
});

// Debounced version of searchLocations
const debouncedSearch = debounce(async () => {
  if (location.value.length < 3) return;

  try {
    const res = await axios.get('https://nominatim.openstreetmap.org/search', {
      params: {
        q: location.value,
        format: 'json',
        addressdetails: 1,
        limit: 5,
        'accept-language': 'en-GB',
      },
    });
    locationSuggestions.value = res.data;
  } catch (e) {
    console.error('Location lookup failed:', e);
  }
}, 300);

// Triggers location search when typing
const searchLocations = () => {
  debouncedSearch();
};

// Handles location suggestion selection
const selectSuggestion = (suggestion) => {
  location.value = suggestion.display_name;
  selectedCoords.value = { lat: parseFloat(suggestion.lat), lng: parseFloat(suggestion.lon) };
  locationSuggestions.value = [];
  
  // Updates map pin
  if (mapViewRef.value?.addOrMovePin) {
    mapViewRef.value.addOrMovePin(
      selectedCoords.value.lat,
      selectedCoords.value.lng
    );
  }
};

// Handles map click for manual location selection
const handleMapClick = async (coords) => {
  const lat = parseFloat(coords.lat);
  const lng = parseFloat(coords.lng);
  selectedCoords.value = { lat, lng };

  try {
    // Reverse geocode to get location name
    const res = await axios.get('https://nominatim.openstreetmap.org/reverse', {
      params: {
        lat,
        lon: lng,
        format: 'json',
        'accept-language': 'en-GB',
      },
    });
    location.value = res.data.display_name;
  } catch (e) {
    console.error('Reverse geocoding failed:', e);
    location.value = 'Unknown location';
  }

  // Updates map pin
  nextTick(() => {
    if (mapViewRef.value?.addOrMovePin) {
      mapViewRef.value.addOrMovePin(lat, lng);
    }
  });
};

// File handling utilities
function updateFilePreviews(newFiles) {
  newFiles.forEach((file) => {
    const url = URL.createObjectURL(file);
    filePreviews.value.push(url);
  });
}

const isImage = (file) => file.type.startsWith('image/');
const isAudio = (file) => file.type.startsWith('audio/');

const triggerFileInput = () => {
  fileInput.value?.click();
};

const handleFileChange = (e) => {
  if (e.target.files) {
    const newFiles = Array.from(e.target.files);
    files.value = [...files.value, ...newFiles];
    updateFilePreviews(newFiles);
    console.log('After file selection. files.value:', files.value.map(f => f.name));
  }
};

const removeFile = (index) => {
  URL.revokeObjectURL(filePreviews.value[index]);
  files.value.splice(index, 1);
  filePreviews.value.splice(index, 1);
};

const handleDrop = (e) => {
  const droppedFiles = Array.from(e.dataTransfer.files);
  files.value = [...files.value, ...droppedFiles];
  updateFilePreviews(droppedFiles);
};

// Main form submission handler
const handleSubmit = async () => {
  try {

      // Validates required fields
      if (!filterOptions.value.family || filterOptions.value.family === 'All') {
      alert('Please select a family before submitting the form.');
      return;
    }

    if (!selectedCoords.value || typeof selectedCoords.value.lat !== 'number' || typeof selectedCoords.value.lng !== 'number') {
      alert('Please select a valid location on the map. Coordinates are missing or invalid.');
      console.error('Validation failed: selectedCoords is invalid.', selectedCoords.value);
      return;
    }

    if (!date.value) {
      alert('Please select an observation date.');
      return;
    }

    // Prepares form data for submission
    const formData = new FormData();

    formData.append('family', filterOptions.value.family);
    formData.append('genus', filterOptions.value.genus);
    formData.append('species', filterOptions.value.species);
    formData.append('latitude', selectedCoords.value.lat.toString());
    formData.append('longitude', selectedCoords.value.lng.toString());
    formData.append('location_name', location.value);
    formData.append('date', date.value);
    formData.append('quantity', quantity.value.toString());
    formData.append('additional_details', description.value);

    // Includes existing files that weren't removed
    existingFiles.value.forEach(url => {
      formData.append('existing_photos[]', url);
    });
    existingAudio.value.forEach(url => {
      formData.append('existing_audio[]', url);
    });

    console.log('Inside handleSubmit. Final files.value before FormData append:', files.value.map(f => f.name));
    // Adds new files
    files.value.forEach(file => {
      formData.append('media_files', file);
    });

    console.log('--- FormData Contents (before sending) ---');
  
    for (const pair of formData.entries()) {
      console.log(`${pair[0]}: ${pair[1]}`);
    }
    console.log('-----------------------------------------');

    // Checks authentication
    const token = localStorage.getItem('token');

    if (!token) {
      alert('Authentication required. Please log in.');
      router.push('/login');
      return;
    }

    // Determines API endpoint based on edit mode
    let requestUrl = 'http://localhost:8000/api/upload/';
    const method = isEditMode.value ? 'PATCH' : 'POST';

    
    if (isEditMode.value) {
      requestUrl = `${requestUrl}?source_id=${sourceId.value}`; 
    }

    const response = await axios({
      method,
      url: requestUrl, 
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': `Bearer ${token}`
      }
    });

    alert(isEditMode.value ? 'Update successful!' : 'Upload successful!');

    // Redirects to the observation page using the returned source_id
    if (response.data.source_id) {
      router.push(`/observations/${response.data.source_id}`);
    } else {
      // Resets form for new submissions
      filterOptions.value = {
        family: 'All',
        genus: 'All',
        species: 'All',
        continent: 'All Continents',
        startDate: '2025-01-01',
        endDate: '2025-12-31',
      };
      location.value = '';
      selectedCoords.value = null;
      date.value = '';
      description.value = '';
      quantity.value = 1;

      files.value = [];
      filePreviews.value.forEach((url) => URL.revokeObjectURL(url));
      filePreviews.value = [];
      existingFiles.value = [];
      existingAudio.value = [];

      if (mapViewRef.value?.removePin) mapViewRef.value.removePin();
    }
  } catch (error) {
    console.error('Error submitting observation:', error);
    if (error.response) {
      console.error('Backend Error Data:', error.response.data);
      console.error('Backend Error Status:', error.response.status);
      alert(`An error occurred while ${isEditMode.value ? 'updating' : 'submitting'} your observation: ${error.response.data.error || error.message}`);
    } else {
      alert(`An error occurred while ${isEditMode.value ? 'updating' : 'submitting'} your observation: ${error.message}`);
    }
  }
};

watch(mapViewRef, (newVal) => {
  if (newVal && selectedCoords.value) {
    nextTick(() => {
      if (mapViewRef.value?.addOrMovePin) {
        mapViewRef.value.addOrMovePin(
          selectedCoords.value.lat,
          selectedCoords.value.lng
        );
      }
    });
  }
});

// Initializes edit mode if needed
onMounted(fetchObservationForEdit);
</script>

<style scoped>
.upload-form-container {
  max-width: 100%;
  margin: 2rem auto;
  padding: 2rem;
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-100);
}

h1 {
  font-size: var(--font-size-3xl);
  color: var(--color-primary-900);
  margin-bottom: 1.5rem;
  font-weight: 600;
  line-height: 1.2;
}

.upload-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  position: relative;
}

.suggestions-dropdown {
  list-style: none; /* remove bullet points */
  padding: 0;
  margin: 0.25rem 0 0 0;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-sm);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: absolute;
  top: 100%;
  background: white;
  z-index: 10;
  width: 100%;
  max-height: 200px;
  overflow-y: auto;
}

.suggestions-dropdown li {
  padding: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s ease;
  border-bottom: 1px solid var(--color-neutral-100);
}
.suggestions-dropdown li:last-child {
  border-bottom: none;
}

.suggestions-dropdown li:hover {
  background-color: var(--color-primary-50);
}

.map-container {
  width: 100%;
  height: 500px;
  display: block;
}

label {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--color-primary-800);
}

input[type='text'],
input[type='date'],
textarea,
input[type='file'] {
  padding: 0.5rem 0.75rem;
  font-size: var(--font-size-md);
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-sm);
  transition: border-color 0.2s ease;
  font-family: inherit;
}

input[type='text']:focus,
input[type='date']:focus,
textarea:focus,
input[type='file']:focus {
  outline: none;
  border-color: var(--color-primary-500);
}

textarea {
  resize: vertical;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.preview-image {
  width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.preview-audio {
  width: 100%;
}

button {
  background-color: var(--color-primary-600);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  font-size: var(--font-size-md);
  font-weight: 600;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

button:disabled {
  background-color: var(--color-neutral-300);
  cursor: not-allowed;
}

button:not(:disabled):hover {
  background-color: var(--color-primary-700);
}

.error-message {
  color: var(--color-error-600);
  font-weight: 600;
  margin-top: 0.5rem;
}

.success-message {
  color: var(--color-success-600);
  font-weight: 600;
  margin-top: 0.5rem;
}
</style>