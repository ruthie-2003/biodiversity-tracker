// In your types.ts file

export interface Comment {
  id: string
  user_name: string
  user_profile_picture?: string
  comment_text: string
  timestamp: string
  parent_comment_id?: string
  replies?: Comment[] // 🔁 Important: recursive replies
}

export interface Species {
  _id: string;
  species: string;
  family: string;
  genus: string;
  common_name?: string;
  image_url?: string;
  audio_url?: string;
  observations_count?: number;
}

export interface SpeciesDetailResponse {
  species: Species;
  recent_observations: Observation[];
  status_counts: Record<string, number>;
}

export interface Observation {
  _id?: string
  source_id?: number
  type: 'Feature'
  location: {
    type: 'Point'
    coordinates: [number, number]
    latitude?: number
    longitude?: number  // [longitude, latitude]
  }
  properties: {
    species: string
    genus: string
    family: string
    timestamp: string
    location_name?: string
    region?: string
    country?: string
    photo?: string[]
    audio?: string[]
    external_link?: string
    status?: string
    user_name?: string
    name?: string
    user_profile_picture?: string
  }
}

export interface DetailedObservation extends Observation {
  _id: string
  species_name: string
  common_name?: string
  family: string
  genus: string
  user_name: string
  user_title?: string
  user_id: string
  user_profile_picture?: string
  status?: string
  comments_count?: number
  comments?: Comment[]
  properties: {
    species: string;
    genus: string;
    family: string;
    timestamp: string;
    location_name?: string;
    region?: string;
    country?: string;
    photo?: string[];
    audio?: string[];
    external_link?: string;
    status?: string;
  };
  is_admin?: boolean;
  is_current_user?: boolean;
}

export interface MapObservation {
  location: {
    coordinates: [number, number];
  };
  properties: {
    species: string;
    family: string;
    genus: string;
    timestamp: string;
    location_name: string;
    region: string;
    country: string;
    photo: string[];
    external_link: string;
  };
}

export interface FilterOptions {
  family: string;
  genus: string;
  species: string;
  continent: string;
  startDate: string;
  endDate: string;
  showOnlyMyObservations?: boolean;
}

export interface TaxaOptions {
  families: string[];
  genera: string[];
  species: string[];
}