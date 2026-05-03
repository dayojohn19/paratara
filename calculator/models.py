from django.db import models

# Create your models here.


class Total_Investment(models.Model):
    amount = models.IntegerField(default=0)  # iCLub Total Value
    average = models.FloatField(blank=True, default=0)  # Invested calculated
    balance = models.IntegerField(default=0)
    # Invested actual the Only investd amount
    gatheredAmount = models.IntegerField(blank=True, default=0)
    stock = models.CharField(max_length=64)
    portfolioValue = models.IntegerField(default=0)

# ####################################
# ############ INVESTOR SECTION ######
# ####################################


class InterestTypes(models.Model):
    RatioInterest = models.ManyToManyField(
        'calculator.Investor', blank=True, related_name='ratioList')
    FixInterest = models.ManyToManyField(
        'calculator.Investor', blank=True, related_name='fixList')
    GrowthInterest = models.ManyToManyField(
        'calculator.Investor', blank=True, related_name='growthList')

    Year = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def RatioInvestors(self):
        return self.RatioInterest.all()

    def FixInvestors(self):
        return self.FixInterest.all()

    def GrowthInvestors(self):
        return self.GrowthInterest.all()

    # def __str__(self):
    #     return f"{self.type} -\n  {self.percentage}% - {self.duration} - "


class Investor(models.Model):
    # NEW
    # interestType = models.ForeignKey(
    #     InterestTypes, on_delete=models.CASCADE, related_name='TypeofInterest', null=True, blank=True)
    interestType = models.CharField(max_length=32, blank=True)
    interest = models.FloatField(blank=True, default=0)
    duration = models.CharField(max_length=32, blank=True)

    dividendsReceived = models.ManyToManyField(
        'calculator.DividendRecord', blank=True, related_name='dividendGiven')

    investmentHistory = models.ManyToManyField(
        'calculator.InvestmentRecord', blank=True, related_name='investrecordhistory')

    # end New
    investor_name = models.CharField(max_length=64)
    investor_contact = models.CharField(max_length=64, blank=True)
    invested_percentage = models.FloatField(default=0)
    invested_amount = models.IntegerField(default=0)
    invested_value = models.IntegerField(default=0)
    reinvested = models.DateTimeField(auto_now=False, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.investor_name} - {self.interestType} - "

    @property
    def dividendReceivedList(self):
        return self.dividendsReceived.all()

    def investHistory(self):
        return self.investmentHistory.all()


class DividendRecord(models.Model):
    investorID = models.IntegerField(default=0)
    investedAmount = models.IntegerField()
    investedValue = models.IntegerField()
    investedProfit = models.IntegerField()
    contractRatio = models.FloatField(default=0)
    investedDividend = models.IntegerField(default=0)
    # valueDeducted = models.IntegerField(default=0)
    deliveredDividend = models.BooleanField(default=False)

    timestamp = models.DateTimeField(auto_now_add=True)


class InvestmentRecord(models.Model):
    timestamp = models.DateTimeField(auto_now=True)  # Initial Invested
    timestamp2 = models.DateTimeField(auto_now_add=True)  # Re invested

    investedPercentageBefore = models.FloatField(default=0)  # NEW
    investedPercentageAfter = models.FloatField(default=0)  # NEW
    CurrentiClubValue = models.IntegerField(default=0)  # NEW
    invest_valueBefore = models.IntegerField(default=0)
    investor_name = models.CharField(max_length=64)
    invest_amount = models.IntegerField()
    investor_id = models.IntegerField()

    # def __str__(self):
    #     return f" {self.investor_name}__Php {self.invest_amount} "


# ####################################
# ############ STCOKS SECTION ########
# ####################################


class StocksHand(models.Model):
    stockQuantity = models.IntegerField()
    stockBuyPrice = models.FloatField()
    stockName = models.CharField(max_length=64)

    def __str__(self):
        return f" {self.stockName} "

 
class TradeRecords(models.Model):
    stockName = models.CharField(max_length=32)
    stockQuantity = models.IntegerField(default=0)
    TransactionSide = models.CharField(max_length=32)
    stockPrice = models.FloatField()
    CostAfterTax = models.IntegerField()

    timestamp = models.DateTimeField(auto_now=True)  # Initial Invested

    def __str__(self):
        return f" {self.stockName} __ {self.TransactionSide} __ {self.timestamp}"


class SideComputations(models.Model):
    YearComputation = models.IntegerField(default=2022)
    MonthComputation = models.IntegerField(blank=True, default=1)
    DateComputation = models.IntegerField(blank=True, default=1)
    #
    InterestComputation = models.FloatField(default=0)
    ProfitComputation = models.IntegerField(default=0)
    #

    side = models.CharField(max_length=32)  # BUY OR SELL
    sideAmount = models.IntegerField(blank=True, default=0)
    updatedTime = models.DateTimeField(auto_now=True, blank=True)
    startTime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f" {self.side} __ {self.sideAmount} __ {self.YearComputation}"

    # sell = models.ManyToManyField(
    #     TradeRecords, blank=True, related_name='selling')
    # buy = models.ManyToManyField(
    #     TradeRecords, blank=True, related_name='buying')

    # @property
    # def sellValue(self):
    #     TotalSell = 0
    #     for sellItem in self.sell:
    #         TotalSell += int(sellItem.CostAfterTax)
    #     return TotalSell

    # def buyValue(self):
    #     TotalBuy = 0
    #     for buyItem in self.buy:
    #         TotalBuy += int(buyItem.CostAfterTax)
    #     return TotalBuy
