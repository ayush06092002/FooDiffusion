"""Test for Medicine API"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Medicine

from medicine.serializers import (
    MedicineSerializer,
    MedicineDetailSerializer,
)

MEDICINES_URL = reverse('medicine:medicine-list')

def detail_url(medicine_id):
    """Create and return a medicine detail URL"""
    return reverse('medicine:medicine-detail', args=[medicine_id])


def create_medicine(user, **params):
    """Create and return a sample medicine"""
    defaults = {
        'name': 'Sample medicine',
        'ref_text': 'AFI',
        'dispensing_size': '200 ml',
        'dosage': '12 - 24 ml',
        'precautions': 'NS',
        'preferred_use': 'Both',
    }
    defaults.update(params)

    medicine = Medicine.objects.create(user=user, **defaults)
    return medicine

def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


class PublicMedicineAPITests(TestCase):
    """Test unauthenticated medicine API access"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(MEDICINES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMedicineAPITests(TestCase):
    """Test authenticated medicine API access"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email = 'user@example.com', password = 'test123')
        self.client.force_authenticate(self.user)

    def test_retrieve_medicines(self):
        """Test retrieving a list of medicines"""
        create_medicine(user=self.user)
        create_medicine(user=self.user)

        res = self.client.get(MEDICINES_URL)

        medicines = Medicine.objects.all().order_by('-id')
        serializer = MedicineSerializer(medicines, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_medicines_limited_to_user(self):
        """Test list of medicines is limited to authenticated user"""
        other_user = create_user(email = 'other@example.com', password = 'test123')
        create_medicine(user=other_user)
        create_medicine(user=self.user)

        res = self.client.get(MEDICINES_URL)

        medicines = Medicine.objects.filter(user=self.user)
        serializer = MedicineSerializer(medicines, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_medicine_detail(self):
        """Test viewing a medicine detail"""
        medicine = create_medicine(user=self.user)

        url = detail_url(medicine.id)
        res = self.client.get(url)

        serializer = MedicineDetailSerializer(medicine)
        self.assertEqual(res.data, serializer.data)

    def test_create_medicine(self):
        """Test creating a new medicine"""
        payload = {
            'name': 'Sample medicine',
            'ref_text': 'AFI',
            'dispensing_size': '200 ml',
            'dosage': '12 - 24 ml',
            'precautions': 'NS',
            'preferred_use': 'Both',
        }
        res = self.client.post(MEDICINES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        medicine = Medicine.objects.get(id=res.data['id'])

        for k, v in payload.items():
            self.assertEqual(getattr(medicine, k), v)
        self.assertEqual(medicine.user, self.user)

    def test_partial_update(self):
        """Test updating a medicine with patch"""
        original_name = 'Sample medicine'
        medicine = create_medicine(
            user = self.user,
            name = original_name,
            precautions = 'NS',
        )

        payload = {'precautions': 'Pregnancy'}
        url = detail_url(medicine.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        medicine.refresh_from_db()
        self.assertEqual(medicine.precautions, payload['precautions'])
        self.assertEqual(medicine.name, original_name)
        self.assertEqual(medicine.user, self.user)

    def test_full_update(self):
        """Test full update of medicine"""
        medicine = create_medicine(
            user = self.user,
            name = 'Sample medicine',
            ref_text = 'AFI',
            dispensing_size = '200 ml',
            dosage = '12 - 24 ml',
            precautions = 'NS',
            preferred_use = 'Both',
        )

        payload = {
            'name': 'New Sample medicine',
            'ref_text': 'AH',
            'dispensing_size': '100 gm',
            'dosage': '5 - 15 gm',
            'precautions': 'Pregnancy',
            'preferred_use': 'OPD',
        }
        url = detail_url(medicine.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        medicine.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(medicine, k), v)
        self.assertEqual(medicine.user, self.user)


    def test_update_user_returns_error(self):
        """Test cannot update user field"""
        new_user = create_user(email = 'user2@example.com', password = 'test123')
        medicine = create_medicine(user=self.user)
        payload = {'user': new_user.id}
        url = detail_url(medicine.id)
        self.client.patch(url, payload)

        medicine.refresh_from_db()
        self.assertEqual(medicine.user, self.user)

    def test_delete_medicine(self):
        """Test deleting a medicine successful"""
        medicine = create_medicine(user=self.user)
        url = detail_url(medicine.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Medicine.objects.filter(id=medicine.id).exists())

    def test_delete_other_users_medicine_error(self):
        """Test cannot delete other users medicine"""
        new_user = create_user(email = 'user2@exampl.com' , password = 'test123')
        medicine = create_medicine(user=new_user)

        url = detail_url(medicine.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Medicine.objects.filter(id=medicine.id).exists())