from home.models import TouristSpot, Visit, UserCredentials
from django.utils import timezone
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

spot = TouristSpot.objects.get(name='Coconut Plantation View Point')
users = list(UserCredentials.objects.all())
num_users = len(users)
for i in range(50):
    user = users[i % num_users]  # cycle through users
    Visit.objects.create(tourist_spot=spot, tourist=user, timestamp=timezone.now())
print('Added 50 visits')