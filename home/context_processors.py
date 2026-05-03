

from django.core.cache import cache
from datetime import datetime
# Cache
# def navbar_context(request):
#     categories = cache.get('navbar_categories')
#     if categories is None:
#         categories = list(Category.objects.all())
#         cache.set('navbar_categories', categories, 300)  # cache for 5 minutes
#     return {"navbar_categories": categories}

def newSession(request, sessionName, value):
    from resorts.models import Packages, resortPackages, resortItem
    
    if sessionName == 'resort_object':
        print('\n\n\n New Resort Object')


    else:
        print('\n\n\n OLD RESORT OBJECT \n\n')


        pass
    request.session[sessionName] = value

def navbar_context(request):
    # from resorts.models import resortItem



    now = datetime.now()

    context = {
        # 'resortRooms' : getattr(request, "resortRooms", None) ,
        # 'resortRooms':request.resortRooms,
        # 'resortRooms': request.session['resort_rooms'],

        'month': now.month, 
        'year':now.year,
        'whatstepvalue':'update_id'
    }    

    # # resortCache = cache.get('resortcache')
    # # if resortCache is None:
    # #     pass
    # # resortObj = getattr(request, "resortObject", None)
    # newObj = request.session.get('new_resort_object', None)
    # if newObj is None:
    #     print('No resort Object Passed')
    #     resortObj = None
    #     return {}
    # else:
    #     resortObj = request.session.get('resort_object')
    #     if resortObj is None:
    #         return {}
    #     resortObj = resortItem.objects.get(id = resortObj)
    #     context.update(
    #         {
    #             'resortObject':resortObj,
    #             'resortName': resortObj.name,
    #             'resortRealName': resortObj.RealName,
    #             'resortID': resortObj.id,
    #         }
    #     )        
    # print('Resort Object: from session resort_object ',resortObj)
    # # if resortObj == None:
    # #     newSession(request, 'resort_object', resortObj)
    # #     resortObj = newObj
    # # if newObj != resortObj:
    # #     print('Found New Resort Object')
    # #     resortObj = newObj
    # #     request.session['resort_object'] = resortObj        
    # #     newSession(request,'resort_object',resortObj)


    # # if request.session.get('resort_object', None) != resortObj:
    # newSession(request,'resort_object',resortObj)






    

 
    # cache.set('resortcache', context, 600) 
    return context