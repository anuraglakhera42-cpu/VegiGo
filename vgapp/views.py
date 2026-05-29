"""
VegiGo - Views file
Saare views yahan hain - function based, simple aur easy to understand
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.db import transaction
from django.conf import settings

from vgapp.models import (
    Product, Category, Cart, CartItem, Order, OrderItem, GuestUser, UserProfile
)
from vgapp.forms import (
    SignUpForm, LoginForm, GuestCheckoutForm, UserCheckoutForm,
    UserProfileForm, CustomPasswordResetForm, CustomSetPasswordForm
)

import uuid
import decimal


# ==================== HELPER FUNCTIONS ====================

def get_or_create_cart(request):
    """Cart nikalo ya banao - logged in user ya guest dono ke liye"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        return cart
    else:
        # Guest cart - session mein store karo
        guest_id = request.session.get('guest_id')
        if not guest_id:
            guest_id = str(uuid.uuid4())
            request.session['guest_id'] = guest_id

        guest, _ = GuestUser.objects.get_or_create(guest_id=guest_id)
        cart, _ = Cart.objects.get_or_create(guest=guest)
        return cart


def get_cart_totals(cart):
    """Cart ka total calculate karo - subtotal, tax, shipping, grand total"""
    cart_items = cart.items.select_related('product').all()
    subtotal = sum(item.get_cost for item in cart_items)
    free_shipping_threshold = decimal.Decimal(str(settings.FREE_SHIPPING_THRESHOLD))
    standard_shipping_cost = decimal.Decimal(str(settings.STANDARD_SHIPPING_COST))
    free_shipping_remaining = max(
        free_shipping_threshold - subtotal,
        decimal.Decimal('0.00'),
    )
    shipping = standard_shipping_cost if free_shipping_remaining else decimal.Decimal('0.00')
    tax = (subtotal * decimal.Decimal('0.18')).quantize(decimal.Decimal('0.01'))
    total = subtotal + shipping + tax

    return {
        'subtotal': subtotal,
        'shipping': shipping,
        'tax': tax,
        'total': total,
        'free_shipping_threshold': free_shipping_threshold,
        'free_shipping_remaining': free_shipping_remaining,
        'has_free_shipping': free_shipping_remaining == 0,
    }


def parse_quantity(value, default=1, min_value=1):
    """Return a safe positive integer quantity from user input."""
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return default
    return max(quantity, min_value)


# ==================== HOME PAGE ====================

def home(request):
    """Homepage - featured products dikhao"""
    products = Product.objects.filter(is_active=True).select_related('category')[:6]
    return render(request, 'index.html', {
        'products': products,
        'active_page': 'home'
    })


# ==================== PRODUCTS PAGE ====================

def product_view(request):
    """Saare products dikhao - category filter ke saath"""
    categories = Category.objects.all()
    selected_category = request.GET.get('category')
    search_query = request.GET.get('search', '').strip()

    products = Product.objects.filter(is_active=True).select_related('category')

    if selected_category:
        products = products.filter(category__id=selected_category)

    if search_query:
        products = products.filter(name__icontains=search_query)

    return render(request, 'products.html', {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
        'active_page': 'products',
    })


# ==================== PRODUCT DETAIL ====================

def product_detail(request, pk):
    """Ek product ki poori detail"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(pk=pk)[:4]

    return render(request, 'product_detail.html', {
        'product': product,
        'related_products': related_products,
    })


# ==================== CART - ADD PRODUCT ====================

@require_POST
def add_to_cart(request, product_id):
    """
    Product ko cart mein add karo.
    AJAX request pe JSON return karta hai,
    Normal request pe cart page pe redirect karta hai.
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    quantity = parse_quantity(request.POST.get('quantity', 1))

    # Stock check
    if quantity > product.stock:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Itna stock available nahi hai!'})
        messages.error(request, 'Itna stock available nahi hai!')
        return redirect('products')

    cart = get_or_create_cart(request)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )

    if not created:
        if cart_item.quantity + quantity > product.stock:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f"Only {product.stock} units available in stock.",
                }, status=400)
            messages.error(request, f"Only {product.stock} units available in stock.")
            return redirect('cart')

        cart_item.quantity += quantity
        cart_item.save()

    # Cart count update karo
    cart_count = cart.items.count()

    # AJAX request ke liye JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f"'{product.name}' cart mein add ho gaya!",
            'cart_count': cart_count,
            'item_quantity': cart_item.quantity,
            'product_id': product_id,
        })

    # Normal request ke liye redirect
    messages.success(request, f"'{product.name}' cart mein add ho gaya!")
    return redirect('cart')


# ==================== CART - VIEW ====================

def view_cart(request):
    """Cart page - saare items dikhao"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').all()
    totals = get_cart_totals(cart)
    cart_count = cart_items.count()

    return render(request, 'cart/cart.html', {
        'cart_items': cart_items,
        'totals': totals,
        'cart_count': cart_count,
        'active_page': 'cart',
    })


# ==================== CART - UPDATE ====================

@require_POST
def update_cart(request, product_id):
    """Cart item ki quantity update ya remove karo"""
    cart = get_or_create_cart(request)
    product = get_object_or_404(Product, id=product_id)
    action = request.POST.get('action', 'update')

    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)

        if action == 'remove':
            cart_item.delete()
            messages.success(request, f"'{product.name}' cart se remove ho gaya.")

        elif action == 'update':
            new_qty = parse_quantity(request.POST.get('quantity', 1), min_value=0)
            if new_qty < 1:
                cart_item.delete()
            else:
                cart_item.quantity = min(new_qty, product.stock)
                cart_item.save()

        # AJAX support
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart = get_or_create_cart(request)
            totals = get_cart_totals(cart)
            return JsonResponse({
                'success': True,
                'cart_count': cart.items.count(),
                'subtotal': str(totals['subtotal']),
                'total': str(totals['total']),
            })

    except CartItem.DoesNotExist:
        pass

    return redirect('cart')


# ==================== CART - CLEAR ====================

@require_POST
def clear_cart(request):
    """Poora cart khaali karo"""
    cart = get_or_create_cart(request)
    cart.items.all().delete()
    messages.success(request, 'Cart saaf ho gaya!')
    return redirect('cart')


# ==================== CART COUNT API ====================

def get_cart_count(request):
    """Navbar badge ke liye cart count return karo (JSON)"""
    try:
        cart = get_or_create_cart(request)
        count = cart.items.count()
    except Exception:
        count = 0
    return JsonResponse({'count': count})


# ==================== CHECKOUT ====================

def checkout(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').all()

    if not cart_items:
        messages.warning(request, 'Cart khaali hai! Pehle kuch products add karo.')
        return redirect('products')

    totals = get_cart_totals(cart)

    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)

        initial = {
            'full_name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'phone': profile.phone,
            'street_address': profile.default_address,
            'city': profile.default_city,
            'state': profile.default_state,
            'pincode': profile.default_pincode,
            'payment_method': 'cod',
        }

        form = UserCheckoutForm(initial=initial)
    else:
        form = GuestCheckoutForm(initial={'payment_method': 'cod'})

    return render(request, 'checkout/checkout.html', {
        'cart_items': cart_items,
        'totals': totals,
        'form': form,
    })


@require_POST
def process_checkout(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').all()

    if not cart_items:
        messages.error(request, 'Cart khaali hai.')
        return redirect('products')

    totals = get_cart_totals(cart)

    if not request.POST.get('no_cancel_ack'):
        messages.error(request, 'Please confirm that this order cannot be cancelled after checkout.')
        return redirect('checkout')

    if request.user.is_authenticated:
        form = UserCheckoutForm(request.POST)
    else:
        form = GuestCheckoutForm(request.POST)

    if form.is_valid():
        data = form.cleaned_data

        guest = None

        if request.user.is_authenticated:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            profile.phone = data['phone']
            profile.default_address = data['street_address']
            profile.default_city = data['city']
            profile.default_state = data['state']
            profile.default_pincode = data['pincode']
            profile.save()
        else:
            guest_id = request.session.get('guest_id')

            if not guest_id:
                guest_id = str(uuid.uuid4())
                request.session['guest_id'] = guest_id

            guest, created = GuestUser.objects.get_or_create(guest_id=guest_id)
            guest.name = data['full_name']
            guest.email = data['email']
            guest.phone = data['phone']
            guest.street_address = data['street_address']
            guest.city = data['city']
            guest.state = data['state']
            guest.pincode = data['pincode']
            guest.save()

        try:
            with transaction.atomic():
                locked_items = cart.items.select_related('product').select_for_update()
                for item in locked_items:
                    product = Product.objects.select_for_update().get(pk=item.product_id)
                    if item.quantity > product.stock:
                        raise ValueError(f"Only {product.stock} units of {product.name} are available.")

                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    guest=guest,
                    customer_name=data['full_name'],
                    customer_email=data['email'],
                    customer_phone=data['phone'],
                    shipping_address=data['street_address'],
                    shipping_city=data['city'],
                    shipping_state=data['state'],
                    shipping_pincode=data['pincode'],
                    payment_method=data['payment_method'],
                    subtotal=totals['subtotal'],
                    tax=totals['tax'],
                    shipping_cost=totals['shipping'],
                    total_amount=totals['total'],
                )

                for item in locked_items:
                    product = item.product
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        quantity=item.quantity,
                        price=product.get_price,
                    )
                    product.stock -= item.quantity
                    product.save(update_fields=['stock'])

                cart.items.all().delete()
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('cart')

        messages.success(request, 'Order placed successfully!')
        return redirect('order_success', order_id=order.id)

    messages.error(request, 'Please check the checkout form errors.')

    return render(request, 'checkout/checkout.html', {
        'cart_items': cart_items,
        'totals': totals,
        'form': form,
    })


# ==================== ORDER SUCCESS ====================

def order_success(request, order_id):
    """Order success page"""
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'checkout/order_success.html', {'order': order})


# ==================== ORDER DETAIL ====================

def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'checkout/order_detail.html', {'order': order})


# ==================== USER PROFILE ====================

@login_required
def profile_view(request):
    """User profile page"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile update ho gaya!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'user/profile.html', {'form': form})


# ==================== ORDER HISTORY ====================

@login_required
def order_history(request):
    """User ke saare orders"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user/order_history.html', {'orders': orders})


# ==================== AUTH VIEWS ====================

def signup_view(request):
    """Signup page"""
    if request.user.is_authenticated:
        return redirect('home')

    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome to VegiGo, {user.first_name}!')
        return redirect('home')

    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    """Login page"""
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']

        from django.contrib.auth.models import User
        try:
            username = User.objects.get(email__iexact=email).username
            user = authenticate(request, username=username, password=password)
        except User.DoesNotExist:
            user = None

        if user:
            login(request, user)
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Email ya password galat hai.')

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """Logout"""
    logout(request)
    messages.success(request, 'Successfully logout ho gaye!')
    return redirect('home')


# ==================== PASSWORD RESET ====================

class CustomPasswordResetView(PasswordResetView):
    template_name = 'auth/password_reset.html'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('password_reset_done')
    email_template_name = 'auth/password_reset_email.html'
    subject_template_name = 'auth/password_reset_subject.txt'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'auth/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('password_reset_complete')
