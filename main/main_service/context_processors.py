from django.core.cache import cache


def user_message_processor(request):
    user_message = None

    if request.user.username:
        user_message = cache.get(request.user.username)
    else:
        registration_message_key = request.session.get('registration_message_key')
        if registration_message_key:
            user_message = cache.get(registration_message_key)

    return {'user_message': user_message}
