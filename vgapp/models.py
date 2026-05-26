
import uuid
from django.db import models
from django.contrib.auth.models import User


# ==================== CATEGORY ====================

class Category(models.Model):
    """Product categories - Vegetables, Fruits, Dairy, etc."""

    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


# ==================== PRODUCT ====================

class Product(models.Model):

    name          = models.CharField(max_length=100)
    category      = models.ForeignKey(Category, on_delete=models.CASCADE)
    description   = models.TextField()
    price         = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image         = models.ImageField(upload_to='product_images/')
    stock         = models.IntegerField(default=0)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def get_price(self):
        """Discount price hai toh wo return karo, warna normal price."""
        return self.discount_price if self.discount_price else self.price

    @property
    def is_in_stock(self):
        """Stock available hai ya nahi."""
        return self.stock > 0

    @property
    def discount_percentage(self):
        """Discount kitne % ka hai."""
        if self.discount_price and self.price > 0:
            discount = ((self.price - self.discount_price) / self.price) * 100
            return round(discount)
        return 0


# ==================== PRODUCT IMAGE (Gallery) ====================

class ProductImage(models.Model):
    """Product ke extra images - detail page carousel ke liye."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    image   = models.ImageField(upload_to='product_gallery/')

    def __str__(self):
        return f"Image for {self.product.name}"


# ==================== GUEST USER ====================

class GuestUser(models.Model):
    """
    Bina account banaye order karne wale customers.
    Session ID se identify hote hain.
    """

    guest_id      = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    name          = models.CharField(max_length=200, blank=True)
    email         = models.EmailField(blank=True)
    phone         = models.CharField(max_length=15, blank=True)
    street_address = models.CharField(max_length=255, blank=True)
    city          = models.CharField(max_length=100, blank=True)
    state         = models.CharField(max_length=100, blank=True)
    pincode       = models.CharField(max_length=10, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or self.email or f"Guest {self.guest_id[:8]}"


# ==================== CART ====================

class Cart(models.Model):
    """
    User ya guest ka cart.
    Ek waqt mein ya toh user hoga ya guest - dono nahi.
    """

    user       = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    guest      = models.OneToOneField(GuestUser, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.email}"
        return f"Guest Cart - {self.guest}"

    @property
    def get_cart_total(self):
        """Cart ka total price calculate karo."""
        return sum(item.get_cost for item in self.items.all())


# ==================== CART ITEM ====================

class CartItem(models.Model):
    """Cart mein ek product ki entry."""

    cart       = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product    = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity   = models.IntegerField(default=1)
    added_at   = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def get_cost(self):
        """Is item ka total cost."""
        return self.product.get_price * self.quantity


# ==================== ORDER ====================

class Order(models.Model):
    """Customer ka ek placed order."""

    # Order Status choices
    ORDER_STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('processing', 'Processing'),
        ('shipped',    'Shipped'),
        ('delivered',  'Delivered'),
        ('cancelled',  'Cancelled'),
        ('refunded',   'Refunded'),
    ]

    # Payment Status choices
    PAYMENT_STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]

    # Payment Method choices
    PAYMENT_METHOD_CHOICES = [
        ('cod',  'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
        ('upi',  'UPI'),
    ]

    # Order identification
    order_id   = models.CharField(max_length=20, unique=True, blank=True)

    # Linked to user or guest
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    guest      = models.ForeignKey(GuestUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')

    # Customer details (order ke waqt ka snapshot)
    customer_name  = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=15)

    # Shipping address
    shipping_address = models.CharField(max_length=255)
    shipping_city    = models.CharField(max_length=100)
    shipping_state   = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=10)

    # Amount breakdown
    subtotal      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax           = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount  = models.DecimalField(max_digits=10, decimal_places=2)

    # Status fields
    order_status   = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')

    # Extra info
    notes           = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)

    # Timestamps
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    shipped_at   = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_id} - {self.customer_name}"

    def save(self, *args, **kwargs):
        """Order ID auto-generate karo agar nahi hai."""
        if not self.order_id:
            # VGO + 6 random digits
            self.order_id = 'VGO' + str(uuid.uuid4().int)[:6].upper()
        super().save(*args, **kwargs)


# ==================== ORDER ITEM ====================

class OrderItem(models.Model):
    """Order mein ek product ki entry."""

    order        = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product      = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)   # Product ka naam snapshot (agar product delete ho)
    quantity     = models.IntegerField(default=1)
    price        = models.DecimalField(max_digits=10, decimal_places=2)  # Order ke waqt ka price

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

    @property
    def get_cost(self):
        """Is item ka total cost."""
        return self.price * self.quantity


# ==================== PAYMENT TRANSACTION ====================

class PaymentTransaction(models.Model):
    """Payment gateway ka transaction record."""

    PAYMENT_METHOD_CHOICES = [
        ('cod',  'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
        ('upi',  'UPI'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed',  'Failed'),
    ]

    transaction_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    order          = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions')
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    response_data  = models.JSONField(default=dict, blank=True)  # Gateway ka raw response
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transaction {self.transaction_id[:8]} - {self.order.order_id}"


# ==================== USER PROFILE ====================

class UserProfile(models.Model):
    """
    Django ke default User model ka extension.
    Extra info store karta hai jaise phone, default address, preferences.
    """

    user              = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    phone             = models.CharField(max_length=15, blank=True)
    default_address   = models.CharField(max_length=255, blank=True)
    default_city      = models.CharField(max_length=100, blank=True)
    default_state     = models.CharField(max_length=100, blank=True)
    default_pincode   = models.CharField(max_length=10, blank=True)
    email_notifications = models.BooleanField(default=True)
    newsletter        = models.BooleanField(default=False)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.email}"
