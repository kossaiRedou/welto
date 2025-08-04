from django.views.generic import ListView, CreateView, UpdateView
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, reverse
from django.urls import reverse_lazy
from django.contrib import messages
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg
from django_tables2 import RequestConfig
from .models import Order, OrderItem, Payment, CURRENCY
from decimal import Decimal
from .forms import OrderCreateForm, OrderEditForm
from product.models import Product, Category
from .tables import ProductTable, OrderItemTable, OrderTable

import datetime


@method_decorator(staff_member_required, name='dispatch')
class HomepageView(ListView):
    template_name = 'main_dashboard.html'
    model = Order
    queryset = Order.objects.all()[:10]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Données de base - utilisation de datetime.date pour compatibilité avec DateField
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        seven_days_ago = today - datetime.timedelta(days=6)  # 7 derniers jours (aujourd'hui inclus)
        this_month_start = today.replace(day=1)
        
        # Toutes les commandes - filtrage sur DateField
        all_orders = Order.objects.all()
        today_orders = all_orders.filter(date=today)
        yesterday_orders = all_orders.filter(date=yesterday)
        week_orders = all_orders.filter(date__gte=seven_days_ago, date__lte=today)
        month_orders = all_orders.filter(date__gte=this_month_start, date__lte=today)
        
        # === STATISTIQUES SIMPLES ET PARLANTES ===
        
        # Ventes d'aujourd'hui
        today_sales = today_orders.aggregate(Sum('final_value'))['final_value__sum'] or 0
        today_orders_count = today_orders.count()
        
        # Ventes d'hier (pour comparaison)
        yesterday_sales = yesterday_orders.aggregate(Sum('final_value'))['final_value__sum'] or 0
        
        # Évolution par rapport à hier
        if yesterday_sales > 0:
            sales_evolution = ((today_sales - yesterday_sales) / yesterday_sales) * 100
        else:
            sales_evolution = 100 if today_sales > 0 else 0
            
        # Ventes de la semaine
        week_sales = week_orders.aggregate(Sum('final_value'))['final_value__sum'] or 0
        week_orders_count = week_orders.count()
        
        # Ventes du mois
        month_sales = month_orders.aggregate(Sum('final_value'))['final_value__sum'] or 0
        month_orders_count = month_orders.count()
        
        # Panier moyen aujourd'hui
        avg_order_today = today_sales / today_orders_count if today_orders_count > 0 else 0
        
        # Argent en attente (non payé)
        unpaid_total = all_orders.filter(is_paid=False).aggregate(Sum('final_value'))['final_value__sum'] or 0
        
        # Produits les plus vendus (top 5)
        top_products = OrderItem.objects.values('product__title')\
            .annotate(total_qty=Sum('qty'), total_revenue=Sum('total_price'))\
            .order_by('-total_qty')[:5]
            
        # Stock faible (moins de 5 unités)
        low_stock = Product.objects.filter(active=True, qty__lt=5).count()
        
        # Produits en rupture
        out_of_stock = Product.objects.filter(active=True, qty=0).count()
        
        # Total des produits en stock
        total_products_in_stock = Product.objects.filter(active=True, qty__gt=0).aggregate(Sum('qty'))['qty__sum'] or 0
        
        # Commandes récentes (5 dernières)
        recent_orders = Order.objects.all()[:5]
        
        # === FORMATAGE POUR L'AFFICHAGE ===
        context.update({
            # Ventes du jour
            'today_sales': f'{today_sales:,.0f} {CURRENCY}',
            'today_orders_count': today_orders_count,
            'avg_order_today': f'{avg_order_today:,.0f} {CURRENCY}',
            
            # Comparaison avec hier
            'yesterday_sales': f'{yesterday_sales:,.0f} {CURRENCY}',
            'sales_evolution': f'{sales_evolution:+.1f}%',
            'sales_evolution_positive': sales_evolution >= 0,
            
            # Périodes plus longues
            'week_sales': f'{week_sales:,.0f} {CURRENCY}',
            'week_orders_count': week_orders_count,
            'month_sales': f'{month_sales:,.0f} {CURRENCY}',
            'month_orders_count': month_orders_count,
            
            # Argent en attente
            'unpaid_total': f'{unpaid_total:,.0f} {CURRENCY}',
            'has_unpaid': unpaid_total > 0,
            
            # Stock
            'low_stock_count': low_stock,
            'out_of_stock_count': out_of_stock,
            'total_products_in_stock': total_products_in_stock,
            'stock_alert': low_stock > 0 or out_of_stock > 0,
            
            # Produits populaires
            'top_products': top_products,
            
            # Commandes récentes
            'recent_orders': recent_orders,
            
            # Dates pour affichage
            'today_date': today.strftime('%d/%m/%Y'),
            'yesterday_date': yesterday.strftime('%d/%m/%Y'),
        })
        
        return context


@staff_member_required
def auto_create_order_view(request):
    new_order = Order.objects.create(
        title='Order 66',
        date=datetime.datetime.now()

    )
    new_order.title = f'Order - {new_order.id}'
    new_order.save()
    return redirect(new_order.get_edit_url())


@method_decorator(staff_member_required, name='dispatch')
class OrderListView(ListView):
    template_name = 'list.html'
    model = Order
    paginate_by = 50

    def get_queryset(self):
        qs = Order.objects.all()
        if self.request.GET:
            qs = Order.filter_data(self.request, qs)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orders = OrderTable(self.object_list)
        RequestConfig(self.request).configure(orders)
        context.update(locals())
        return context


@method_decorator(staff_member_required, name='dispatch')
class CreateOrderView(CreateView):
    template_name = 'form.html'
    form_class = OrderCreateForm
    model = Order

    def get_success_url(self):
        self.new_object.refresh_from_db()
        return reverse('update_order', kwargs={'pk': self.new_object.id})

    def form_valid(self, form):
        object = form.save()
        object.refresh_from_db()
        self.new_object = object
        return super().form_valid(form)


@method_decorator(staff_member_required, name='dispatch')
class OrderUpdateView(UpdateView):
    model = Order
    template_name = 'order_update.html'
    form_class = OrderEditForm

    def get_success_url(self):
        return reverse('update_order', kwargs={'pk': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.object
        qs_p = Product.objects.filter(active=True)[:12]
        products = ProductTable(qs_p)
        order_items = OrderItemTable(instance.order_items.all())
        RequestConfig(self.request).configure(products)
        RequestConfig(self.request).configure(order_items)
        context.update(locals())
        return context


@staff_member_required
def delete_order(request, pk):
    instance = get_object_or_404(Order, id=pk)
    instance.delete()
    messages.warning(request, 'The order is deleted!')
    return redirect(reverse('homepage'))


@staff_member_required
def done_order_view(request, pk):
    instance = get_object_or_404(Order, id=pk)
    instance.is_paid = True
    instance.save()
    return redirect(reverse('homepage'))


@staff_member_required
def ajax_add_product(request, pk, dk):
    instance = get_object_or_404(Order, id=pk)
    product = get_object_or_404(Product, id=dk)
    order_item, created = OrderItem.objects.get_or_create(order=instance, product=product)
    if created:
        order_item.qty = 1
        order_item.price = product.value
        order_item.discount_price = product.discount_value
    else:
        order_item.qty += 1
    order_item.save()
    product.qty -= 1
    product.save()
    instance.refresh_from_db()
    order_items = OrderItemTable(instance.order_items.all())
    RequestConfig(request).configure(order_items)
    data = dict()
    data['result'] = render_to_string(template_name='include/order_container.html',
                                      request=request,
                                      context={'instance': instance,
                                               'order_items': order_items
                                               }
                                    )
    return JsonResponse(data)


@staff_member_required
def ajax_modify_order_item(request, pk, action):
    order_item = get_object_or_404(OrderItem, id=pk)
    product = order_item.product
    instance = order_item.order
    if action == 'remove':
        order_item.qty -= 1
        product.qty += 1
        if order_item.qty < 1: order_item.qty = 1
    if action == 'add':
        order_item.qty += 1
        product.qty -= 1
    product.save()
    order_item.save()
    if action == 'delete':
        order_item.delete()
    data = dict()
    instance.refresh_from_db()
    order_items = OrderItemTable(instance.order_items.all())
    RequestConfig(request).configure(order_items)
    data['result'] = render_to_string(template_name='include/order_container.html',
                                      request=request,
                                      context={
                                          'instance': instance,
                                          'order_items': order_items
                                      }
                                      )
    return JsonResponse(data)


@staff_member_required
def ajax_search_products(request, pk):
    instance = get_object_or_404(Order, id=pk)
    q = request.GET.get('q', None)
    products = Product.broswer.active().filter(title__startswith=q) if q else Product.broswer.active()
    products = products[:12]
    products = ProductTable(products)
    RequestConfig(request).configure(products)
    data = dict()
    data['products'] = render_to_string(template_name='include/product_container.html',
                                        request=request,
                                        context={
                                            'products': products,
                                            'instance': instance
                                        })
    return JsonResponse(data)


@staff_member_required
def order_action_view(request, pk, action):
    instance = get_object_or_404(Order, id=pk)
    if action == 'is_paid':
        instance.is_paid = True
        instance.save()
    if action == 'delete':
        instance.delete()
    return redirect(reverse('homepage'))


@staff_member_required
def ajax_calculate_results_view(request):
    orders = Order.filter_data(request, Order.objects.all())
    total_value, total_paid_value, remaining_value, data = 0, 0, 0, dict()
    if orders.exists():
        total_value = orders.aggregate(Sum('final_value'))['final_value__sum']
        total_paid_value = orders.filter(is_paid=True).aggregate(Sum('final_value'))['final_value__sum'] if\
            orders.filter(is_paid=True) else 0
        remaining_value = total_value - total_paid_value
    total_value, total_paid_value, remaining_value = f'{total_value} {CURRENCY}',\
                                                     f'{total_paid_value} {CURRENCY}', f'{remaining_value} {CURRENCY}'
    data['result'] = render_to_string(template_name='include/result_container.html',
                                      request=request,
                                      context=locals())
    return JsonResponse(data)


@staff_member_required
def ajax_calculate_category_view(request):
    orders = Order.filter_data(request, Order.objects.all())
    order_items = OrderItem.objects.filter(order__in=orders)
    category_analysis = order_items.values_list('product__category__title').annotate(qty=Sum('qty'),
                                                                                      total_incomes=Sum('total_price')
                                                                                      )
    data = dict()
    category, currency = True, CURRENCY
    data['result'] = render_to_string(template_name='include/result_container.html',
                                      request=request,
                                      context=locals()
                                      )
    return JsonResponse(data)


# === VUES POUR GESTION DES PAIEMENTS ===

@staff_member_required
def ajax_add_payment(request, pk):
    """Ajouter un paiement à une commande via AJAX"""
    order = get_object_or_404(Order, id=pk)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            method = request.POST.get('method', 'cash')
            note = request.POST.get('note', '')
            
            if amount <= 0:
                return JsonResponse({'success': False, 'error': 'Le montant doit être supérieur à 0'})
            
            # Vérifier que le paiement ne dépasse pas le montant restant
            remaining = order.remaining_amount()
            if amount > remaining:
                return JsonResponse({
                    'success': False, 
                    'error': f'Le paiement ({amount} {CURRENCY}) dépasse le montant restant ({remaining} {CURRENCY})'
                })
            
            # Créer le paiement
            payment = Payment.objects.create(
                order=order,
                amount=amount,
                method=method,
                note=note
            )
            
            # Mettre à jour le statut is_paid de la commande
            order.is_paid = order.is_fully_paid()
            order.save()
            
            # Retourner les données mises à jour
            payments_html = render_to_string('include/payments_container.html', {
                'order': order,
                'payments': order.payments.all()
            })
            
            return JsonResponse({
                'success': True,
                'payments_html': payments_html,
                'total_payments': str(order.total_payments()),
                'remaining_amount': str(order.remaining_amount()),
                'payment_percentage': round(order.payment_percentage(), 1),
                'is_fully_paid': order.is_fully_paid()
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@staff_member_required
def ajax_delete_payment(request, pk, payment_id):
    """Supprimer un paiement via AJAX"""
    order = get_object_or_404(Order, id=pk)
    payment = get_object_or_404(Payment, id=payment_id, order=order)
    
    if request.method == 'POST':
        try:
            payment.delete()
            
            # Mettre à jour le statut is_paid de la commande
            order.is_paid = order.is_fully_paid()
            order.save()
            
            # Retourner les données mises à jour
            payments_html = render_to_string('include/payments_container.html', {
                'order': order,
                'payments': order.payments.all()
            })
            
            return JsonResponse({
                'success': True,
                'payments_html': payments_html,
                'total_payments': str(order.total_payments()),
                'remaining_amount': str(order.remaining_amount()),
                'payment_percentage': round(order.payment_percentage(), 1),
                'is_fully_paid': order.is_fully_paid()
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
