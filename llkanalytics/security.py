def staff_upload_allowed(request):
    return request.user.is_authenticated and request.user.is_active and request.user.is_staff
