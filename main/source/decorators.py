from django.utils import translation

from main_service.forms import SupportForm
from django.utils.translation import activate


def set_user_language(view_func):
    def wrapped(request, *args, **kwargs):
        if "message" in request.POST:
            form = SupportForm(request.POST, request.FILES)
            if form.is_valid():
                user = request.user
                support_request = form.save(commit=False)

                support_request.user_id = user.id
                support_request.save()
                request.session["form_saved_success"] = True
            else:
                request.session["form_saved_error"] = True

        # Добавьте обработку выбора языка, предполагая, что язык передается как параметр lang в POST-запросе
        if request.method == "GET":
            if "lang" in request.GET:
                lang = request.GET["lang"]
                if lang in ["en", "uk"]:
                    activate(lang)  # Set the selected language
                    request.session["user_language"] = (
                        lang  # Save the selected language in the session
                    )
                else:
                    request.session["user_language"] = (
                        None  # Clear the selected language
                    )

        if "user_language" in request.session:
            translation.activate(request.session["user_language"])

        return view_func(request, *args, **kwargs)

    return wrapped


def support_form(view_func):
    def wrapped(request, *args, **kwargs):
        if "lang" in request.GET or "lang" in request.POST:
            user_language = request.GET.get("lang", request.POST.get("lang"))
            request.session["user_language"] = user_language
            translation.activate(request.session.get("user_language"))
        translation.activate(request.session.get("user_language"))
        return view_func(request, *args, **kwargs)

    return wrapped
