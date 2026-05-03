from django.core import serializers
from .models import yourmodel
from django.http import HttpResponse


def example(request):
    objects = yourmodel.objects.all()
    with open(r'Mode_extracted_data.json', "w") as out:
        mast_point = serializers.serialize("json", objects)
        out.write(mast_point)
    # template = loader.get_template('some_template.html')
    context = {'object': objects}
    # return HttpResponse(template.render(context, request))
