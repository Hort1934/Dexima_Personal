from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render


@login_required
def commodity_index(request) -> HttpResponse:
    return render(request, "commodity_service/commodity_index.html")
