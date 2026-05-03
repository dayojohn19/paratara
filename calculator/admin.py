from django.contrib import admin

# Register your models here.
from .models import Investor, Total_Investment, InvestmentRecord, StocksHand, SideComputations, TradeRecords, InterestTypes, DividendRecord

admin.site.register(Investor)
admin.site.register(Total_Investment)
admin.site.register(InvestmentRecord)
admin.site.register(StocksHand)
admin.site.register(SideComputations)
admin.site.register(TradeRecords)
admin.site.register(InterestTypes)
admin.site.register(DividendRecord)
