from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Company(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    currency = models.CharField(max_length=10, default='PKR')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def total_outstanding(self):
        return sum(i.balance() for i in self.invoice_set.filter(status__in=['pending', 'partial', 'overdue']))


class Supplier(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    STATUS = [('draft','Draft'),('pending','Pending'),('partial','Partial'),('paid','Paid'),('overdue','Overdue')]
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=50)
    issue_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def balance(self):
        return self.amount - self.paid_amount

    def is_overdue(self):
        return self.due_date < timezone.now().date() and self.status not in ['paid']

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"


class Bill(models.Model):
    STATUS = [('draft','Draft'),('pending','Pending'),('paid','Paid'),('overdue','Overdue')]
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    bill_number = models.CharField(max_length=50)
    issue_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def balance(self):
        return self.amount - self.paid_amount

    def __str__(self):
        return f"{self.bill_number} - {self.supplier.name}"


EXPENSE_CATEGORIES = [
    ('salaries', 'Salaries'), ('rent', 'Rent'), ('utilities', 'Utilities'),
    ('marketing', 'Marketing'), ('logistics', 'Logistics'), ('travel', 'Travel'),
    ('software', 'Software'), ('misc', 'Miscellaneous'),
]


class Expense(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    category = models.CharField(max_length=50, choices=EXPENSE_CATEGORIES)
    description = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    receipt = models.FileField(upload_to='receipts/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - {self.amount}"


REVENUE_CATEGORIES = [
    ('products', 'Products'), ('services', 'Services'),
    ('consulting', 'Consulting'), ('other', 'Other'),
]


class Revenue(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    category = models.CharField(max_length=50, choices=REVENUE_CATEGORIES)
    description = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - {self.amount}"
