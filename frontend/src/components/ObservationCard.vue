<template>
    <div class="card">
      <img :src="observation.image_url" alt="Insect image" />
      <h3>{{ observation.common_name || observation.species }}</h3>
      <p><strong>Species:</strong> {{ observation.species }}</p>
      <p><strong>User:</strong> {{ observation.username }}</p>
    </div>
  </template>
  
  <script>
  export default {
    // Accepts an observation object with:
    // - image_url: string (URL to observation photo)
    // - common_name: string | null (optional common name)
    // - species: string (scientific name)
    // - username: string (observer's username)
    props: ['observation']
  }
  </script>
  
  <style scoped>
  .card {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem;
    width: 250px;
    text-align: center;
  }
  .card img {
    width: 100%;
    height: auto;
    border-radius: 5px;
  }
  </style>
  