from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q
from django.core.serializers.json import DjangoJSONEncoder
import json
from .models import Salon, Service, Appointment, Product, Conversation, Message,CustomUser
from .form import UserForm, ServiceForm, ProductForm, AppointmentForm, MessageForm,UserEditForm

# -----------------------
# Helper Functions
# -----------------------

def owner_required(user):
    return user.is_authenticated and Salon.objects.filter(owner=user).exists()

def admin_required(user):
    """Check if the user is an admin (role='admin')."""
    return user.is_authenticated and getattr(user, 'role', '') == 'admin'

@login_required
@user_passes_test(admin_required)
def ajax_user_form(request):
    role = request.GET.get('role')
    form = UserForm(initial={'role': role})
    html = render_to_string('snow/partials/users_list.html', {'form': form, 'roles': CustomUser.ROLE_CHOICES}, request=request)
    return JsonResponse({'html': html})


@login_required
def dashboard(request):
    user = request.user

    if not user.is_approved:
        return render(request, 'snow/partials/apending_approval.html')

    if user.role == 'salon':
        return render(request, 'snow/partials/salon_dashboard.html')
    elif user.role == 'shop':
        return render(request, 'snow/partials/shop_dashboard.html')
    elif user.role == 'provider':
        return render(request, 'snow/partials/provider_dashboard.html')
    else:
        return render(request, 'snow/partials/user_dashboard.html')

@login_required
def admin_approve_users(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    pending_users = CustomUser.objects.filter(is_approved=False)
    return render(request, 'snow/partials/approve_users.html', {'pending_users': pending_users})

@login_required
def approve_user(request, user_id):
    if request.user.role != 'admin':
        return redirect('dashboard')

    user_to_approve = CustomUser.objects.get(id=user_id)
    user_to_approve.is_approved = True
    user_to_approve.save()
    return redirect('admin_approve_users')

def ajax_response(request, template_name, context, fallback_template=None):
    """Return JSON HTML if AJAX, else render fallback template."""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string(template_name, context, request=request)
        return JsonResponse({'html': html})
    fallback = fallback_template or template_name
    return render(request, fallback, context)


# Unified login view
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            if not user.is_approved:
                messages.error(request, "Your account is not approved yet.")
            elif not user.is_active:
                messages.error(request, "Your account is inactive.")
            else:
                login(request, user)
                # Redirect based on role
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role in ['salon', 'shop', 'provider']:
                    return redirect('owner_dashboard')
                else:
                    return redirect('dashboard')  # regular users
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'snow/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

def register(request):
    """Handle user registration for all roles."""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_approved = False
            user.save()

            role = form.cleaned_data.get('role')
            salon_name = form.cleaned_data.get('salon_name', '').strip()
            salon_address = form.cleaned_data.get('salon_address', '').strip()
            provider_address = form.cleaned_data.get('provider_address', '').strip()
            service_types = form.cleaned_data.get('service_types', [])

            # --- Salon Owner ---
            if role == 'salon':
                if not salon_name or not salon_address:
                    messages.error(request, "Business name and address are required for your role.")
                    user.delete()
                    return redirect('register')

                Salon.objects.create(
                    owner=user,
                    name=salon_name,
                    address=salon_address,
                    approved=False
                )

            # --- Shop Owner ---
            elif role == 'shop':
                if not salon_name or not salon_address:
                    messages.error(request, "Shop name and address are required for your role.")
                    user.delete()
                    return redirect('register')

                # For shop owners, we can still create a salon object if needed
                Salon.objects.create(
                    owner=user,
                    name=salon_name,
                    address=salon_address,
                    approved=False
                )

            # --- Service Provider ---
            elif role == 'provider':
                if not provider_address:
                    messages.error(request, "Address is required for service providers.")
                    user.delete()
                    return redirect('register')

                # Create a virtual salon for the provider
                virtual_salon = Salon.objects.create(
                    owner=user,
                    name=f"{user.username}'s Services",
                    address=provider_address,
                    approved=False
                )

                # Create services linked to the virtual salon
                for stype in service_types:
                    Service.objects.create(
                        salon=virtual_salon,
                        provider=user,
                        name=stype.title(),
                        service_type=stype,
                        price=0,
                        duration_minutes=30
                    )

            # --- Regular User ---
            else:
                pass  # no business info needed

            messages.success(request, "Registration successful! Await admin approval.")
            return redirect('register')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserForm()

    context = {
        'form': form,
        'roles': CustomUser.ROLE_CHOICES,
    }
    return render(request, 'snow/partials/register.html', context)

def render_services_table():
    services = Service.objects.select_related('salon').all().order_by('-id')
    return render_to_string("snow/partials/service_table.html", {"services": services})

def render_products_list(request):
    products = Product.objects.all().order_by('-id')
    return render_to_string(
        "snow/partials/products_list.html",
        {"products": products, "form": ProductForm()},
        request=request  
    )


def render_salons_list():
    salons = Salon.objects.all().order_by('-created_at')
    return render_to_string("snow/partials/salons_list.html", {"salons": salons, "form": UserForm()})


# -----------------------
# Public Views
# -----------------------
def home(request):
    salons = Salon.objects.all()
    products = Product.objects.filter(featured=True).order_by('-id')
    context = {
        "salons": salons,
        "products": products,
        "service_types": Service.SERVICE_TYPES,
    }
    return render(request, "snow/partials/index.html", context)

def about(request):
    return render(request, "snow/partials/about.html")

def services(request):
    services = Service.objects.filter(is_visible=True).order_by('-id')
    grouped_services = {
        label: services.filter(service_type=key, featured=True)
        for key, label in Service.SERVICE_TYPES
    }
    return render(request, "snow/partials/services.html", {
        "grouped_services": grouped_services,
        "service_types": Service.SERVICE_TYPES,
    })

def contact(request):
    users = CustomUser.objects.filter(is_approved=True).exclude(role='admin')
    salons_data = []

    for user in users:
        if user.role in ['salon', 'provider', 'shop']:
            salon = Salon.objects.filter(owner=user, approved=True).first()
            if salon:
                salons_data.append({
                    'id': salon.id,
                    'name': salon.name,
                    'lat': salon.latitude or 0.3476,
                    'lng': salon.longitude or 32.5825,
                    'role': user.role
                })

    return render(request, 'snow/partials/contact.html', {
        'salons_json': json.dumps(salons_data, cls=DjangoJSONEncoder),
        'working_days': ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
    })

def salon_details(request, salon_id):
    salon = get_object_or_404(Salon, id=salon_id, approved=True)
    services = Service.objects.filter(salon=salon, is_visible=True)[:5]
    products = Product.objects.filter(owner=salon.owner)[:5]

    html = render_to_string('snow/partials/salon_details_popup.html', {
        'salon': salon,
        'services': services,
        'products': products
    }, request=request)

    print("HTML length:", len(html))
    print("Services count:", services.count())
    print("Products count:", products.count())

    return JsonResponse({'html': html})


def search_items(request):
    query = request.GET.get('query', '').strip()
    service_type = request.GET.get('service', '').strip()
    address = request.GET.get('address', '').strip()
    price_range = request.GET.get('price_range', '').strip()

    services = Service.objects.filter(featured=True)
    products = Product.objects.filter(featured=True)

    if query:
        services = services.filter(service_type__icontains=query)
        products = products.filter(name__icontains=query)
    elif service_type:
        services = services.filter(service_type__icontains=service_type)

    if address:
        services = services.filter(salon__address__icontains=address)
        products = products.filter(salon__address__icontains=address)

    if price_range:
        if price_range == 'low':
            services = services.filter(price__lt=30000)
            products = products.filter(price__lt=30000)
        elif price_range == 'medium':
            services = services.filter(price__gte=30000, price__lte=80000)
            products = products.filter(price__gte=30000, price__lte=80000)
        elif price_range == 'high':
            services = services.filter(price__gt=80000)
            products = products.filter(price__gt=80000)

    return render(request, 'snow/partials/search_results.html', {
        'services': services.distinct(),
        'products': products.distinct(),
        'query': query,
        'service_type': service_type,
        'address': address,
        'price_range': price_range,
    })


# -----------------------
# Booking Views
# -----------------------
@login_required
def book_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    salon = service.salon

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.user = request.user
            appointment.service = service
            appointment.salon = salon
            appointment.status = 'booked'
            appointment.save()
            return redirect('booking_success')
    else:
        form = AppointmentForm()

    return render(request, 'snow/partials/book_service.html', {'form': form, 'service': service})


# -----------------------
# Admin Auth & Dashboard
# -----------------------
def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            if not user.is_approved:
                messages.error(request, "Your account is not approved yet.")
            elif not user.is_active:
                messages.error(request, "Your account is inactive.")
            else:
                login(request, user)
                # Redirect based on role
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'salon':
                    return redirect('owner_dashboard')
                else:
                    return redirect('dashboard')  # regular users
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'snow/login.html')

@login_required
@user_passes_test(admin_required)
def admin_dashboard(request):
    context = {
        'pending_salons_count': Salon.objects.filter(approved=False).count(),
        'approved_salons_count': Salon.objects.filter(approved=True).count(),
       'total_users': CustomUser.objects.count(),
     'pending_appointments_count': Appointment.objects.filter(status='pending').count(),
    }
    return ajax_response(
        request,
        'snow/partials/dashboard_cards.html',
        context,
        fallback_template='snow/admin/admin_dashboard.html'
    )



# -----------------------
# Salon CRUD
# -----------------------
@login_required
@user_passes_test(admin_required)
def salons_list(request):
    if request.method == 'POST':
        salon_id = request.POST.get('id')
        form = UserForm(request.POST, instance=get_object_or_404(Salon, id=salon_id) if salon_id else None)
        if form.is_valid():
            salon = form.save(commit=False)
            salon.owner = request.user
            salon.approved = True
            salon.save()
            return JsonResponse({'html': render_salons_list()})
        return JsonResponse({'error': form.errors})
    return ajax_response(request, 'snow/partials/salons_list.html', {'salons': Salon.objects.all(), 'form': UserForm()})


@login_required
@user_passes_test(admin_required)
@require_POST
def approve_salon(request, salon_id):
    salon = get_object_or_404(Salon, id=salon_id)
    salon.approved = True
    salon.save()
    return JsonResponse({'success': True}) if request.headers.get('x-requested-with') == 'XMLHttpRequest' else redirect("salons_list")

@login_required
@user_passes_test(admin_required)
@require_POST
def reject_salon(request, salon_id):
    salon = get_object_or_404(Salon, id=salon_id)
    salon.delete()
    return JsonResponse({'success': True}) if request.headers.get('x-requested-with') == 'XMLHttpRequest' else redirect("salons_list")


# -----------------------
# Service CRUD
# -----------------------
@login_required
@user_passes_test(admin_required, login_url='login')
def services_list(request):
    return ajax_response(request, 'snow/partials/service.html', {'services': Service.objects.all(), 'form': ServiceForm()})

@login_required
@user_passes_test(admin_required, login_url='login')
def add_service(request):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True, "html": render_services_table()})
        return JsonResponse({"success": False, "error": form.errors})
    return render(request, "snow/partials/service.html", {"form": ServiceForm(), "services": Service.objects.all()})


@login_required
@user_passes_test(admin_required)
def edit_service(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "GET" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "id": service.id,
            "name": service.name,
            "price": str(service.price),
            "duration_minutes": service.duration_minutes,
            "service_type": service.service_type,
            "featured": service.featured,
            "salon": service.salon.id,
        })
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True, "html": render_services_table()})
        return JsonResponse({"success": False, "error": form.errors})

@login_required
@user_passes_test(admin_required)
def delete_service(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        service.delete()
        return JsonResponse({"success": True, "html": render_services_table()})
    return JsonResponse({"error": "Invalid request"})


# -----------------------
# Product CRUD
# -----------------------
@login_required
@user_passes_test(admin_required, login_url='login')
def products_list(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'html': render_products_list(request)})  
    return render(request, 'snow/partials/products_list.html', {'products': Product.objects.all(), 'form': ProductForm()})


@login_required
@user_passes_test(admin_required)  # or your admin check
def add_or_edit_product(request, id=None):
    # ---------- Handle AJAX GET (fetch product data for editing)
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if id:
            product = get_object_or_404(Product, id=id)
            data = {
                "id": product.id,
                "name": product.name,
                "price": str(product.price),
                "description": product.description,
                "featured": product.featured,
                "image": product.image.url if product.image else ''
            }
            return JsonResponse(data)
        return JsonResponse({"error": "No product found"}, status=400)

    # ---------- Handle AJAX POST (create or update)
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if id:
            product = get_object_or_404(Product, id=id)
            form = ProductForm(request.POST, request.FILES, instance=product)
        else:
            form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            # Render updated products table to send back
            products = Product.objects.all().order_by('-id')
            html = render_to_string('partials/product_table.html', {'products': products}, request=request)
            return JsonResponse({'success': True, 'html': html})
        else:
            return JsonResponse({'success': False, 'error': form.errors}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@user_passes_test(admin_required)
def delete_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        product.delete()
        return JsonResponse({'success': True, 'html': render_products_list(request)})  
    
    return JsonResponse({'error': 'Invalid request'})

# -----------------------
# Owner Views & Chat API
# -----------------------

@login_required
@user_passes_test(owner_required, login_url='login')
def owner_dashboard(request):
    user = request.user
    salons = Salon.objects.filter(owner=user, approved=True)

    # Aggregate data
    services = Service.objects.filter(salon__in=salons)
    products = Product.objects.filter(owner=user)
    appointments = Appointment.objects.filter(salon__in=salons)
    conversations = Conversation.objects.filter(salon__in=salons).select_related('user').order_by('-last_updated')

    page = request.GET.get('page', 'dashboard')  # Default page

    context = {
        'salons': salons,
        'services': services,
        'products': products,
        'appointments': appointments,
        'conversations': conversations,
        'service_form': ServiceForm(),
        'product_form': ProductForm(),
        'page': page
    }

    # Compute stats dynamically
    stats = {}
    if page == 'dashboard':
        stats = {
            'appointments_count': appointments.count(),
            'services_count': services.count(),
            'products_count': products.count(),
            'revenue': sum(a.service.price for a in appointments if a.service),
            'unread_messages': sum(c.messages.filter(read=False).exclude(sender=user).count() for c in conversations),
            'reviews_count': sum(s.reviews.count() for s in services) + sum(p.reviews.count() for p in products)
        }
        context['stats'] = stats
        template = 'snow/partials/salon_dashboard.html'
    elif page == 'services':
        template = 'snow/partials/service_table.html'
    elif page == 'products':
        template = 'snow/partials/products_list.html'
    elif page == 'appointments':
        template = 'snow/partials/appointments_list.html'
    else:
        template = 'snow/partials/salon_dashboard.html'

    # If AJAX request, render HTML snippet only
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string(template, context, request=request)
        return JsonResponse({'html': html})

    # Otherwise render full dashboard
    context['stats'] = stats
    return render(request, 'snow/partials/salon_dashboard.html', context)

@login_required
@user_passes_test(owner_required)

def owner_add_or_edit_service(request, id=None):
    user = request.user
    salon = Salon.objects.filter(owner=user).first()
    if not salon:
        return JsonResponse({"error": "You have no salon"}, status=400)

    if request.method == "GET":
        if id:
            service = get_object_or_404(Service, id=id, salon=salon)
            form = ServiceForm(instance=service)
        else:
            form = ServiceForm()
        
        html = render_to_string("snow/partials/service_form.html", {"form": form}, request=request)
        return JsonResponse({"html": html})  # <-- send HTML for modal

    elif request.method == "POST":
        if id:
            service = get_object_or_404(Service, id=id, salon=salon)
            form = ServiceForm(request.POST, request.FILES, instance=service)
        else:
            form = ServiceForm(request.POST, request.FILES)

        if form.is_valid():
            new_service = form.save(commit=False)
            new_service.salon = salon
            new_service.save()
            services = Service.objects.filter(salon=salon).order_by('-id')
            html = render_to_string("snow/partials/service_table.html", {"services": services}, request=request)
            return JsonResponse({"success": True, "html": html})
        else:
            # Return the form with errors as HTML
            html = render_to_string("snow/partials/service_form.html", {"form": form}, request=request)
            return JsonResponse({"success": False, "html": html}, status=400)

@login_required
@user_passes_test(owner_required)
def owner_edit_service(request, pk):
    service = get_object_or_404(Service, pk=pk)

    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            html = render_services_table()
            return JsonResponse({'success': True, 'html': html})
        
        # Return form with errors
        html = render_to_string('snow/partials/service_form.html', {'form': form}, request=request)
        return JsonResponse({'success': False, 'html': html})

    else:
        # GET request
        form = ServiceForm(instance=service)
        html = render_to_string("snow/partials/service_form.html", {'form': form}, request=request)

        # AJAX response
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({'html': html})

        # Normal fallback page (only for debugging)
        return render(request, "snow/partials/service_form.html", {'form': form})

@login_required
@user_passes_test(owner_required)
@require_POST
def owner_delete_service(request, id):
    user = request.user
    salon = Salon.objects.filter(owner=user).first()
    service = get_object_or_404(Service, id=id, salon=salon)

    service.delete()

    # Optionally, return updated services list
    html = render_to_string("snow/partials/service_table.html", {
        "services": Service.objects.filter(salon=salon)
    }, request=request)

    return JsonResponse({"success": True, "html": html})

@login_required
def edit_profile(request):
    user = request.user
    salon = Salon.objects.filter(owner=user).first()  # Get related salon if any

    # Pre-fill extra fields for initial form data
    initial_data = {
        'salon_name': salon.name if salon else '',
        'salon_address': salon.address if salon else '',
    }

    # If user is a provider, pre-fill provider_address and services
    if user.role == 'provider' and salon:
        initial_data['provider_address'] = salon.address
        initial_data['service_types'] = [s.service_type for s in salon.services.all()]

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('owner_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserEditForm(instance=user, initial=initial_data)

    context = {
        'form': form,
        'salon': salon
    }

    return render(request, 'snow/partials/edit_profile.html', context)


@login_required
@require_GET
def api_conversations(request, salon_id):
    salon = get_object_or_404(Salon, id=salon_id)
    if salon.owner != request.user:
        return JsonResponse({'error': 'forbidden'}, status=403)
    convs = Conversation.objects.filter(salon=salon).select_related('user').order_by('-last_updated')
    data = [{
        'id': c.id,
        'user_id': c.user.id,
        'username': c.user.username,
        'preview': (c.messages.last().content[:60] if c.messages.last() else ''),
        'last_updated': c.last_updated.isoformat(),
        'unread': c.messages.filter(read=False).exclude(sender=request.user).count()
    } for c in convs]
    return JsonResponse({'conversations': data})

@login_required
@require_GET
def api_messages(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id)
    if conv.salon.owner != request.user and conv.user != request.user:
        return JsonResponse({'error': 'forbidden'}, status=403)
    msgs = conv.messages.select_related('sender').order_by('created_at')
    conv.messages.filter(read=False).exclude(sender=request.user).update(read=True)
    return JsonResponse({'messages': [{
        'id': m.id,
        'sender_id': m.sender.id,
        'sender_username': m.sender.username,
        'content': m.content,
        'created_at': m.created_at.isoformat(),
        'read': m.read,
    } for m in msgs]})

@login_required
@require_POST
def api_send_message(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id)
    if conv.salon.owner != request.user and conv.user != request.user:
        return JsonResponse({'error': 'forbidden'}, status=403)
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'empty'}, status=400)
    msg = Message.objects.create(conversation=conv, sender=request.user, content=content)
    conv.last_updated = msg.created_at
    conv.save()
    html = render_to_string('snow/owner/_message_item.html', {'message': msg, 'me': request.user})
    return JsonResponse({
        'success': True,
        'message': {'id': msg.id, 'content': msg.content, 'sender': msg.sender.username, 'created_at': msg.created_at.isoformat()},
        'html': html
    })

def filter_services_by_type(request):
    service_type = request.GET.get('service')
    services = Service.objects.filter(is_visible=True)
    if service_type:
        services = services.filter(service_type=service_type)
    services = services.order_by('-id')
    html = render_to_string('snow/partials/service_cards.html', {'services': services}, request=request)
    return JsonResponse({'html': html})

@login_required
@user_passes_test(admin_required)
def users_list(request):
    role_filter = request.GET.get('role', None)
    if role_filter:
        users = CustomUser.objects.filter(role=role_filter)
    else:
        users = CustomUser.objects.all()

    # Check if request is AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string(
            'snow/partials/users_list.html',
            {'users': users, 'roles': CustomUser.ROLE_CHOICES, 'form': UserForm()},
            request=request
        )
        return JsonResponse({'html': html})

    # fallback full page render
    return render(request, 'snow/admin/users.html', {
        'users': users,
        'roles': CustomUser.ROLE_CHOICES,
        'form': UserForm()
    })

@login_required
@user_passes_test(admin_required)
def edit_user(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    salon = getattr(user, 'salon', None)

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            role = form.cleaned_data.get('role')
            salon_name = form.cleaned_data.get('salon_name', '').strip()
            salon_address = form.cleaned_data.get('salon_address', '').strip()
            provider_address = form.cleaned_data.get('provider_address', '').strip()
            service_types = form.cleaned_data.get('service_types', [])

            # --- Salon / Shop Owner ---
            if role in ['salon', 'shop']:
                if not salon_name or not salon_address:
                    messages.error(request, "Business name and address are required.")
                    return redirect('edit_user', pk=pk)

                if salon:
                    salon.name = salon_name
                    salon.address = salon_address
                    salon.save()
                else:
                    Salon.objects.create(
                        owner=user,
                        name=salon_name,
                        address=salon_address,
                        approved=False
                    )

            # --- Service Provider ---
            elif role == 'provider':
                if not provider_address:
                    messages.error(request, "Address is required for service providers.")
                    return redirect('edit_user', pk=pk)

                if salon:
                    salon.address = provider_address
                    salon.save()
                    salon.services.all().delete()
                else:
                    salon = Salon.objects.create(
                        owner=user,
                        name=f"{user.username}'s Services",
                        address=provider_address,
                        approved=False
                    )

                # Update services
                for stype in service_types:
                    Service.objects.create(
                        salon=salon,
                        name=stype.title(),
                        service_type=stype,
                        price=0,
                        duration_minutes=30
                    )

            # --- Regular User ---
            else:
                if salon:
                    salon.delete()

            user.save()
            messages.success(request, "User updated successfully!")
            return redirect('users_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = UserForm(instance=user)

    context = {
        'form': form,
        'user_obj': user,
        'salon': salon,
        'roles': CustomUser.ROLE_CHOICES,
    }
    return render(request, 'snow/partials/edit_user.html', context)



@login_required
@user_passes_test(admin_required)
def delete_user(request, id):
    user = get_object_or_404(CustomUser, id=id)
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user.delete()
        html = render_to_string(
            'snow/partials/users_table_body.html',
            {'users': CustomUser.objects.all()},
            request=request
        )
        return JsonResponse({'success': True, 'html': html})

    return JsonResponse({'success': False, 'error': 'Invalid request'})
@login_required
@user_passes_test(admin_required)
def toggle_user_status(request, id):
    user = get_object_or_404(CustomUser, id=id)
    user.is_approved = not user.is_approved
    user.save()

    html = render_to_string(
        'snow/partials/users_table_body.html',
        {'users': CustomUser.objects.all()},
        request=request
    )
    return JsonResponse({'success': True, 'html': html})

@login_required
@user_passes_test(admin_required)
def appointments_list(request):
    appointments = Appointment.objects.select_related('service', 'salon', 'user').all().order_by('-date_time')
    return ajax_response(request, "snow/partials/appointments_list.html", {"appointments": appointments})


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, "snow/partials/product_detail.html", {"product": product})


@login_required
@user_passes_test(owner_required)
def owner_add_or_edit_product(request, pk=None):
    user = request.user
    salon = Salon.objects.filter(owner=user).first()
    if not salon:
        return JsonResponse({"error": "You have no salon"}, status=400)

    if pk:
        product = get_object_or_404(Product, pk=pk, owner=user)
    else:
        product = None

    # GET: return form HTML
    if request.method == "GET" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        form = ProductForm(instance=product)
        html = render_to_string("snow/partials/product_form.html", {"form": form}, request=request)
        return JsonResponse({"html": html})

    # POST: handle create/update
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            prod = form.save(commit=False)
            prod.owner = user
            prod.save()
            products = Product.objects.filter(owner=user).order_by("-id")
            html = render_to_string("snow/partials/products_list.html", {"products": products, "form": ProductForm()}, request=request)
            return JsonResponse({"success": True, "html": html})
        # return form with errors
        html = render_to_string("snow/partials/product_form.html", {"form": form}, request=request)
        return JsonResponse({"success": False, "html": html}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)




@login_required
@require_POST
def owner_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()

    html = render_to_string(
        'snow/partials/products_list.html',
        {'products': Product.objects.filter(salon=request.user.salon)}
    )
    return JsonResponse({'success': True, 'html': html})