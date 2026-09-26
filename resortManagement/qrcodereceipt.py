import qrcode
import base64
from io import BytesIO
from django.shortcuts import render
from urllib.parse import urlencode
from django.http import QueryDict
from resorts.models import resortItem
import json

data = {"name": "John", "age": 30}
query_string = urlencode(data)


def dict_to_url(data: dict) -> str:
    json_str = json.dumps(data)
    encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
    # return encoded
    imageStr = create_qr(encoded) # to be put on html
    # imageDict = url_to_dict(encoded)
    data = imageStr
    
    return data
    # data = {"user": {"name": "John", "role": "admin"}}
    # token = dict_to_url(data)
    # Gives something like:
    # eyJ1c2VyIjp7Im5hbWUiOiJKb2huIiwicm9sZSI6ImFkbWluIn19

def url_to_dict(encoded: str) -> dict:
    try:
        decoded_json = base64.urlsafe_b64decode(encoded.encode()).decode()
        return json.loads(decoded_json)
    except:
        return {}

def my_page(request,qr_strings):
    # qr_strings = {
    #     'a':1,
    #     'b':'b',
    #     'c':'cc',
    #     'd':2
    # }
    # decoded_json = base64.urlsafe_b64decode(qr_strings.encode()).decode()
    # data = json.loads(decoded_json)
    # print('Decoded Data: ',data )
    print('QR STRINGS: ',qr_strings)
    dictdata = url_to_dict(qr_strings)

    imageStr = dict_to_url(dictdata)
    print('imageStr: ',imageStr)
    print('Dict Data: ', dictdata)
    resort_details = None
    try:
        resort_id = int(dictdata.get('resort'))
        resort_details = resortItem.objects.filter(pk=resort_id).first()
    except (TypeError, ValueError):
        pass
    if resort_details:
        dictdata['resort_address'] = dictdata.get('resort_address') or resort_details.address
        dictdata['resort_contact_number'] = dictdata.get('resort_contact_number') or resort_details.contactNumber
        dictdata['resort_contact_email'] = dictdata.get('resort_contact_email') or resort_details.contactEmail
        dictdata['resort_whatsapp_number'] = dictdata.get('resort_whatsapp_number') or resort_details.whatsappNumber
        dictdata['resort_open_hours'] = dictdata.get('resort_open_hours') or resort_details.open_hours
        dictdata['resort_website'] = dictdata.get('resort_website') or resort_details.websiteURL
        dictdata['resort_description'] = dictdata.get('resort_description') or resort_details.description
    resort_name = (
        dictdata.get('resort_name_display')
        or dictdata.get('resort_name')
        or (resort_details.RealName or resort_details.name if resort_details else '')
    )
    resort_address = dictdata.get('resort_address') or ''
    resort_logo = dictdata.get('resort_logo') or ''
    return render(
        request,
        "resortManagement/qr_page.html",
        {
            "imageStr": imageStr,
            'dictdata': dictdata,
            'resort_name': resort_name,
            'resort_address': resort_address,
            'resort_logo': resort_logo,
        }
    )
    # return render(request, "garden/qr_page.html", {"qr_code": img_str})
    # return render(request, "page.html", {"data": data})
        


# qs = QueryDict("name=John&age=30")
# data = qs.dict()   # converts to normal dict
# print(data)
# print(data['name'])
# data_dict = {}
# data_dict = json.loads(base64.urlsafe_b64decode(encoded.encode()).decode())


def create_qr(qr_strings):
    qs = QueryDict(qr_strings)
    data = qs.dict()
    data_dict = {}
    print('QR VIEWing')
    data = f'https://www.paratara.com/resortManagement/qr/{qr_strings}'
    qr = qrcode.QRCode(version=1, box_size=10,border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", black_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str

#     # return render(request, "garden/qr_page.html", {"qr_code": img_str})

