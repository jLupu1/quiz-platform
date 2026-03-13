from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template import loader


# Create your views here.

def index(request):
    if request.user.is_authenticated:
        print(request.user)
        temp = loader.get_template('courses/index.html')
        return HttpResponse(temp.render(request=request))
    else:
        return redirect('users/login')