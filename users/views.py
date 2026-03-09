from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader


# Create your views here.

def login(request):
    temp = loader.get_template('login.html')
    context = {'is_member' : True}
    return HttpResponse(temp.render(context, request))
