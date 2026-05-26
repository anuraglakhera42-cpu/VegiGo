from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count
from django.utils import timezone
from vgapp.models import (
    Category, Product, ProductImage, GuestUser, Cart, CartItem,
    Order, OrderItem, PaymentTransaction, UserProfile
)


# ==================== CATEGORY ADMIN ====================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count']
    search_fields = ['name']
    
    def product_count(self, obj):
        count = obj.product_set.count()
        return format_html(
            '<span style="background-color: #417690; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            count
        )
    product_count.short_description = 'Products'


# ==================== PRODUCT ADMIN ====================



class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'price_display', 'stock_status',
        'is_active', 'created_at'
    ]

    list_filter = [
        'is_active', 'category', 'created_at'
    ]

    search_fields = ['name', 'description']
    inlines = [ProductImageInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'discount_price', 'stock')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def price_display(self, obj):
        if obj.discount_price:
            return format_html(
                '<span style="text-decoration: line-through;">₹{}</span> '
                '<strong style="color: green;">₹{}</strong> '
                '<span style="color: red;">({}% off)</span>',
                obj.price,
                obj.discount_price,
                obj.discount_percentage
            )
        return f'₹{obj.price}'

    price_display.short_description = 'Price'

    def stock_status(self, obj):
        if obj.stock == 0:
            color = 'red'
            status = 'Out of Stock'
        elif obj.stock < 10:
            color = 'orange'
            status = f'Low ({obj.stock})'
        else:
            color = 'green'
            status = f'In Stock ({obj.stock})'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )

    stock_status.short_description = 'Stock Status'


# ==================== GUEST USER ADMIN ====================

@admin.register(GuestUser)
class GuestUserAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'email', 'phone', 'order_count', 'created_at', 'last_activity'
    ]
    
    list_filter = ['created_at', 'last_activity']
    search_fields = ['email', 'phone', 'name', 'guest_id']
    readonly_fields = ['guest_id', 'created_at', 'last_activity']
    
    fieldsets = (
        ('Identification', {
            'fields': ('guest_id', 'created_at', 'last_activity')
        }),
        ('Contact Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Address', {
            'fields': (
                'street_address', 'city', 'state', 'pincode'
            )
        }),
    )
    
    def order_count(self, obj):
        count = obj.orders.count()
        return format_html(
            '<span style="background-color: #417690; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            count
        )
    order_count.short_description = 'Orders'


# ==================== CART ADMIN ====================

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'added_at', 'updated_at']
    can_delete = False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['cart_owner', 'item_count', 'cart_total', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'guest__email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CartItemInline]
    
    def cart_owner(self, obj):
        if obj.user:
            return obj.user.email
        return f"Guest: {obj.guest.name}"
    cart_owner.short_description = 'Owner'
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'
    
    def cart_total(self, obj):
        return f"₹{obj.get_cart_total}"
    cart_total.short_description = 'Total'


# ==================== ORDER ADMIN ====================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'quantity', 'price', 'get_cost']
    can_delete = False
    
    def get_cost(self, obj):
        return f"₹{obj.get_cost or 0}"
    get_cost.short_description = 'Cost'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_id', 'customer_name', 'total_amount_display',
        'order_status_badge', 'payment_status_badge', 'created_at'
    ]
    
    list_filter = [
        'order_status', 'payment_status', 'payment_method', 'created_at'
    ]
    
    search_fields = [
        'order_id', 'customer_email', 'customer_phone', 'customer_name'
    ]
    
    readonly_fields = [
        'order_id', 'created_at', 'updated_at', 'shipped_at', 'delivered_at'
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'user', 'guest', 'created_at', 'updated_at')
        }),
        ('Customer Details', {
            'fields': (
                'customer_name', 'customer_email', 'customer_phone'
            )
        }),
        ('Shipping Address', {
            'fields': (
                'shipping_address', 'shipping_city',
                'shipping_state', 'shipping_pincode'
            )
        }),
        ('Order Details', {
            'fields': (
                'subtotal', 'tax', 'shipping_cost', 'discount', 'total_amount'
            )
        }),
        ('Status & Payment', {
            'fields': (
                'order_status', 'payment_status', 'payment_method', 'notes'
            )
        }),
        ('Tracking', {
            'fields': (
                'tracking_number', 'shipped_at', 'delivered_at'
            )
        }),
    )
    
    inlines = [OrderItemInline]
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered']
    
    def total_amount_display(self, obj):
        return f"₹{obj.total_amount}"
    total_amount_display.short_description = 'Amount'
    
    def order_status_badge(self, obj):
        colors = {
            'pending': '#FFA500',
            'processing': '#417690',
            'shipped': '#1E90FF',
            'delivered': '#228B22',
            'cancelled': '#DC143C',
            'refunded': '#9370DB'
        }
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.order_status, '#999'),
            obj.get_order_status_display()
        )
    order_status_badge.short_description = 'Status'
    
    def payment_status_badge(self, obj):
        colors = {
            'pending': '#FFA500',
            'completed': '#228B22',
            'failed': '#DC143C',
            'refunded': '#9370DB'
        }
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.payment_status, '#999'),
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment'
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(order_status='processing')
        self.message_user(request, f'{updated} orders marked as processing')
    mark_as_processing.short_description = 'Mark selected as Processing'
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(
            order_status='shipped',
            shipped_at=timezone.now()
        )
        self.message_user(request, f'{updated} orders marked as shipped')
    mark_as_shipped.short_description = 'Mark selected as Shipped'
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(
            order_status='delivered',
            delivered_at=timezone.now()
        )
        self.message_user(request, f'{updated} orders marked as delivered')
    mark_as_delivered.short_description = 'Mark selected as Delivered'


# ==================== PAYMENT TRANSACTION ADMIN ====================

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id', 'order', 'amount_display',
        'payment_method', 'status_badge', 'created_at'
    ]
    
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'order__order_id']
    readonly_fields = [
        'transaction_id', 'order', 'amount', 'created_at', 'updated_at',
        'response_data'
    ]
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('transaction_id', 'order', 'created_at', 'updated_at')
        }),
        ('Payment Details', {
            'fields': (
                'amount', 'payment_method', 'status'
            )
        }),
        ('Gateway Response', {
            'fields': ('response_data',),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        return f"₹{obj.amount}"
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FFA500',
            'success': '#228B22',
            'failed': '#DC143C'
        }
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#999'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ==================== USER PROFILE ADMIN ====================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Contact Information', {
            'fields': ('phone',)
        }),
        ('Default Address', {
            'fields': (
                'default_address', 'default_city',
                'default_state', 'default_pincode'
            )
        }),
        ('Preferences', {
            'fields': ('email_notifications', 'newsletter')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


# ==================== CUSTOM ADMIN SITE ====================

admin.site.site_header = "VegiGo Admin Dashboard"
admin.site.site_title = "VegiGo"
admin.site.index_title = "Welcome to VegiGo Admin"
