from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render

from users.views import error_403


# Create your views here.
@login_required(login_url='/users/login')
def index_dashboard(request):
    if request.user.is_student:
        return student_dashboard(request)

    elif request.user.is_teacher:
        return teacher_dashboard(request)

    elif request.user.is_admin:
        return admin_dashboard(request)

    else:
        return error_403(request)

@login_required(login_url='/users/login')
@user_passes_test(lambda user: user.is_student,redirect_field_name="error403",login_url="/users/login/")
def student_dashboard(request):
    return render(request, 'dashboard_student.html')


@login_required(login_url='/users/login')
@user_passes_test(lambda user: user.is_teacher,login_url="/users/login/")
def teacher_dashboard(request):
    return render(request, 'dashboard_teacher.html')


@login_required(login_url='/users/login')
@user_passes_test(lambda user: user.is_admin,login_url="/users/login/")
def admin_dashboard(request):
    return render(request, 'dashboard_admin.html')

