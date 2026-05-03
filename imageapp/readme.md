To Use this

from imageapp.imageuploader import Upload_and_get_URL


Upload_and_get_URL(request) with files
return url

on html

<form action="{% url '' %}" method="POST" enctype="multipart/form-data" class="p-3 border rounded">
    <div class="mb-3">
        {% csrf_token %}
        <label for="formFile" class="form-label">Upload an image</label>
        <input required="" class="form-control" type="file" id="formFile" name="image" accept="image/*">
    </div>
    <button type="submit" class="btn btn-primary">Try Image</button>
</form>


