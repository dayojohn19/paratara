from rest_framework.serializers import ModelSerializer
from .models import Payments, Blogger, Blogs, Storeproducts
from home.models import  SiargaoEventSchedule, allSchedules

class PaymentSerializer(ModelSerializer):
    class Meta:
        model = Payments
        fields = '__all__'

class ScheduleSerializer(ModelSerializer):
    class Meta:
        model = SiargaoEventSchedule
        fields = '__all__'
class allSchedulesSerializer(ModelSerializer):
    class Meta:
        model = allSchedules
        fields = '__all__'

class BloggerSerializer(ModelSerializer):
    class Meta:
        model = Blogger
        fields = '__all__'

class BlogsSerializer(ModelSerializer):
    class Meta:
        model = Blogs
        fields = '__all__'
        # exclude = ['blogUser',]

class StoreproductsSerializer(ModelSerializer):
    class Meta:
        model = Storeproducts
        fields = '__all__'

# class BlogsSerializer(ModelSerializer):
#     class Meta:
#         model = Blogs
#         fields = '__all__'
