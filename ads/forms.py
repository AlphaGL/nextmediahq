# ads/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import AdvertiserProfile, Advertisement, AdSlot


class AdvertiserRegistrationForm(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'ads-input', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'ads-input', 'placeholder': 'Last Name'})
    )
    business_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'ads-input', 'placeholder': 'Business / Brand Name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'ads-input', 'placeholder': 'Business Email'})
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'ads-input', 'placeholder': 'Phone Number (e.g. 08012345678)'})
    )
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'ads-input', 'placeholder': 'Website URL (optional)'})
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'ads-input', 'placeholder': 'Create a password'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'ads-input', 'placeholder': 'Confirm password'})
    )
    agree_terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the advertising guidelines to continue.'}
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        return cleaned_data

    def save(self):
        data = self.cleaned_data
        email = data['email']
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=data['password1'],
            first_name=data['first_name'],
            last_name=data['last_name'],
        )
        AdvertiserProfile.objects.create(
            user=user,
            business_name=data['business_name'],
            phone_number=data['phone_number'],
            website=data.get('website') or None,
        )
        return user


class AdvertiserLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'ads-input', 'placeholder': 'Email Address'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'ads-input', 'placeholder': 'Password'})
    )


class AdvertiserPasswordResetForm(forms.Form):
    """
    Identity-verification reset form.
    The user must supply email + phone + business name (all must match their
    AdvertiserProfile) before a new password is accepted.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'ads-input', 'placeholder': 'The email you registered with'})
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'ads-input', 'placeholder': 'e.g. 08012345678'})
    )
    business_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'ads-input', 'placeholder': 'e.g. Ace Tutorials'})
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'ads-input', 'placeholder': 'At least 8 characters'})
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'ads-input', 'placeholder': 'Repeat new password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        email        = cleaned_data.get('email', '').strip()
        phone        = cleaned_data.get('phone_number', '').strip()
        business     = cleaned_data.get('business_name', '').strip()
        p1           = cleaned_data.get('new_password1', '')
        p2           = cleaned_data.get('new_password2', '')

        # ── Password rules ──────────────────────────────────────────────────
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")

        # ── Identity verification ────────────────────────────────────────────
        # Look up by email first so we don't leak which field is wrong
        try:
            user = User.objects.get(email__iexact=email)
            profile = user.advertiser_profile  # raises DoesNotExist if not an advertiser
        except (User.DoesNotExist, AdvertiserProfile.DoesNotExist):
            raise forms.ValidationError(
                "No advertiser account found matching those details. "
                "Please check your information and try again."
            )

        if profile.is_banned:
            raise forms.ValidationError(
                "This account has been suspended. Please contact support."
            )

        # Normalise phone: strip spaces/dashes for a loose comparison
        def _norm(s):
            return ''.join(c for c in s if c.isdigit())

        if _norm(profile.phone_number) != _norm(phone):
            raise forms.ValidationError(
                "The details you provided do not match our records. "
                "Please check your information and try again."
            )

        if profile.business_name.strip().lower() != business.lower():
            raise forms.ValidationError(
                "The details you provided do not match our records. "
                "Please check your information and try again."
            )

        # All good — attach user to form so the view can call save()
        self._verified_user = user
        return cleaned_data

    def save(self):
        user = self._verified_user
        user.set_password(self.cleaned_data['new_password1'])
        user.save(update_fields=['password'])
        return user


class AdvertisementForm(forms.ModelForm):
    """Form for creating a new advertisement — uses file upload for the banner image."""

    # Override the image field to get a proper styled file input
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'ads-file-input',
            'id': 'id_image',
            'accept': 'image/jpeg,image/png,image/webp',
        }),
        help_text='JPG, PNG or WebP. Max 2 MB. Recommended sizes below.',
    )

    class Meta:
        model = Advertisement
        fields = [
            'slot', 'ad_format', 'title', 'description',
            'image', 'cta_text', 'destination_url',
        ]
        widgets = {
            'slot': forms.Select(attrs={'class': 'ads-input'}),
            'ad_format': forms.Select(attrs={'class': 'ads-input'}),
            'title': forms.TextInput(attrs={
                'class': 'ads-input',
                'placeholder': 'e.g. Best Study Materials for WAEC 2025',
                'maxlength': '100',
            }),
            'description': forms.Textarea(attrs={
                'class': 'ads-input',
                'rows': 3,
                'placeholder': 'Short description (max 300 characters)',
                'maxlength': '300',
            }),
            'cta_text': forms.TextInput(attrs={
                'class': 'ads-input',
                'placeholder': 'e.g. Shop Now, Learn More, Get Started',
                'maxlength': '50',
            }),
            'destination_url': forms.URLInput(attrs={
                'class': 'ads-input',
                'placeholder': 'your business link or phone number',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        available = [
            slot.pk for slot in AdSlot.objects.filter(is_active=True)
            if not slot.is_full()
        ]
        self.fields['slot'].queryset = AdSlot.objects.filter(pk__in=available, is_active=True)

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # 2 MB limit
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image file is too large. Maximum size is 2 MB.")
            allowed = ('image/jpeg', 'image/png', 'image/webp')
            if hasattr(image, 'content_type') and image.content_type not in allowed:
                raise forms.ValidationError("Only JPG, PNG, or WebP images are accepted.")
        return image

    def clean(self):
        cleaned_data = super().clean()
        ad_format = cleaned_data.get('ad_format')
        image = cleaned_data.get('image')
        if ad_format in ('image', 'image_text') and not image:
            raise forms.ValidationError(
                "Please upload a banner image for image-based ads."
            )
        return cleaned_data