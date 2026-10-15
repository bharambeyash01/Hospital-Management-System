from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Include the URLs from our hospital app
    path('', include('hospital.urls')), 
]