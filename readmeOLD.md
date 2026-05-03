# Important to reset migrations

```
python manage.py migrate --fake [APP_name] zero
```

## These Linke [Migration](https://tech.raturi.in/how-reset-django-migrations)

## [Race models](g_pigeon_race/models.py)

# What is Viaje?

## Distinctiveness and Complexity

unlike other e-commerce buy and sell website or networking sites where you post what you are , This aims to gather individual people who share the same destinations and ease their travel and cost, <br><br> Also to help people share their plan for others who might have the same interest or intrigued to be a part of it<br><br> Using Javascript to fetch content from database to ease the loading time of html page and animation and design

## About Viaje

This app is good for people who are looking for weekend or weekdays gig, also for work travel nomads to ease their effort in search of place and people to go

## Uses Of Viaje

- Car Pooling <br> `If you have a car and want to have others to share the gas cost share your travel dates and destination` <br>

- Crowd Sourcing <br> `Search or Make an Event on Place Near You or in Place you want to go and be surprise to meet people wih similar interest`

# On each File Applications

- [Users](userProfile) - Folder where all users who sign up are stored here their provided for public information
- [home](home) - Where all the Application's model for Schedules, Places, Comments and Discussions are stored
- [settings](webSchedule) - Application's Settings
- [room](rooms) - Folder where users who would like to create their own website to advertise their place are store here, `** this is still under construction one of new feature to be released **`

# Contains 3 Main [models](home/models.py)

It has several Models but the main models on this app are:

- Schedule Model <br>`Model for Creating Departure Schedule from Oneplace to another, where Other people will see the Destination and the Point of Origin `
- Place Model <br>`Model for List of Place where User planned to Go with corresponding count of Schedule of Travel and Events`
- Discussion Model <br>`Events List that the User share to find other with similar interest`

# How to Run this [Application](manage.py)

## Requirements

1.  Clone this Project from git hub

        git clone [ Ctrl+C browser's URL ]

2.  After Cloning proceed to the Folder and type:

        pip3 insntall requirements.txt

3.  Run the Application by: python3 manage.py runserver
4.  Go to this Server at: [Home Page](http://127.0.0.1:8000/)

        http://127.0.0.1:8000/

# Instructions

## How to use

1.  [Create a Plan](http://127.0.0.1:8000/) where you want to Go
    - At the Bottom you you will find button how to contact us, feedback, SignUp/Login
    - On the Top Right You will see `Create a Viaje` button
      - Two Choices either Make or Find a Schedule
        - `Make` Schedule if you're planning an event/schedule to share with others
        - `Find` Schedule if you're looking to join others who might have the same destination you want to go
2.  On the Top left You will find `Search` Icon to ease your search
    - You will be redirected to Place's Page with a calender
      - You can Make a Discussion on the Place
      - Below the Dates are the meeting place
        - Click it to see further information about the Schedule
    - Icons on the side of the date represents what type of schedule it is, there are several types of schedule:
      - `Ride` if you are planning to go on that place and looking for extra passenger to ease the travel cost, basically its like car pooling with the maker as the driver, or can be if you're looking for a ride
      - `Bike` for biking
      - `Hike` for hiking Activities
      - `Dive` for diving enthusiasts
      - `Camp` for people who like to chill and bond
3.  Comment on a schedule made by others - On the top right you will see `New Schedule` button where you can easily add/make new Schedule on the same place
