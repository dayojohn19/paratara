from django.urls import path

from . import views

app_name = "invest"
urlpatterns = [
    path("", views.index, name="index"),
    path("recordss", views.records, name="records"),
    path("investors<str:csrf_token>", views.add_investor, name="add_investor"),
    path("reports", views.reports, name="reports"),
    path("portfolio", views.portfolio, name="portfolio"),
    path("reinvest<str:csrf_token>", views.reinvest, name="reinvest"),
    # path("computations", views.computations, name="computations"),
    path("<str:csrf_token>/InvestAmount",
         views.InvestAmount, name="InvestAmount"),
    #
    path("RecordTheDividend", views.RecordTheDividend, name="RecordTheDividend"),
    path("options", views.options, name="options"),
    path("contact/<str:userMessage>", views.contact, name="contact"),
    path("HandinStock", views.HandinStock, name="HandinStock"),
    path("HandoutStock", views.HandoutStock, name="HandoutStock"),
    path("checkMyRecord/<int:investor_id>",
         views.checkMyRecord, name="checkMyRecord")
]
