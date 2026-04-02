from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Company, Customer, Supplier, Invoice, Bill, Expense, Revenue
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Load 4 years of rich dummy data (2022-2025)'

    def handle(self, *args, **kwargs):
        user, created = User.objects.get_or_create(username='demo')
        if created:
            user.set_password('demo1234')
            user.save()
            self.stdout.write('Created user: demo / demo1234')

        company, _ = Company.objects.get_or_create(
            user=user,
            defaults={'name': 'Pak Trading Co.', 'address': 'Blue Area, Islamabad', 'phone': '051-1234567', 'email': 'info@paktrading.com', 'currency': 'PKR'}
        )

        customers_data = [
            ('Alpha Corp', 'alpha@corp.com', '0300-1234567'),
            ('Beta Industries', 'beta@ind.com', '0321-2345678'),
            ('Gamma Solutions', 'gamma@sol.com', '0333-3456789'),
            ('Delta Traders', 'delta@trade.com', '0312-4567890'),
            ('Epsilon Tech', 'eps@tech.com', '0345-5678901'),
            ('Zeta Enterprises', 'zeta@ent.com', '0301-6789012'),
        ]
        customers = []
        for name, email, phone in customers_data:
            c, _ = Customer.objects.get_or_create(company=company, name=name, defaults={'email': email, 'phone': phone})
            customers.append(c)

        suppliers_data = [
            ('Steel Corp', '0311-1111111'),
            ('Office Mart', '0322-2222222'),
            ('Tech Supplies', '0333-3333333'),
            ('Logistics Ltd', '0344-4444444'),
            ('Print House', '0355-5555555'),
        ]
        suppliers = []
        for name, phone in suppliers_data:
            s, _ = Supplier.objects.get_or_create(company=company, name=name, defaults={'phone': phone})
            suppliers.append(s)

        Invoice.objects.filter(company=company).delete()
        Bill.objects.filter(company=company).delete()
        Expense.objects.filter(company=company).delete()
        Revenue.objects.filter(company=company).delete()
        self.stdout.write('Cleared old data...')

        year_configs = {
            2022: {'base_rev': 650000,  'base_exp': 480000},
            2023: {'base_rev': 800000,  'base_exp': 580000},
            2024: {'base_rev': 1050000, 'base_exp': 720000},
            2025: {'base_rev': 1180000, 'base_exp': 800000},
        }

        seasonal = [0.82, 0.85, 0.93, 0.98, 1.05, 1.12, 0.90, 0.88, 1.08, 1.15, 1.20, 1.25]
        inv_count = 0
        bill_count = 0

        for year, cfg in year_configs.items():
            base_rev = cfg['base_rev']
            base_exp = cfg['base_exp']

            for month in range(1, 13):
                d = date(year, month, 15)
                season = seasonal[month - 1]
                noise = random.uniform(0.93, 1.10)

                rev_amt = base_rev * season * noise
                for cat, desc, pct in [('products','Product sales',0.55),('services','Service revenue',0.28),('consulting','Consulting fees',0.12),('other','Other income',0.05)]:
                    amt = round(rev_amt * pct)
                    if amt > 0:
                        Revenue.objects.create(company=company, date=d, category=cat, description=f'{desc} - {d.strftime("%b %Y")}', amount=amt)

                exp_amt = base_exp * season * random.uniform(0.92, 1.06)
                for cat, desc, pct in [('salaries','Salaries',0.40),('rent','Office rent',0.12),('utilities','Utilities',0.06),('marketing','Marketing',0.13),('logistics','Logistics',0.17),('software','Software',0.05),('travel','Travel',0.04),('misc','Misc',0.03)]:
                    amt = round(exp_amt * pct)
                    if amt > 0:
                        Expense.objects.create(company=company, date=d, category=cat, description=f'{desc} - {d.strftime("%b %Y")}', amount=amt)

                for cust in random.sample(customers, random.randint(2, 4)):
                    inv_count += 1
                    inv_amt = round(random.uniform(60000, 420000))
                    if year < 2025:
                        status = random.choices(['paid','partial'], weights=[85,15])[0]
                    elif month < 10:
                        status = random.choices(['paid','partial','pending'], weights=[70,15,15])[0]
                    else:
                        status = random.choices(['paid','pending','overdue'], weights=[50,35,15])[0]
                    paid = inv_amt if status == 'paid' else (round(inv_amt * random.uniform(0.3, 0.7)) if status == 'partial' else 0)
                    Invoice.objects.create(company=company, customer=cust, invoice_number=f'INV-{inv_count:04d}', issue_date=d, due_date=d+timedelta(days=30), amount=inv_amt, paid_amount=paid, status=status, description=f'Services {d.strftime("%b %Y")}')

                for sup in random.sample(suppliers, random.randint(2, 4)):
                    bill_count += 1
                    bill_amt = round(random.uniform(35000, 200000))
                    if year < 2025:
                        b_status = random.choices(['paid','partial'], weights=[88,12])[0]
                    else:
                        b_status = random.choices(['paid','pending','overdue'], weights=[55,30,15])[0]
                    b_paid = bill_amt if b_status == 'paid' else (round(bill_amt * random.uniform(0.3, 0.6)) if b_status == 'partial' else 0)
                    Bill.objects.create(company=company, supplier=sup, bill_number=f'BILL-{bill_count:04d}', issue_date=d, due_date=d+timedelta(days=30), amount=bill_amt, paid_amount=b_paid, status=b_status, description=f'Supply {d.strftime("%b %Y")}')

            self.stdout.write(f'  done {year}')

        self.stdout.write(self.style.SUCCESS(f'Done! {inv_count} invoices, {bill_count} bills loaded.'))
        self.stdout.write('Login: demo / demo1234')
