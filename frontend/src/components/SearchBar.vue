<script setup lang="ts">
import axios from 'axios';
import { ref, watch } from 'vue'

const props = defineProps<{
  search: string
}>()

const emit = defineEmits(['update:search'])

const localSearch = ref(props.search)

// Search suggestions - can be species or users
const suggestions = ref<
  (
    | { type: 'species'; id: string | number; species: string; common_name?: string }
    | { type: 'user'; id: string | number; name: string; username: string }
  )[]
>([])

const showSuggestions = ref(false)

const highlightedIndex = ref(0)

watch(() => props.search, (newValue) => {
  localSearch.value = newValue
})

// Main search watcher - fetches suggestions when query changes
watch(localSearch, async (newValue) => {
  emit('update:search', newValue)

  const query = newValue.trim()
  if (query.length > 1) {
    try {
      const res = await axios.get(`http://localhost:8000/api/search_species_and_users/?q=${encodeURIComponent(query)}`)
      suggestions.value = res.data
      showSuggestions.value = suggestions.value.length > 0
      highlightedIndex.value = 0
    } catch (err) {
      console.error('Failed to fetch suggestions', err)
      suggestions.value = []
      showSuggestions.value = false
    }
  } else {
    // Clears results if search is too short
    suggestions.value = []
    showSuggestions.value = false
  }
})

function updateSearch() {
  emit('update:search', localSearch.value)
}

// Clears search term and results
function clearSearch() {
  localSearch.value = ''
  emit('update:search', '')
  suggestions.value = []
  showSuggestions.value = false
  highlightedIndex.value = 0
}

/**
 * Handles selecting a suggestion from dropdown
 * Updates search term and navigates to appropriate page
 */
function selectSuggestion(item: any) {
  localSearch.value = item.type === 'species' ? item.species : item.username
  showSuggestions.value = false
  if (item.type === 'species') {
    window.location.href = `/species/${encodeURIComponent(item.species)}/`
  } else if (item.type === 'user') {
    window.location.href = `/profile/${encodeURIComponent(item.id)}/`
  }
}

// Handles Enter key - selects first suggestion or shows message
function onEnter() {
  if (suggestions.value.length > 0) {
    const firstSuggestion = suggestions.value[highlightedIndex.value]
    selectSuggestion(firstSuggestion)
  } else {
    alert("Please select a valid species or user from the suggestions.")
  }
}

// Keyboard navigation for suggestions
function onKeyDown(event: KeyboardEvent) {
  if (!showSuggestions.value || suggestions.value.length === 0) return

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    highlightedIndex.value = (highlightedIndex.value + 1) % suggestions.value.length

  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    highlightedIndex.value =
      (highlightedIndex.value - 1 + suggestions.value.length) % suggestions.value.length

  } else if (event.key === 'Enter') {
    event.preventDefault()
    onEnter()
  }
}

</script>

<template>
  <div class="search-container">
    <div class="search-bar">
      <svg xmlns="http://www.w3.org/2000/svg" class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"></circle>
        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
      </svg>
      <input 
        type="text"
        placeholder="Search species or contributors..."
        v-model="localSearch"
        @input="updateSearch"
        @keydown="onKeyDown"
        class="search-input"
        autocomplete="off"
      />
      <button 
        v-if="localSearch" 
        @click="clearSearch" 
        class="clear-button"
        aria-label="Clear search"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
      <ul v-if="showSuggestions" class="suggestion-list" role="listbox">
        <li 
          v-for="(item, index) in suggestions" 
          :key="item.id"
          @click="selectSuggestion(item)"
          :class="['suggestion-item', { highlighted: index === highlightedIndex }]"
          role="option"
          :aria-selected="index === highlightedIndex"
        >
          <span v-if="item.type === 'species'">
            🐞 {{ item.species }}<span v-if="item.common_name"> – {{ item.common_name }}</span>
          </span>
          <span v-else-if="item.type === 'user'">
            👤 {{ item.name || '' }} <span class="text-muted">@{{ item.username }}</span>
          </span>
        </li>
      </ul>
  </div>
</template>

<style scoped>
.search-container {
  display: flex;
  max-width: 800px;
  margin: var(--space-3) auto;
  gap: var(--space-2);
  position: relative;
}

.search-bar {
  flex: 1;
  display: flex;
  align-items: center;
  background-color: white;
  border-radius: var(--radius-md);
  padding: 0 var(--space-2);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-200);
  transition: all var(--transition-normal);
}

.search-bar:focus-within {
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-400);
}

.search-icon {
  width: 20px;
  height: 20px;
  color: var(--color-neutral-500);
  margin-right: var(--space-1);
}

.search-input {
  flex: 1;
  border: none;
  padding: var(--space-1) 0;
  font-size: var(--font-size-md);
  background: transparent;
}

.search-input:focus {
  outline: none;
}

.suggestion-list {
  position: absolute;
  top: 100%;
  left: 0;
  background: white;
  z-index: 10;
  list-style: none;
  margin: 4px 0 0 0;
  padding: var(--space-1);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
  width: 100%;
  max-height: 200px;
  overflow-y: auto;
}

.suggestion-item {
  cursor: pointer;
  padding: 8px 12px;
  transition: background-color 0.2s ease;
  border-radius: var(--radius-sm);
  color: var(--color-neutral-900);
}
.suggestion-item.highlighted {
  background-color: var(--color-primary-100);
  color: var(--color-primary-800);
}

.suggestion-item:hover,
.suggestion-item:focus {
  background-color: var(--color-primary-100); /* light highlight */
  color: var(--color-primary-800);
  outline: none;
}

.clear-button {
  background: none;
  border: none;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--color-neutral-500);
  transition: color var(--transition-fast);
}

.clear-button:hover {
  color: var(--color-neutral-800);
}

.clear-button svg {
  width: 16px;
  height: 16px;
}

.search-button {
  background-color: var(--color-primary-600);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-1) var(--space-2);
  font-weight: 500;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.search-button:hover {
  background-color: var(--color-primary-700);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .search-container {
    flex-direction: column;
    padding: 0 var(--space-2);
  }
}
</style>