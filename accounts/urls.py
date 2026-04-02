from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('invoices/', views.invoices, name='invoices'),
    path('invoices/add/', views.add_invoice, name='add_invoice'),
    path('invoices/<int:pk>/pay/', views.mark_invoice_paid, name='mark_invoice_paid'),
    path('bills/', views.bills, name='bills'),
    path('bills/add/', views.add_bill, name='add_bill'),
    path('expenses/', views.expenses_view, name='expenses'),
    path('revenue/', views.revenue_view, name='revenue'),
    path('customers/', views.customers_view, name='customers'),
    path('suppliers/', views.suppliers_view, name='suppliers'),
    path('settings/', views.settings_view, name='settings'),
    path('api/chart-data/', views.api_chart_data, name='api_chart_data'),
]
