# # list_of_possible_locations = ['cebu sinulog festival','naic cavite']

# # x = [f.split(' ')[0] for f in list_of_possible_locations]

# # # FileList = [f for f in listdir(self.exportFrom) if isfile(join(self.exportFrom, f))]
# # print(x)
# x = 'the quick brown fox jump over the fence'
# x = ' '.join([f.capitalize() for f in x.split(' ')])

# print(x)
# x = 'asdasdas'
# print(x[:3])

# time= "2022-09-27 03:17:28"
# z = time.split('-')


# # print(y)
# for i in range(len(z)):
#     print(i+1)
# # from datetime import datetime
# # print(datetime.now().month)
# x = 1 
# x +=1
# print('X: ',x)

# from datetime import datetime
# x = datetime.now().day
# print(x)
import datetime
x = {'available': True,
 'comments': 459,
 'comments_full': None,
 'factcheck': None,
 'fetched_time': datetime.datetime(2021, 4, 20, 13, 39, 53, 651417),
 'image': 'https://scontent.fhlz2-1.fna.fbcdn.net/v/t1.6435-9/fr/cp0/e15/q65/58745049_2257182057699568_1761478225390731264_n.jpg?_nc_cat=111&ccb=1-3&_nc_sid=8024bb&_nc_ohc=ygH2fPmfQpAAX92ABYY&_nc_ht=scontent.fhlz2-1.fna&tp=14&oh=7a8a7b4904deb55ec696ae255fff97dd&oe=60A36717',
 'images': ['https://scontent.fhlz2-1.fna.fbcdn.net/v/t1.6435-9/fr/cp0/e15/q65/58745049_2257182057699568_1761478225390731264_n.jpg?_nc_cat=111&ccb=1-3&_nc_sid=8024bb&_nc_ohc=ygH2fPmfQpAAX92ABYY&_nc_ht=scontent.fhlz2-1.fna&tp=14&oh=7a8a7b4904deb55ec696ae255fff97dd&oe=60A36717'],
 'is_live': False,
 'likes': 3509,
 'link': 'https://www.nintendo.com/amiibo/line-up/',
 'post_id': '2257188721032235',
 'post_text': 'Don’t let this diminutive version of the Hero of Time fool you, '
              'Young Link is just as heroic as his fully grown version! Young '
              'Link joins the Super Smash Bros. series of amiibo figures!\n'
              '\n'
              'https://www.nintendo.com/amiibo/line-up/',
 'post_url': 'https://facebook.com/story.php?story_fbid=2257188721032235&id=119240841493711',
 'reactions': {'haha': 22, 'like': 2657, 'love': 706, 'sorry': 1, 'wow': 123}, # if `extra_info` was set
 'reactors': None,
 'shared_post_id': None,
 'shared_post_url': None,
 'shared_text': '',
 'shared_time': None,
 'shared_user_id': None,
 'shared_username': None,
 'shares': 441,
 'text': 'Don’t let this diminutive version of the Hero of Time fool you, '
         'Young Link is just as heroic as his fully grown version! Young Link '
         'joins the Super Smash Bros. series of amiibo figures!\n'
         '\n'
         'https://www.nintendo.com/amiibo/line-up/',
 'time': datetime.datetime(2019, 4, 30, 5, 0, 1),
 'user_id': '119240841493711',
 'username': 'Nintendo',
 'video': None,
 'video_id': None,
 'video_thumbnail': None,
 'w3_fb_url': 'https://www.facebook.com/Nintendo/posts/2257188721032235'}
print(x['text'][:30])