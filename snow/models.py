from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, Group, Permission

# Custom User
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('salon', 'Salon Owner'),
        ('shop', 'Beauty Shop Owner'),
        ('provider', 'Service Provider'),
        ('user', 'Regular User'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    is_approved = models.BooleanField(default=False)
    latitude = models.FloatField(default=0.3476)
    longitude = models.FloatField(default=32.5825)
    address = models.CharField(max_length=255, blank=True, null=True)

    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# Salon
class Salon(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='owned_salons', 
        null=True, 
        blank=True
    )
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    rating = models.FloatField(default=0)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    latitude = models.FloatField(default=0.3476)
    longitude = models.FloatField(default=32.5825)

    def __str__(self):
        return self.name


# Service

class Service(models.Model):
    SERVICE_TYPES = [
        ('haircut', 'Haircut'),
        ('hairdress', 'Hairdress'),
        ('styling', 'Styling'),
        ('coloring', 'Coloring'),
        ('massage', 'Massage'),
        ('facial', 'Facial'),
        ('nail', 'Nail'),
        ('makeup', 'MakeUp'),
    ]
    salon = models.ForeignKey(
        Salon, on_delete=models.CASCADE, related_name='services', null=True, blank=True
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='services', null=True, blank=True
    )
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.IntegerField()
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES, default='haircut')
    featured = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    promotion = models.CharField(max_length=100, blank=True, null=True)
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    gallery_image1 = models.ImageField(upload_to='services/gallery/', blank=True, null=True)
    gallery_image2 = models.ImageField(upload_to='services/gallery/', blank=True, null=True)
    gallery_image3 = models.ImageField(upload_to='services/gallery/', blank=True, null=True)
    video = models.FileField(upload_to='services/videos/', blank=True, null=True)

    def __str__(self):
        location = self.salon.name if self.salon else self.provider.username
        return f"{self.name} - {location}"



# Appointment
class Appointment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    status = models.CharField(max_length=20, default='booked')

    def __str__(self):
        return f"{self.user.username} - {self.service.name} ({self.date_time})"


# Product
class Product(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='products',
        default=1
    )  # owner is the shop owner
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    description = models.TextField(blank=True, null=True)
    featured = models.BooleanField(default=False)

    gallery_image1 = models.ImageField(upload_to='products/gallery/', blank=True, null=True)
    gallery_image2 = models.ImageField(upload_to='products/gallery/', blank=True, null=True)
    gallery_image3 = models.ImageField(upload_to='products/gallery/', blank=True, null=True)
    video = models.FileField(upload_to='products/videos/', blank=True, null=True)
 
    def __str__(self):
        return self.name

    def related_products(self):
        return Product.objects.filter(owner=self.owner).exclude(id=self.id)[:4]

class Review(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name="reviews")
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
# Conversation
class Conversation(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='conversations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation: {self.salon.name} <-> {self.user.username}"


# Message
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
