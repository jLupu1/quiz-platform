from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render


# Create your views here.
def index_dashboard(request):
    if request.user.is_student:
        return student_dashboard(request)
    elif request.user.is_teacher:
        return HttpResponse("You're a teacher")
    else:
        return HttpResponse("You're not a Admin")
# @login_required(login_url='/users/login')
@user_passes_test(lambda user: user.is_student,redirect_field_name="error403",login_url="/users/login/")
def student_dashboard(request):
    return render(request, 'dashboard_student.html')

