from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from .models import User, Product, Order, Category, Review
from .forms import AdminProductForm

# RBAC helper
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'role', '') == 'Admin')

admin_required = user_passes_test(is_admin, login_url='/admin/login/')

def admin_login(request):
    if request.user.is_authenticated and is_admin(request.user):
        return redirect('admin_dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
            
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if is_admin(user):
                login(request, user)
                return redirect(request.GET.get('next', 'admin_dashboard'))
            else:
                messages.error(request, "You do not have permission to access the admin portal.")
        else:
            messages.error(request, "Invalid username or password.")
            
    return render(request, 'admin/login.html')

@admin_required
def dashboard(request):
    # Analytics data
    total_users = User.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status='delivered').aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    recent_orders = Order.objects.order_by('-created_at')[:5]
    recent_users = User.objects.order_by('-created_at')[:5]

    context = {
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'now': timezone.now(),
    }
    return render(request, 'admin/dashboard.html', context)

@admin_required
def users_list(request):
    search_query = request.GET.get('search', '')
    if search_query:
        users = User.objects.filter(username__icontains=search_query) | User.objects.filter(email__icontains=search_query)
    else:
        users = User.objects.all().order_by('-date_joined')
    
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'users': page_obj, 'search_query': search_query, 'page_obj': page_obj}
    return render(request, 'admin/users.html', context)

@admin_required
def user_toggle_active(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user.is_superuser and user == request.user:
            messages.error(request, "You cannot block yourself.")
        else:
            user.is_active = not user.is_active
            user.save()
            status = 'unblocked' if user.is_active else 'blocked'
            messages.success(request, f"User {user.username} successfully {status}.")
    return redirect('admin_users')

@admin_required
def products_list(request):
    search_query = request.GET.get('search', '')
    if search_query:
        products = Product.objects.filter(name__icontains=search_query) | Product.objects.filter(category__name__icontains=search_query)
    else:
        products = Product.objects.all().order_by('-created_at')
        
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
        
    context = {'products': page_obj, 'search_query': search_query, 'page_obj': page_obj}
    return render(request, 'admin/products.html', context)

@admin_required
def product_delete(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        product.delete()
        messages.success(request, f"Product {product.name} deleted successfully.")
    return redirect('admin_products')

@admin_required
def product_create(request):
    if request.method == 'POST':
        form = AdminProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product {product.name} created successfully.")
            return redirect('admin_products')
        else:
            messages.error(request, "Failed to create product. Please check the form for validation errors.")
    else:
        form = AdminProductForm()
    return render(request, 'admin/product_form.html', {'form': form, 'title': 'Add New Product'})

@admin_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = AdminProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product {product.name} updated successfully.")
            return redirect('admin_products')
        else:
            messages.error(request, "Failed to update product. Please check the form for validation errors.")
    else:
        form = AdminProductForm(instance=product)
    return render(request, 'admin/product_form.html', {'form': form, 'product': product, 'title': 'Edit Product'})

@admin_required
def orders_list(request):
    search_query = request.GET.get('search', '')
    if search_query:
        orders = Order.objects.filter(order_number__icontains=search_query)
    else:
        orders = Order.objects.all().order_by('-created_at')
        
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
        
    context = {'orders': page_obj, 'search_query': search_query, 'page_obj': page_obj}
    return render(request, 'admin/orders.html', context)

@admin_required
def order_update_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, f"Order {order.order_number} status updated to {new_status}.")
        else:
            messages.error(request, "Invalid status.")
    return redirect('admin_orders')

@admin_required
def categories_list(request):
    categories = Category.objects.all().order_by('name')
    paginator = Paginator(categories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'categories': page_obj, 'page_obj': page_obj}
    return render(request, 'admin/categories.html', context)

@admin_required
def category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            Category.objects.create(name=name, description=description)
            messages.success(request, f"Category {name} created successfully.")
        else:
            messages.error(request, "Name is required.")
    return redirect('admin_categories')

@admin_required
def category_delete(request, category_id):
    if request.method == 'POST':
        category = get_object_or_404(Category, id=category_id)
        category.delete()
        messages.success(request, f"Category {category.name} deleted successfully.")
    return redirect('admin_categories')

@admin_required
def general_settings(request):
    # Placeholder for settings until models are added
    return render(request, 'admin/settings.html')
