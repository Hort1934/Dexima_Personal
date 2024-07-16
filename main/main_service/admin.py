from django.contrib import admin
from main_service.models import CustomUser, SupportRequest, Strategy

admin.site.register(CustomUser)
admin.site.register(SupportRequest)
admin.site.register(Strategy)
