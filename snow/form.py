from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Salon, Service, Product, Appointment, Message


# -----------------------------
# User Registration Form
# -----------------------------

class UserForm(UserCreationForm):
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES, label="I am a")
    salon_name = forms.CharField(required=False, label="Business Name")
    salon_address = forms.CharField(required=False, label="Business Address")
    provider_address = forms.CharField(required=False, label="Address")
    service_types = forms.MultipleChoiceField(
        required=False,
        choices=Service.SERVICE_TYPES,
        widget=forms.CheckboxSelectMultiple,
        label="Services Offered"
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role', 'password1', 'password2']

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        salon_name = cleaned_data.get("salon_name")
        salon_address = cleaned_data.get("salon_address")
        provider_address = cleaned_data.get("provider_address")

        # Validation based on role
        if role in ["salon", "shop"]:
            if not salon_name or not salon_address:
                raise forms.ValidationError("Business name and address are required for your role.")
        elif role == "provider":
            if not provider_address:
                raise forms.ValidationError("Address is required for service providers.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()

        # Handle salon/shop creation
        role = self.cleaned_data.get("role")
        if role in ["salon", "shop"]:
            salon_name = self.cleaned_data.get("salon_name")
            salon_address = self.cleaned_data.get("salon_address")
            if salon_name and salon_address:
                Salon.objects.create(
                    owner=user,
                    name=salon_name,
                    address=salon_address,
                    approved=False
                )

        # Service provider services
        service_types = self.cleaned_data.get("service_types")
        if role == "provider" and service_types:
            provider_address = self.cleaned_data.get("provider_address")
            # Create a virtual salon for provider
            virtual_salon = Salon.objects.create(
                owner=user,
                name=f"{user.username}'s Services",
                address=provider_address,
                approved=False
            )
            for stype in service_types:
                Service.objects.create(
                    salon=virtual_salon,
                    provider=user,
                    name=stype.title(),
                    service_type=stype,
                    price=0,
                    duration_minutes=30
                )

        return user


# -----------------------------
# Edit Profile / User Form
# -----------------------------
class UserEditForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank if you don't want to change your password."
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput,
        required=False
    )

    # Extra fields
    salon_name = forms.CharField(required=False, label="Business Name")
    salon_address = forms.CharField(required=False, label="Business Address")
    provider_address = forms.CharField(required=False, label="Address")
    service_types = forms.MultipleChoiceField(
        required=False,
        choices=Service.SERVICE_TYPES,
        widget=forms.CheckboxSelectMultiple,
        label="Services Offered"
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role']

    # Check username uniqueness excluding self
    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    # Validate role-dependent fields
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        salon_name = cleaned_data.get("salon_name")
        salon_address = cleaned_data.get("salon_address")
        provider_address = cleaned_data.get("provider_address")
        salon = getattr(self.instance, 'salon', None)

        if role in ["salon", "shop"]:
            if not (salon_name or salon_address or salon):
                raise forms.ValidationError("Business name and address are required for your role.")
        elif role == "provider":
            if not (provider_address or salon):
                raise forms.ValidationError("Address is required for service providers.")

        # Password match check
        pw1 = cleaned_data.get("password1")
        pw2 = cleaned_data.get("password2")
        if pw1 or pw2:
            if pw1 != pw2:
                raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        # Update password if provided
        pw = self.cleaned_data.get("password1")
        if pw:
            user.set_password(pw)

        if commit:
            user.save()

        # Update or create salon/shop
        salon_name = self.cleaned_data.get("salon_name")
        salon_address = self.cleaned_data.get("salon_address")
        salon = getattr(user, 'salon', None)

        if self.cleaned_data.get("role") in ["salon", "shop"]:
            if salon:
                salon.name = salon_name or salon.name
                salon.address = salon_address or salon.address
                salon.save()
            elif salon_name and salon_address:
                Salon.objects.create(
                    owner=user,
                    name=salon_name,
                    address=salon_address,
                    approved=False
                )

        # Update services for provider
        service_types = self.cleaned_data.get("service_types")
        if self.cleaned_data.get("role") == "provider" and service_types:
            provider_address = self.cleaned_data.get("provider_address")
            if not salon:
                salon = Salon.objects.create(
                    owner=user,
                    name=f"{user.username}'s Services",
                    address=provider_address,
                    approved=False
                )
            else:
                salon.address = provider_address or salon.address
                salon.services.all().delete()
                salon.save()
            for stype in service_types:
                Service.objects.create(
                    salon=salon,
                    provider=user,
                    name=stype.title(),
                    service_type=stype,
                    price=0,
                    duration_minutes=30
                )

        return user
# -----------------------------
# Product Form
# -----------------------------
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'image', 'gallery_image1', 'gallery_image2', 'gallery_image3', 'video', 'description', 'featured']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

# -----------------------------
# Service Form
# -----------------------------
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            'salon', 'provider', 'name', 'price', 'duration_minutes',
            'service_type', 'featured', 'promotion',
            'image', 'gallery_image1', 'gallery_image2', 'gallery_image3', 'video'
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)   # GET logged-in user from view
        super().__init__(*args, **kwargs)

        # Hide salon & provider for non-admins
        if user and user.role != 'admin':
            self.fields['salon'].widget = forms.HiddenInput()
            self.fields['provider'].widget = forms.HiddenInput()


# -----------------------------
# Appointment Form
# -----------------------------
class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['date_time']
        widgets = {'date_time': forms.DateTimeInput(attrs={'type': 'datetime-local'})}

# -----------------------------
# Message Form
# -----------------------------
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {'content': forms.Textarea(attrs={'rows':1, 'placeholder':'Type a message...', 'class':'message-input'})}
