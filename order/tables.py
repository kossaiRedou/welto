import django_tables2 as tables

from product.models import Product
from .models import OrderItem, Order


class OrderTable(tables.Table):
    tag_final_value = tables.Column(orderable=False, verbose_name='Value')
    payment_status = tables.TemplateColumn(
        '''
        {% if record.is_paid %}
            <span class="badge bg-success">
                <i class="bi bi-check-circle me-1"></i>
                Payé
            </span>
        {% else %}
            <span class="badge bg-danger">
                <i class="bi bi-x-circle me-1"></i>
                Non payé
            </span>
        {% endif %}
        ''',
        orderable=False,
        verbose_name='Paiement'
    )
    action = tables.TemplateColumn(
        '''
        <a href="{{ record.get_edit_url }}" class="btn btn-outline-primary btn-sm" title="Modifier la commande">
            <i class="bi bi-pencil-square"></i>
        </a>
        ''', 
        orderable=False, 
        verbose_name='Actions'
    )

    class Meta:
        model = Order
        template_name = 'django_tables2/bootstrap.html'
        fields = ['date', 'title', 'payment_status', 'tag_final_value', 'action']


class ProductTable(tables.Table):
    tag_final_value = tables.Column(orderable=False, verbose_name='Price')
    qty = tables.TemplateColumn(
        '''
        {% if record.qty > 5 %}
            <span class="badge bg-success">{{ record.qty }}</span>
        {% elif record.qty > 0 %}
            <span class="badge bg-warning">{{ record.qty }}</span>
        {% else %}
            <span class="badge bg-danger">0</span>
        {% endif %}
        ''',
        orderable=False,
        verbose_name='Stock'
    )
    action = tables.TemplateColumn(
        '''
        {% if record.qty > 0 %}
            <button class="btn btn-info add_button" data-href="{% url "ajax_add" instance.id record.id %}">
                <i class="bi bi-plus-circle me-1"></i>Add
            </button>
        {% else %}
            <button class="btn btn-secondary" disabled title="Stock épuisé">
                <i class="bi bi-x-circle me-1"></i>Rupture
            </button>
        {% endif %}
        ''',
        orderable=False,
        verbose_name='Action'
    )

    class Meta:
        model = Product
        template_name = 'django_tables2/bootstrap.html'
        fields = ['title', 'category', 'qty', 'tag_final_value']


class OrderItemTable(tables.Table):
    tag_final_price = tables.Column(orderable=False, verbose_name='Price')
    action = tables.TemplateColumn('''
            <button data-href="{% url "ajax_modify" record.id "add" %}" class="btn btn-success edit_button"><i class="fa fa-arrow-up"></i></button>
            <button data-href="{% url "ajax_modify" record.id "remove" %}" class="btn btn-warning edit_button"><i class="fa fa-arrow-down"></i></button>
            <button data-href="{% url "ajax_modify" record.id "delete" %}" class="btn btn-danger edit_button"><i class="fa fa-trash"></i></button>
    ''', orderable=False)

    class Meta:
        model = OrderItem
        template_name = 'django_tables2/bootstrap.html'
        fields = ['product', 'qty', 'tag_final_price']