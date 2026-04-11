"""
URL configuration for com3610 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from courses import views as courses_views
from com3610 import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('users/',include("django.contrib.auth.urls")),
    path('',courses_views.home_router,name='index'),
    path('courses/',include("courses.urls")),

    path('quizzes/',include("quizzes.urls")),
    path('questions/',include("questions.urls")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = 'users.views.error_403'
handler404 = 'users.views.error_404'
handler500 = 'users.views.error_500'
handler405 = 'users.views.error_405'
handler401 = 'users.views.error_401'