<script setup lang="ts">
import { ref, watch, computed } from 'vue'

// Props - expects an array of image URLs
const props = defineProps<{
  images: string[]
}>()

// Tracks which image is currently active
const activeIndex = ref(0)
const totalImages = computed(() => props.images.length)

// Moves to next image
const goToNext = () => {
  activeIndex.value = (activeIndex.value + 1) % totalImages.value
}

// Move to previous image
const goToPrevious = () => {
  activeIndex.value = (activeIndex.value - 1 + totalImages.value) % totalImages.value
}

// Jumps directly to specific image
const setActiveImage = (index: number) => {
  activeIndex.value = index
}

// Resets to first image if the images array changes and our current index is now invalid
watch(() => props.images, (newImages) => {
  if (activeIndex.value >= newImages.length) {
    activeIndex.value = 0
  }
}, { deep: true })
</script>

<template>
  <div class="image-gallery">
    <div class="main-image-container">
      <div class="main-image">
        <img 
          :src="images[activeIndex]" 
          alt="Observation photo" 
          :key="activeIndex"
          class="active-image"
        />
      </div>
    </div>
    
    <div v-if="totalImages > 1" class="thumbnail-navigation">
      <div class="pagination-controls">
        <button 
          class="pagination-button" 
          @click="goToPrevious"
          aria-label="Previous page"
        >
          Previous
        </button>
        
        <div class="pagination-indicator">
          {{ activeIndex + 1 }} / {{ totalImages }}
        </div>
        
        <button 
          class="pagination-button" 
          @click="goToNext"
          aria-label="Next page"
        >
          Next
        </button>
      </div>
      
      <div class="thumbnail-container">
        <div 
          v-for="(image, index) in images" 
          :key="index"
          class="thumbnail"
          :class="{ active: index === activeIndex }"
          @click="setActiveImage(index)"
        >
          <img :src="image" :alt="`Thumbnail ${index + 1}`" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.image-gallery {
  background: white;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.main-image-container {
  position: relative;
  height: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-neutral-100);
}

.main-image {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.active-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: cover;
  transition: opacity 0.3s ease;
}

.gallery-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background-color: rgba(255, 255, 255, 0.7);
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  cursor: pointer;
  z-index: 2;
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.thumbnail-navigation {
  padding: var(--space-2);
  background-color: white;
}

.pagination-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.pagination-button {
  background-color: var(--color-primary-600);
  color: white;
  border: none;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.pagination-button:hover {
  background-color: var(--color-primary-700);
}

.pagination-indicator {
  font-weight: 500;
  color: var(--color-neutral-700);
}

.thumbnail-container {
  display: flex;
  gap: var(--space-2);
  overflow-x: auto;
  padding-bottom: var(--space-1);
}

.thumbnail {
  width: 80px;
  height: 60px;
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.thumbnail.active {
  border-color: var(--color-primary-600);
}

.thumbnail:hover {
  transform: scale(1.05);
}

.thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

@media (max-width: 768px) {
  .main-image-container {
    height: 300px;
  }
  
  .thumbnail {
    width: 60px;
    height: 45px;
  }
}

@media (max-width: 480px) {
  .main-image-container {
    height: 250px;
  }
  
  .thumbnail-container {
    justify-content: center;
  }
}
</style>