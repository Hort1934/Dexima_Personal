# forms.py
from django import forms


class TradingInstrumentFilterForm(forms.Form):
    trading_pair = forms.CharField(max_length=50, required=False)
    price = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    price_change_in_24h = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    volume_change_in_24h = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
