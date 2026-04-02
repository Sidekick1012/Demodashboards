from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import date, timedelta
import json
from decimal import Decimal
from .models import Company, Customer, Supplier, Invoice, Bill, Expense, Revenue


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid credentials')
    return render(request, 'accounts/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        company_name = request.POST.get('company_name')
        email = request.POST.get('email', '')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            user = User.objects.create_user(username=username, password=password, email=email)
            Company.objects.create(user=user, name=company_name)
            login(request, user)
            messages.success(request, 'Welcome! Your account is ready.')
            return redirect('dashboard')
    return render(request, 'accounts/register.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def get_company(request):
    try:
        return request.user.company
    except:
        return None


def get_filter_context(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', 0))
    return year, month, today


@login_required
def dashboard(request):
    company = get_company(request)
    if not company:
        return redirect('register')
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', 0))
    prev_year = year - 1

    rev_qs = Revenue.objects.filter(company=company, date__year=year)
    exp_qs = Expense.objects.filter(company=company, date__year=year)
    if month:
        rev_qs = rev_qs.filter(date__month=month)
        exp_qs = exp_qs.filter(date__month=month)

    total_rev = float(rev_qs.aggregate(s=Sum('amount'))['s'] or 0)
    total_exp = float(exp_qs.aggregate(s=Sum('amount'))['s'] or 0)
    net_profit = total_rev - total_exp
    margin = round(net_profit / total_rev * 100, 1) if total_rev else 0

    prev_rev = float(Revenue.objects.filter(company=company, date__year=prev_year).aggregate(s=Sum('amount'))['s'] or 0)
    prev_exp = float(Expense.objects.filter(company=company, date__year=prev_year).aggregate(s=Sum('amount'))['s'] or 0)
    prev_profit = prev_rev - prev_exp

    rev_growth = round((total_rev - prev_rev) / prev_rev * 100, 1) if prev_rev else 0
    exp_growth = round((total_exp - prev_exp) / prev_exp * 100, 1) if prev_exp else 0
    profit_growth = round((net_profit - prev_profit) / abs(prev_profit) * 100, 1) if prev_profit else 0

    net_ar = float((Invoice.objects.filter(company=company, status__in=['pending','partial','overdue']).aggregate(s=Sum('amount'))['s'] or 0)) - \
             float((Invoice.objects.filter(company=company, status__in=['pending','partial','overdue']).aggregate(s=Sum('paid_amount'))['s'] or 0))
    net_ap = float((Bill.objects.filter(company=company, status__in=['pending','overdue']).aggregate(s=Sum('amount'))['s'] or 0)) - \
             float((Bill.objects.filter(company=company, status__in=['pending','overdue']).aggregate(s=Sum('paid_amount'))['s'] or 0))

    overdue_invoices = Invoice.objects.filter(company=company, due_date__lt=today, status__in=['pending','partial']).count()
    overdue_bills = Bill.objects.filter(company=company, due_date__lt=today, status='pending').count()

    monthly_data = []
    for m in range(1, 13):
        rev = float(Revenue.objects.filter(company=company, date__year=year, date__month=m).aggregate(s=Sum('amount'))['s'] or 0)
        exp = float(Expense.objects.filter(company=company, date__year=year, date__month=m).aggregate(s=Sum('amount'))['s'] or 0)
        ar  = float(Invoice.objects.filter(company=company, issue_date__year=year, issue_date__month=m).aggregate(s=Sum('amount'))['s'] or 0)
        ap  = float(Bill.objects.filter(company=company, issue_date__year=year, issue_date__month=m).aggregate(s=Sum('amount'))['s'] or 0)
        monthly_data.append({'month': m, 'rev': rev, 'exp': exp, 'ar': ar, 'ap': ap, 'net': rev - exp})

    prev_monthly = []
    for m in range(1, 13):
        rev = float(Revenue.objects.filter(company=company, date__year=prev_year, date__month=m).aggregate(s=Sum('amount'))['s'] or 0)
        exp = float(Expense.objects.filter(company=company, date__year=prev_year, date__month=m).aggregate(s=Sum('amount'))['s'] or 0)
        prev_monthly.append({'rev': rev, 'exp': exp, 'net': rev - exp})

    exp_by_cat = {}
    for cat, _ in Expense._meta.get_field('category').choices:
        amt = float(exp_qs.filter(category=cat).aggregate(s=Sum('amount'))['s'] or 0)
        if amt > 0:
            exp_by_cat[cat] = amt

    rev_by_cat = {}
    for cat, _ in Revenue._meta.get_field('category').choices:
        amt = float(rev_qs.filter(category=cat).aggregate(s=Sum('amount'))['s'] or 0)
        if amt > 0:
            rev_by_cat[cat] = amt

    top_customers = []
    for cust in Customer.objects.filter(company=company):
        inv_f = Invoice.objects.filter(company=company, customer=cust, issue_date__year=year)
        if month:
            inv_f = inv_f.filter(issue_date__month=month)
        amt = float(inv_f.aggregate(s=Sum('amount'))['s'] or 0)
        if amt > 0:
            top_customers.append({'name': cust.name, 'amount': amt})
    top_customers.sort(key=lambda x: x['amount'], reverse=True)
    top_customers = top_customers[:5]

    yearly_trend = []
    for y in range(year - 3, year + 1):
        r = float(Revenue.objects.filter(company=company, date__year=y).aggregate(s=Sum('amount'))['s'] or 0)
        e = float(Expense.objects.filter(company=company, date__year=y).aggregate(s=Sum('amount'))['s'] or 0)
        yearly_trend.append({'year': y, 'rev': r, 'exp': e, 'net': r - e})

    avg_monthly_rev = total_rev / 12 if total_rev else 0
    avg_monthly_exp = total_exp / 12 if total_exp else 0
    forecast = []
    for i in range(1, 4):
        fm = (today.month + i - 1) % 12 + 1
        fy = today.year + ((today.month + i - 1) // 12)
        forecast.append({'month': date(fy, fm, 1).strftime('%b %Y'), 'rev': round(avg_monthly_rev * 1.03**i), 'exp': round(avg_monthly_exp * 1.01**i)})

    insights = []
    if margin < 10:
        insights.append({'type': 'danger', 'icon': '🚨', 'title': 'Low profit margin', 'body': f'Margin is {margin}% — below healthy 15-20%. Review expenses or increase pricing.'})
    elif margin > 25:
        insights.append({'type': 'success', 'icon': '🎯', 'title': 'Excellent margin', 'body': f'{margin}% margin — well above industry average. Good cost control.'})
    else:
        insights.append({'type': 'info', 'icon': '📊', 'title': 'Healthy margin', 'body': f'{margin}% profit margin — within normal range. Aim for 20%+ with better pricing.'})

    if not month:
        if rev_growth > 20:
            insights.append({'type': 'success', 'icon': '🚀', 'title': 'Strong revenue growth', 'body': f'Revenue up {rev_growth}% vs {prev_year}. Consider investing surplus in marketing or capacity.'})
        elif rev_growth < 0:
            insights.append({'type': 'danger', 'icon': '📉', 'title': 'Revenue declining', 'body': f'Revenue down {abs(rev_growth)}% vs {prev_year}. Investigate top customer loss or market shift.'})
        elif rev_growth < 5:
            insights.append({'type': 'warning', 'icon': '⚠️', 'title': 'Slow revenue growth', 'body': f'Only {rev_growth}% growth vs {prev_year}. Consider new customer acquisition or upselling.'})

    if net_ar > total_rev * 0.3:
        insights.append({'type': 'warning', 'icon': '💸', 'title': 'High receivables', 'body': f'PKR {round(net_ar/1000)}K outstanding — over 30% of annual revenue. Follow up on collections urgently.'})
    if overdue_invoices > 0:
        insights.append({'type': 'danger', 'icon': '⏰', 'title': f'{overdue_invoices} overdue invoices', 'body': 'Immediate follow-up needed. Overdue AR hurts cash flow and may signal customer issues.'})

    exp_ratio = total_exp / total_rev if total_rev else 1
    if exp_ratio > 0.85:
        insights.append({'type': 'danger', 'icon': '💰', 'title': 'Expenses too high', 'body': f'Expense ratio {round(exp_ratio*100)}% of revenue. Identify top cost drivers and reduce non-core spending.'})

    recent_txns = []
    for inv in Invoice.objects.filter(company=company).order_by('-created_at')[:5]:
        recent_txns.append({'date': str(inv.issue_date), 'desc': f'Invoice #{inv.invoice_number} — {inv.customer.name}', 'type': 'AR', 'amount': float(inv.amount), 'status': inv.status})
    for bill in Bill.objects.filter(company=company).order_by('-created_at')[:3]:
        recent_txns.append({'date': str(bill.issue_date), 'desc': f'Bill #{bill.bill_number} — {bill.supplier.name}', 'type': 'AP', 'amount': -float(bill.amount), 'status': bill.status})
    recent_txns.sort(key=lambda x: x['date'], reverse=True)

    MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

    context = {
        'company': company, 'year': year, 'month': month,
        'total_rev': total_rev, 'total_exp': total_exp,
        'net_profit': net_profit, 'margin': margin,
        'net_ar': round(net_ar), 'net_ap': round(net_ap),
        'rev_growth': rev_growth, 'exp_growth': exp_growth, 'profit_growth': profit_growth,
        'overdue_invoices': overdue_invoices, 'overdue_bills': overdue_bills,
        'monthly_data': json.dumps(monthly_data),
        'prev_monthly': json.dumps(prev_monthly),
        'exp_by_cat': json.dumps(exp_by_cat),
        'rev_by_cat': json.dumps(rev_by_cat),
        'top_customers': json.dumps(top_customers),
        'yearly_trend': json.dumps(yearly_trend),
        'forecast': json.dumps(forecast),
        'insights': insights,
        'recent_txns': json.dumps(recent_txns),
        'years': list(range(2022, today.year + 2)),
        'months': [(i, MONTH_NAMES[i-1]) for i in range(1, 13)],
        'prev_year': prev_year,
        'month_name': MONTH_NAMES[month-1] if month else '',
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def invoices(request):
    company = get_company(request)
    today = date.today()
    year, month, _ = get_filter_context(request)
    status_filter = request.GET.get('status', '')

    qs = Invoice.objects.filter(company=company).select_related('customer').order_by('-issue_date')
    if year:
        qs = qs.filter(issue_date__year=year)
    if month:
        qs = qs.filter(issue_date__month=month)
    if status_filter:
        qs = qs.filter(status=status_filter)
    for inv in qs:
        if inv.due_date < today and inv.status in ['pending', 'partial']:
            inv.status = 'overdue'
            inv.save()

    MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    context = {
        'invoices': qs, 'company': company, 'status_filter': status_filter,
        'year': year, 'month': month,
        'years': list(range(2022, today.year + 2)),
        'months': [(i, MONTH_NAMES[i-1]) for i in range(1, 13)],
    }
    return render(request, 'accounts/invoices.html', context)


@login_required
def add_invoice(request):
    company = get_company(request)
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        customer = get_object_or_404(Customer, id=customer_id, company=company)
        Invoice.objects.create(
            company=company, customer=customer,
            invoice_number=request.POST.get('invoice_number'),
            issue_date=request.POST.get('issue_date'),
            due_date=request.POST.get('due_date'),
            amount=request.POST.get('amount'),
            description=request.POST.get('description', ''),
        )
        messages.success(request, 'Invoice added successfully!')
        return redirect('invoices')
    customers = Customer.objects.filter(company=company)
    next_num = f"INV-{Invoice.objects.filter(company=company).count() + 1001}"
    context = {'customers': customers, 'next_num': next_num, 'today': date.today(), 'due': date.today() + timedelta(days=30)}
    return render(request, 'accounts/add_invoice.html', context)


@login_required
def mark_invoice_paid(request, pk):
    inv = get_object_or_404(Invoice, pk=pk, company=get_company(request))
    amount = request.POST.get('amount', inv.balance())
    inv.paid_amount += Decimal(str(amount))
    inv.status = 'paid' if inv.paid_amount >= inv.amount else 'partial'
    inv.save()
    messages.success(request, 'Payment recorded!')
    return redirect('invoices')


@login_required
def bills(request):
    company = get_company(request)
    today = date.today()
    year, month, _ = get_filter_context(request)
    status_filter = request.GET.get('status', '')

    qs = Bill.objects.filter(company=company).select_related('supplier').order_by('-issue_date')
    if year:
        qs = qs.filter(issue_date__year=year)
    if month:
        qs = qs.filter(issue_date__month=month)
    if status_filter:
        qs = qs.filter(status=status_filter)

    MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    context = {
        'bills': qs, 'company': company, 'today': today,
        'status_filter': status_filter,
        'year': year, 'month': month,
        'years': list(range(2022, today.year + 2)),
        'months': [(i, MONTH_NAMES[i-1]) for i in range(1, 13)],
    }
    return render(request, 'accounts/bills.html', context)


@login_required
def add_bill(request):
    company = get_company(request)
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        supplier = get_object_or_404(Supplier, id=supplier_id, company=company)
        Bill.objects.create(
            company=company, supplier=supplier,
            bill_number=request.POST.get('bill_number'),
            issue_date=request.POST.get('issue_date'),
            due_date=request.POST.get('due_date'),
            amount=request.POST.get('amount'),
            description=request.POST.get('description', ''),
        )
        messages.success(request, 'Bill added successfully!')
        return redirect('bills')
    suppliers = Supplier.objects.filter(company=company)
    next_num = f"BILL-{Bill.objects.filter(company=company).count() + 1001}"
    context = {'suppliers': suppliers, 'next_num': next_num, 'today': date.today(), 'due': date.today() + timedelta(days=30)}
    return render(request, 'accounts/add_bill.html', context)


@login_required
def expenses_view(request):
    company = get_company(request)
    today = date.today()
    year, month, _ = get_filter_context(request)
    cat_filter = request.GET.get('cat', '')

    if request.method == 'POST':
        Expense.objects.create(
            company=company,
            category=request.POST.get('category'),
            description=request.POST.get('description'),
            amount=request.POST.get('amount'),
            date=request.POST.get('date'),
        )
        messages.success(request, 'Expense recorded!')
        return redirect('expenses')

    qs = Expense.objects.filter(company=company).order_by('-date')
    if year:
        qs = qs.filter(date__year=year)
    if month:
        qs = qs.filter(date__month=month)
    if cat_filter:
        qs = qs.filter(category=cat_filter)

    from .models import EXPENSE_CATEGORIES
    MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    context = {
        'expenses': qs, 'categories': EXPENSE_CATEGORIES,
        'cat_filter': cat_filter, 'today': today,
        'year': year, 'month': month,
        'years': list(range(2022, today.year + 2)),
        'months': [(i, MONTH_NAMES[i-1]) for i in range(1, 13)],
    }
    return render(request, 'accounts/expenses.html', context)


@login_required
def revenue_view(request):
    company = get_company(request)
    today = date.today()
    year, month, _ = get_filter_context(request)

    if request.method == 'POST':
        Revenue.objects.create(
            company=company,
            category=request.POST.get('category'),
            description=request.POST.get('description'),
            amount=request.POST.get('amount'),
            date=request.POST.get('date'),
        )
        messages.success(request, 'Revenue recorded!')
        return redirect('revenue')

    qs = Revenue.objects.filter(company=company).order_by('-date')
    if year:
        qs = qs.filter(date__year=year)
    if month:
        qs = qs.filter(date__month=month)

    from .models import REVENUE_CATEGORIES
    MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    context = {
        'revenues': qs, 'categories': REVENUE_CATEGORIES, 'today': today,
        'year': year, 'month': month,
        'years': list(range(2022, today.year + 2)),
        'months': [(i, MONTH_NAMES[i-1]) for i in range(1, 13)],
    }
    return render(request, 'accounts/revenue.html', context)


@login_required
def customers_view(request):
    company = get_company(request)
    if request.method == 'POST':
        Customer.objects.create(
            company=company,
            name=request.POST.get('name'),
            email=request.POST.get('email', ''),
            phone=request.POST.get('phone', ''),
            address=request.POST.get('address', ''),
        )
        messages.success(request, 'Customer added!')
        return redirect('customers')
    qs = Customer.objects.filter(company=company).order_by('name')
    context = {'customers': qs}
    return render(request, 'accounts/customers.html', context)


@login_required
def suppliers_view(request):
    company = get_company(request)
    if request.method == 'POST':
        Supplier.objects.create(
            company=company,
            name=request.POST.get('name'),
            email=request.POST.get('email', ''),
            phone=request.POST.get('phone', ''),
        )
        messages.success(request, 'Supplier added!')
        return redirect('suppliers')
    qs = Supplier.objects.filter(company=company).order_by('name')
    context = {'suppliers': qs}
    return render(request, 'accounts/suppliers.html', context)


@login_required
def api_chart_data(request):
    company = get_company(request)
    year = int(request.GET.get('year', date.today().year))
    data = []
    for m in range(1, 13):
        rev = float(Revenue.objects.filter(company=company, date__year=year, date__month=m).aggregate(s=Sum('amount'))['s'] or 0)
        exp = float(Expense.objects.filter(company=company, date__year=year, date__month=m).aggregate(s=Sum('amount'))['s'] or 0)
        data.append({'month': m, 'rev': rev, 'exp': exp, 'net': rev - exp})
    return JsonResponse({'data': data})


@login_required
def settings_view(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    company = get_company(request)
    if request.method == 'POST':
        company.name = request.POST.get('name', company.name)
        company.address = request.POST.get('address', company.address)
        company.phone = request.POST.get('phone', company.phone)
        company.email = request.POST.get('email', company.email)
        company.currency = request.POST.get('currency', company.currency)
        company.save()
        messages.success(request, 'Settings updated!')
        return redirect('settings')
    return render(request, 'accounts/settings.html', {'company': company})