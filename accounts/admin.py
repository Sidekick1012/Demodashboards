from django.contrib import admin
from .models import Company, Customer, Supplier, Invoice, Bill, Expense, Revenue

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'currency', 'created_at']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'email', 'phone']
    list_filter = ['company']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'email']
    list_filter = ['company']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'amount', 'status', 'due_date']
    list_filter = ['status', 'company']

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'supplier', 'amount', 'status', 'due_date']
    list_filter = ['status', 'company']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['category', 'description', 'amount', 'date']
    list_filter = ['category', 'company']

@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ['category', 'description', 'amount', 'date']
    list_filter = ['category', 'company']
