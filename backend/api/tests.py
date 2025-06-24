from django.test import TestCase, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
import json
import jwt
import datetime
from bson import ObjectId
import os
from unittest.mock import patch, MagicMock, ANY
from api.views import upload_observation

# Mock the get_location_details function at the class level
@patch('api.views.get_location_details', return_value={'country': 'MockCountry', 'region': 'MockRegion'})
class UploadNewObservationTests(TestCase):
    def setUp(self):
        """Set up common test resources."""
        self.factory = RequestFactory()
        self.user_id = ObjectId()
        self.token = jwt.encode(
            {"user_id": str(self.user_id), "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        self.auth_headers = {'HTTP_AUTHORIZATION': f'Bearer {self.token}'}

        # Base data for a valid new observation
        self.base_data = {
            'latitude': '30.04439',
            'longitude': '31.23573',
            'date': '2025-06-22T20:45:00',
            'quantity': '1',
            'additional_details': 'Just found this around the city center'
        }

        # Data for a complete taxonomy observation
        self.complete_taxonomy_data = {
            **self.base_data,
            'family': 'Hesperiidae',
            'genus': 'Hylephila',
            'species': 'Hylephila Phyleus',
            'common_name': 'Fiery Skipper'
        }

        # Data for an incomplete taxonomy observation
        self.incomplete_taxonomy_data = {
            **self.base_data,
            'family': 'Hesperiidae',
            # Genus and species are omitted to test default "All" handling
        }

        self.test_image = SimpleUploadedFile("test_image.jpg", b"image_content", "image/jpeg")
        self.test_audio = SimpleUploadedFile("test_audio.mp3", b"audio_content", "audio/mpeg")

    def tearDown(self):
        """Clean up created files."""
        if default_storage.exists('uploads/test_image.jpg'):
            default_storage.delete('uploads/test_image.jpg')
        if default_storage.exists('uploads/test_audio.mp3'):
            default_storage.delete('uploads/test_audio.mp3')

    def _mock_user(self, mock_users_find_one):
        """Mock the user lookup."""
        mock_users_find_one.return_value = {'_id': self.user_id, 'username': 'testuser', 'roles': []}

    @patch('api.views.observations_collection.find_one', return_value=None) # for source_id check
    @patch('api.views.locations_collection.find_one', return_value=None)
    @patch('api.views.species_collection.find_one')
    @patch('api.views.species_collection.insert_one')
    @patch('api.views.locations_collection.insert_one')
    @patch('api.views.observations_collection.insert_one')
    @patch('api.views.users_collection.find_one')
    def test_successful_creation_with_complete_taxonomy(self, mock_users_find, mock_obs_insert, mock_loc_insert, mock_species_insert, mock_species_find, mock_loc_find, mock_obs_find_sid, mock_get_loc):
        """Test creating an observation with full, new taxonomy creates a species entry."""
        self._mock_user(mock_users_find)
        mock_species_find.return_value = None # No existing species
        mock_loc_insert.return_value.inserted_id = ObjectId()
        mock_species_insert.return_value.inserted_id = ObjectId()
        mock_obs_insert.return_value.inserted_id = ObjectId()

        request = self.factory.post('/api/upload/', self.complete_taxonomy_data, **self.auth_headers)
        response = upload_observation(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['message'], 'Observation submitted successfully.')

        # Verify a new species document was created
        mock_species_insert.assert_called_once()
        # Verify the observation links to the new species_id
        mock_obs_insert.assert_called_once()
        inserted_doc = mock_obs_insert.call_args[0][0]
        self.assertIn('species_id', inserted_doc)
        self.assertNotIn('raw_taxonomy', inserted_doc)

    @patch('api.views.observations_collection.find_one', return_value=None) # for source_id check
    @patch('api.views.locations_collection.find_one', return_value=None)
    @patch('api.views.species_collection.insert_one')
    @patch('api.views.locations_collection.insert_one')
    @patch('api.views.observations_collection.insert_one')
    @patch('api.views.users_collection.find_one')
    def test_successful_creation_with_incomplete_taxonomy(self, mock_users_find, mock_obs_insert, mock_loc_insert, mock_species_insert, mock_loc_find, mock_obs_find_sid, mock_get_loc):
        """Test creating an observation with only family name stores raw_taxonomy."""
        self._mock_user(mock_users_find)
        mock_loc_insert.return_value.inserted_id = ObjectId()
        mock_obs_insert.return_value.inserted_id = ObjectId()

        request = self.factory.post('/api/upload/', self.incomplete_taxonomy_data, **self.auth_headers)
        response = upload_observation(request)

        self.assertEqual(response.status_code, 200)
        # Verify no attempt was made to create a species document
        mock_species_insert.assert_not_called()
        # Verify the observation was created with a 'raw_taxonomy' field
        mock_obs_insert.assert_called_once()
        inserted_doc = mock_obs_insert.call_args[0][0]
        self.assertNotIn('species_id', inserted_doc)
        self.assertIn('raw_taxonomy', inserted_doc)
        self.assertEqual(inserted_doc['raw_taxonomy']['family'], 'Hesperiidae')
        self.assertEqual(inserted_doc['raw_taxonomy']['genus'], 'All')
        self.assertEqual(inserted_doc['raw_taxonomy']['species'], 'All')
        self.assertEqual(inserted_doc['status'], 'pending')

    @patch('api.views.users_collection.find_one')
    def test_missing_required_field_family(self, mock_users_find, mock_get_loc):
        """Test request fails if 'family' is missing for a new observation."""
        self._mock_user(mock_users_find)
        data = self.base_data.copy() # Missing family
        request = self.factory.post('/api/upload/', data, **self.auth_headers)
        response = upload_observation(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Family is required", json.loads(response.content)['error'])

    @patch('api.views.users_collection.find_one')
    def test_missing_required_field_location(self, mock_users_find, mock_get_loc):
        """Test request fails if 'latitude' or 'longitude' is missing for a new observation."""
        self._mock_user(mock_users_find)
        data = self.complete_taxonomy_data.copy()
        del data['latitude'] # Missing location
        request = self.factory.post('/api/upload/', data, **self.auth_headers)
        response = upload_observation(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing latitude or longitude", json.loads(response.content)['error'])

    @patch('api.views.observations_collection.find_one', return_value=None)
    @patch('api.views.locations_collection.find_one', return_value=None)
    @patch('api.views.species_collection.find_one', return_value=None)
    @patch('api.views.species_collection.insert_one')
    @patch('api.views.locations_collection.insert_one')
    @patch('api.views.observations_collection.insert_one')
    @patch('api.views.users_collection.find_one')
    @patch('api.views.default_storage.save', return_value='uploads/mock_file.jpg')
    @patch('api.views.default_storage.url', return_value='http://test.com/uploads/mock_file.jpg')
    def test_successful_file_upload(self, mock_storage_url, mock_storage_save, mock_users_find, mock_obs_insert, mock_loc_insert, mock_species_insert, mock_species_find, mock_loc_find, mock_obs_find_sid, mock_get_loc):
        """Test successful creation of an observation with a media file."""
        self._mock_user(mock_users_find)
        mock_loc_insert.return_value.inserted_id = ObjectId()
        mock_species_insert.return_value.inserted_id = ObjectId()
        mock_obs_insert.return_value.inserted_id = ObjectId()

        data = self.complete_taxonomy_data.copy()
        data['media_files'] = self.test_image

        request = self.factory.post('/api/upload/', data, **self.auth_headers)
        response = upload_observation(request)

        self.assertEqual(response.status_code, 200)
        mock_storage_save.assert_called()
        mock_obs_insert.assert_called_once()
        inserted_doc = mock_obs_insert.call_args[0][0]
        self.assertEqual(len(inserted_doc['photo']), 1)
        self.assertEqual(inserted_doc['photo'][0], 'http://test.com/uploads/mock_file.jpg')

    def test_authentication_failure_no_token(self, mock_get_loc):
        """Test that a request without a token fails with 401."""
        request = self.factory.post('/api/upload/', self.complete_taxonomy_data) # No auth headers
        response = upload_observation(request)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authorization header missing", json.loads(response.content)['error'])

    @patch('api.views.jwt.decode', side_effect=jwt.InvalidTokenError)
    def test_authentication_failure_invalid_token(self, mock_jwt_decode, mock_get_loc):
        """Test that a request with an invalid token fails with 401."""
        request = self.factory.post('/api/upload/', self.complete_taxonomy_data, **self.auth_headers)
        response = upload_observation(request)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid token", json.loads(response.content)['error'])