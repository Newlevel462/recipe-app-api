from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Main course'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Cinnamon'):
    """Create and return a sample ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.00,
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API access"""

    def setUp(self):
        self.client = APIClient()

    def test_required_auth(self):
        """Test the authenticaiton is required"""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated recipe API access"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@londonappdev.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving list of recipes"""
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for user"""
        user2 = get_user_model().objects.create_user(
            'other@londonappdev.com',
            'password123'
        )
        sample_recipe(user=user2)
        sample_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_view_recipe_detail(self):
        """Test viewing a recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    # test recipe creation with default params
    def test_create_basic_recipe(self):
        payload = {
            'title': 'choco cheese cake',
            'time_miniutes': 30,
            'price': 5.00
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])
        # check if each of those payload keys are assigned
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    # test recipe creation with Tags
    def test_create_recipe_with_tags(self):
        tag1 = sample_tag(user=self.user, name="Vegan")
        tag2 = sample_tag(user=self.user, name="Dessert")

        payload = {
            'title': 'choco cheese cake',
            'time_miniutes': 30,
            'price': 5.00,
            'tags': [tag1.id, tag2.id]
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        # assert in is used to check if a value is in a list / queryset
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    # test recipe creation with ingredients
    def test_create_recipe_with_ingredients(self):
        ingredient1 = sample_ingredient(user=self.user, name="coco")
        ingredient2 = sample_ingredient(user=self.user, name="creme")
        payload = {
            'title': 'choco cheese cake',
            'time_miniutes': 30,
            'price': 5.00,
            'ingredients': [ingredient1.id, ingredient2.id]
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        # assert in is used to check if a value is in a list / queryset
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    # test partial update recipe (PATCH)
    def test_partial_update_recipe(self):
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))

        # now lets replace this tag with a new tag
        new_tag = sample_tag(self.user, name="curry")
        payload = {
            'title': 'indian curry',
            'tags': [new_tag.id]
        }
        self.client.patch(detail_url(recipe.id), payload)

        recipe.refresh_from_db()

        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    # test full update of recipe (PUT)
    def test_full_update_recipe(self):
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))

        payload = {
            'title': 'new title',
            'time_miniutes': 7,
            'price': 12.00
        }
        self.client.put(detail_url(recipe.id), payload)

        recipe.refresh_from_db()

        # check if each of those payload keys are assigned
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
        # check if tags is empty
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 0)

    # for delete
    # self.client.delete(detail_url(recipe.id))
