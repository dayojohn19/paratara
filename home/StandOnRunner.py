import re
import json
from datetime import datetime
import time
from .models import Places_v2, allSchedules, Comment
currentSecond= datetime.now().second
currentMinute = datetime.now().minute
currentHour = datetime.now().hour
currentMonth = datetime.now().strftime('%B')
currentYear = datetime.now().year


# dateLocations = self.FindString(post['post_text'], [f.split(' ')[0] for f in self.list_of_possible_locations])
def testStandOn():
    from .models import Places_v2, allSchedules, Comment
    JsonRunner()
    return 'Done'



Additional_Locations= ['mabini', 'batangas', 'mauban', 'macalelon', 'bolinao','dingalan', 'pulag','ulap','baguio','makiling','Ilocos','baguio','la union','sagada','baler','zambales','rizal','laguna','cavite','dingalan','burias','bataan','albay','daytour']
facebook_pages = ['1045754699134984','diveasiaPHSubicBay','1991336444419869','1734682023490096','369003129965960','513797347138269','freedivingbuddiesph','diveasiaPHSubicBay']
class JsonRunner():
    
    def __init__(self):
        self.fData = '1709401569337254.json'
        self.DateLists = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
        self.Npages = 40
        try:
            # from .models import Places_v2, allSchedules, Comment
            self.list_of_possible_locations = [i.placename for i in Places_v2.objects.all()]
            self.list_of_possible_locations+=Additional_Locations
        except:
            self.list_of_possible_locations = Additional_Locations

    def surfData(self):
        from facebook_scraper import get_posts
        for facebook_group_page in facebook_pages:

            for post in get_posts(facebook_group_page, pages=self.Npages, options={"comments":True}):
                self.PolishPost(post)
                time.sleep(0.5)

    def readData(self):
        with open(self.fData) as f:
            d = json.load(f)
            for post in d['posts']:
                self.PolishPost(post)




    def PolishPost(self,post):
        print(f"""
        *********************************************
        Create Function that check
        Post ID: {post['post_id']} 
        And Prevent Polishing if the same
        **********************************************
        """)
        time.sleep(1.5)
        # Creating Schedule DONE
        dateLocations = self.FindString(post['post_text'], [f.split(' ')[0] for f in self.list_of_possible_locations])
        if len(dateLocations) <=0:
            print("\n---------- NO LOCATION ------------\n")
            return        
        dateSchedules = self.FindString(post['post_text'], self.DateLists)
        if dateSchedules == []:
            dateSchedules.append(currentMonth)
        print(f"""
        **********************************
        Found Post:
        Month: {dateSchedules} 
        Locations: {dateLocations}
        ----------------------------------
            """)

        try:
            for location in dateLocations:
                print(f"""
                Creating Schedule in {location}
                ------------------------------
                """)
                # if location != '': newPlace = Places_v2.objects.get_or_create(placename__iexact=location)[0]
                from .models import Places_v2
                PlaceForSchedule = Places_v2.objects.filter(placename__icontains=location)
                print(f"""
                Found Registered Places: {PlaceForSchedule}
                """)
                if len(PlaceForSchedule) <= 0: 
                    location = location.capitalize()
                    newPlace = Places_v2.objects.create(placename=location)
                    newPlace.placeID = newPlace.id
                    newPlace.save()
                    PlaceForSchedule = [newPlace]
                    print(f"""
                    ****** NOTHING Registerd Place Found Creating new {PlaceForSchedule}            
                    """)

                for eachPlace in PlaceForSchedule:
                    if eachPlace is None:
                        continue
                    print(f"""
                    Adding Schedule in {eachPlace}
                    todo
                    """)
                    # eachPlace.add(MadeSchedule)
                    time.sleep(0.2)  
                    for i in range(len(dateSchedules)) :
                        MadeSchedule= allSchedules()
                        MadeSchedule.monthN+=int(post['time'].split('-')[1])+int(i)
                        print('MAKING MONTH : ',MadeSchedule.monthN)
                        time.sleep(1)
                        MadeSchedule.schedulePlace = eachPlace
                        MadeSchedule.detailsContact = post['user_url']
                        MadeSchedule.posterName = post['username']
                        MadeSchedule.posterURL = post['post_url']
                        if post['image_lowquality'] is not None:
                            MadeSchedule.scheduleImageURL = post['image_lowquality']
                        else:
                            if post['image'] is not None:
                                MadeSchedule.scheduleImageURL = post['image']
                            else:
                                MadeSchedule.scheduleImageURL = 'No Available Image'
                        
                        MadeSchedule.additionalDetails = post['post_text']
                        MadeSchedule.otherDetails = post['text']
                        if post['header'] is not None: MadeSchedule.meetPlace = post['header']
                        else: MadeSchedule.meetPlace = 'Click for more info'
                        MadeSchedule.save()
                        MadeSchedule.fetchID = post['post_id']
                        MadeSchedule.scheduleID = MadeSchedule.id
                        if MadeSchedule.scheduleTitle: MadeSchedule.scheduleTitle = post['header'][:60]
                        for comment in post['comments_full']:
                            MadeComment = Comment()
                            MadeComment.schedule = MadeSchedule
                            MadeComment.message = comment['comment_text']
                            MadeComment.messanger = comment['commenter_name']
                            MadeComment.origin = 'scrape'
                            MadeComment.save()
                            MadeSchedule.comment.add(MadeComment)
                            print("Comment Added")
                        MadeSchedule.save()
                        eachPlace.placesSchedules.add(MadeSchedule)
                continue
        except Exception as e:
            print('\n\n ****** EXEPTION' ,e,'\n\n')
        time.sleep(0.2)

    def FindString(self, toFind,toLook):
        results = []
        for lookHere in toLook:
            if re.search(lookHere, toFind, re.IGNORECASE):
                results.append(lookHere)
        # print('Result Found: ',results, toFind[::15])
        return results
# JsonRunner()




def scrapeFacebook():
    import groupScrape
    groupScrape.readDatas('1991336444419869')
    print('\n\n SCRAPPING \n\n\n')

