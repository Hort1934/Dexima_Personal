from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render


@login_required
def forex_index(request) -> HttpResponse:
    return render(request, "forex_service/forex_index.html")
