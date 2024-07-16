from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.validators import MinLengthValidator, MaxLengthValidator
from main_service.models import CustomUser
from .models import SupportRequest, GENDER_CHOICES, ICON_CHOICES
from django import forms
from django.utils.translation import gettext as _


class SupportForm(forms.ModelForm):
    class Meta:
        model = SupportRequest
        fields = ["name", "email", "subject", "message"]

    # def clean_photo(self):
    #     uploaded_photo = self.cleaned_data.get('photo')
    #     if uploaded_photo:
    #         if uploaded_photo.size > 1024 * 1024:
    #             raise forms.ValidationError('File size must be less than 1MB')
    #     return uploaded_photo


class StartBotForm(forms.Form):
    # ISOLATED, CROSSED
    MARGIN_CHOICES = (
        ("ISOLATED", "ISOLATED"),
        ("CROSSED", "CROSSED"),
    )

    total_investment = forms.DecimalField(
        label="Total Investment",
        widget=forms.NumberInput(attrs={"step": "0.1"}),
        min_value=0,  # Minimum value
        max_value=5000,  # Minimum value
        error_messages={
            "min_value": "Interval must be greater than 0.",
        },
        initial=1,
    )
    leverage = forms.IntegerField(
        label="Leverage",
        widget=forms.NumberInput(attrs={"step": "1"}),
        min_value=1,
        max_value=50,
        error_messages={
            "min_value": "Interval must be greater than 30.",
            "max_value": "Interval must be less than 90.",
        },
        initial=1,
    )
    margin_type = forms.ChoiceField(choices=MARGIN_CHOICES)


class MyForm(forms.Form):
    days_of_backtest = forms.IntegerField(
        label="Days of Backtest",
        widget=forms.NumberInput(attrs={"step": "30"}),
        min_value=30,  # Minimum value
        max_value=90,  # Maximum value
        error_messages={
            "min_value": "Interval must be greater than 30.",
            "max_value": "Interval must be less than 90.",
        },
        initial=30,
    )
    interval = forms.DecimalField(
        label="Interval",
        widget=forms.NumberInput(attrs={"step": "0.01"}),
        min_value=0.01,  # Minimum value
        max_value=10,  # Maximum value
        error_messages={
            "min_value": "Interval must be greater than 0.",
            "max_value": "Interval must be less than 10.",
        },
        initial=1.5,
    )
    start_balance = forms.DecimalField(
        label="Start Balance",
        widget=forms.NumberInput(attrs={"step": "100"}),
        min_value=100,  # Minimum value
        max_value=1000000000,  # Maximum value
        error_messages={
            "min_value": "Interval must be greater than or equal to 100.",
            "max_value": "Interval must be less than or equal to 100000000.",
        },
        initial=1000,
    )

    def clean(self):
        cleaned_data = super().clean()
        days_of_backtest = cleaned_data.get("days_of_backtest")
        # interval = cleaned_data.get('interval')
        # start_balance = cleaned_data.get('start_balance')

        # Add your custom validation logic here
        if (
            days_of_backtest % 30 != 0
            or days_of_backtest < 0
            or days_of_backtest > 1000000000
        ):
            self.add_error(
                "days_of_backtest", "Days of backtest must be between 0 and 1000000000."
            )

        return cleaned_data


class NewUserForm(UserCreationForm):
    error_messages = {
        "username": {
            "unique": _("A user with that username already exists."),
        },
        "email": {
            "unique": _("A user with that email already exists."),
        },
        "password_mismatch": _("The two password fields didn't match."),
    }

    class Meta:
        model = CustomUser
        fields = (
            "username",
            "first_name",
            "last_name",
            "gender",
            "icon",
            "email",
            "password1",
            "password2",
        )

    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
        initial="",  # Set the initial value to an empty string
    )
    icon = forms.ChoiceField(
        choices=ICON_CHOICES,
        required=True,
        initial="man_1.png",  # Set the initial value to "man_1.png"
    )

    username = forms.CharField(
        required=True,
        label="Username",
        help_text="",
        validators=[
            MinLengthValidator(
                limit_value=4, message="Username must have at least 4 characters."
            ),
            MaxLengthValidator(
                limit_value=32, message="Username cannot exceed 32 characters."
            ),
        ],
        widget=forms.TextInput(attrs={"class": "custom-input"}),
    )
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("Enter your password."),
    )

    def __init__(self, *args, **kwargs):
        super(NewUserForm, self).__init__(*args, **kwargs)
        # Set the initial value for gender and icon fields
        self.fields["gender"].initial = GENDER_CHOICES[0][0]  # Set to the first choice
        self.fields["icon"].initial = "man_1.png"  # Set to the desired icon

    def save(self, commit=True):
        user = super(NewUserForm, self).save(commit=False)
        if commit:
            user.save()
        return user


class UserProfileUpdateForm(UserChangeForm):
    password = forms.CharField(
        label="Password",
        required=False,
        validators=[
            MinLengthValidator(
                limit_value=8, message="Password must have at least 8 characters."
            ),
            MaxLengthValidator(
                limit_value=32, message="Password cannot exceed 32 characters."
            ),
        ],
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "new-password", "placeholder": "Password"},
        ),
    )

    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "gender", "email", "password")

    username = forms.CharField(
        required=True,
        label="Username",
        help_text="",
        validators=[
            MinLengthValidator(
                limit_value=4, message="Username must have at least 4 characters."
            ),
            MaxLengthValidator(
                limit_value=32, message="Username cannot exceed 32 characters."
            ),
        ],
        widget=forms.TextInput(attrs={"class": "custom-input"}),
    )
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        required=False,
        initial="",
    )

    def __init__(self, *args, **kwargs):
        super(UserProfileUpdateForm, self).__init__(*args, **kwargs)

        # Remove labels for the fields
        for field_name, field in self.fields.items():
            field.label = ""
